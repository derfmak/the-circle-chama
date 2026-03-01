import uuid
from decimal import Decimal
from datetime import datetime, date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from django.http import JsonResponse
from django.conf import settings
from apps.accounts.models import User
from .models import MemberProfile, ContributionType, Contribution, PaymentTransaction, Debt, CashPaymentRequest
from .forms import PaymentForm, QuarterlyPaymentForm, MonthSelectionForm, FilterContributionsForm
from apps.payments.mpesa import initiate_stk_push, query_transaction_status

MONTHS = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April',
    5: 'May', 6: 'June', 7: 'July', 8: 'August',
    9: 'September', 10: 'October', 11: 'November', 12: 'December'
}

QUARTER_MONTHS = {
    1: [1, 2, 3, 4],
    2: [5, 6, 7, 8],
    3: [9, 10, 11, 12]
}

@login_required
def member_dashboard_view(request):
    if request.user.is_admin:
        return redirect('admin_dashboard')
    
    monthly_total = Contribution.objects.filter(
        user=request.user,
        contribution_type__contribution_type='monthly',
        status__in=['paid', 'paid_late']
    ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
    
    quarterly_total = Contribution.objects.filter(
        user=request.user,
        contribution_type__contribution_type='quarterly',
        status__in=['paid', 'paid_late']
    ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
    
    registration_total = Contribution.objects.filter(
        user=request.user,
        contribution_type__contribution_type='registration',
        status__in=['paid', 'paid_late']
    ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
    
    total_fines_paid = Contribution.objects.filter(
        user=request.user,
        status__in=['paid', 'paid_late']
    ).aggregate(total=Sum('fine_amount'))['total'] or Decimal('0')
    
    today = date.today()
    current_year = today.year
    current_month = today.month
    current_day = today.day
    
    pending_contributions = Contribution.objects.filter(
        user=request.user,
        status='pending'
    )
    
    filtered_pending = []
    
    for contribution in pending_contributions:
        if contribution.contribution_type.contribution_type == 'monthly':
            if contribution.year < current_year:
                filtered_pending.append(contribution)
            elif contribution.year == current_year and contribution.month < current_month:
                filtered_pending.append(contribution)
            elif (contribution.year == current_year and 
                  contribution.month == current_month and 
                  current_day <= 10):
                filtered_pending.append(contribution)
        else:
            filtered_pending.append(contribution)
    
    pending_count = len(filtered_pending)
    
    rejected_count = Contribution.objects.filter(
        user=request.user,
        status='rejected'
    ).count()
    
    total_debts = Debt.objects.filter(
        user=request.user,
        is_cleared=False
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    recent_payments = PaymentTransaction.objects.filter(
        user=request.user,
        status='completed'
    ).order_by('-created_at')[:5]
    
    context = {
        'monthly_total': monthly_total,
        'quarterly_total': quarterly_total,
        'registration_total': registration_total,
        'total_fines_paid': total_fines_paid,
        'pending_contributions': pending_count,
        'rejected_contributions': rejected_count,
        'total_debts': total_debts,
        'recent_payments': recent_payments,
    }
    
    return render(request, 'members/dashboard.html', context)

@login_required
def contributions_view(request):
    if request.user.is_admin:
        return redirect('admin_dashboard')
    
    contributions = Contribution.objects.filter(
        user=request.user,
        status__in=['paid', 'paid_late', 'waiting_approval', 'rejected']
    ).select_related('contribution_type').order_by('-year', '-month')
    
    form = FilterContributionsForm(data=request.GET)
    if form.is_valid():
        year = form.cleaned_data.get('year')
        status = form.cleaned_data.get('status')
        
        if year:
            contributions = contributions.filter(year=year)
        if status:
            contributions = contributions.filter(status=status)
    
    total_accumulated = contributions.filter(
        status__in=['paid', 'paid_late']
    ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
    
    total_fines = contributions.filter(
        status__in=['paid', 'paid_late']
    ).aggregate(total=Sum('fine_amount'))['total'] or Decimal('0')
    
    pending_approval_total = CashPaymentRequest.objects.filter(
        user=request.user,
        status='pending'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    years = contributions.values_list('year', flat=True).distinct().order_by('-year')
    
    contribution_list = []
    for c in contributions:
        month_name = MONTHS.get(c.month, '') if c.month else ''
        contribution_list.append({
            'id': c.id,
            'year': c.year,
            'month': c.month,
            'month_name': month_name,
            'quarter': c.quarter,
            'type_name': c.contribution_type.name,
            'type': c.contribution_type.contribution_type,
            'amount_due': c.amount_due,
            'fine_amount': c.fine_amount,
            'amount_paid': c.amount_paid,
            'status': c.status,
            'paid_at': c.paid_at,
            'is_late': c.is_late,
        })
    
    context = {
        'contributions': contribution_list,
        'form': form,
        'years': years,
        'total_accumulated': total_accumulated,
        'total_fines': total_fines,
        'pending_approval_total': pending_approval_total,
        'MONTHS': MONTHS,
    }
    return render(request, 'members/contributions.html', context)

@login_required
def make_payment_view(request):
    if request.user.is_admin:
        return redirect('admin_dashboard')
    
    monthly_type = ContributionType.objects.get(contribution_type='monthly', is_active=True)
    quarterly_type = ContributionType.objects.get(contribution_type='quarterly', is_active=True)
    
    today = date.today()
    current_year = today.year
    current_month = today.month
    current_day = today.day
    join_date = request.user.date_joined.date()
    join_month = join_date.month
    join_year = join_date.year
    
    selected_year = int(request.GET.get('year', current_year))
    selected_quarter_year = int(request.GET.get('quarter_year', current_year))
    
    QUARTER_STARTS = {
        1: 1, 2: 1, 3: 1, 4: 1,
        5: 5, 6: 5, 7: 5, 8: 5,
        9: 9, 10: 9, 11: 9, 12: 9,
    }
    
    start_month = QUARTER_STARTS[join_month]
    start_year = join_year
    
    calendar_months = []
    available_years = set()
    
    earliest_unpaid_year = None
    earliest_unpaid_month = None
    
    for year in range(start_year, current_year + 1):
        month_start = 1
        if year == start_year:
            month_start = start_month
        month_end = 12 if year < current_year else current_month
        
        for month in range(month_start, month_end + 1):
            contribution, created = Contribution.objects.get_or_create(
                user=request.user,
                contribution_type=monthly_type,
                year=year,
                month=month,
                defaults={
                    'amount_due': monthly_type.amount,
                    'status': 'pending'
                }
            )
            
            if contribution.status in ['pending', 'partial'] and earliest_unpaid_year is None:
                earliest_unpaid_year = year
                earliest_unpaid_month = month
    
    for year in range(start_year, 2101):
        month_start = 1
        if year == start_year:
            month_start = start_month
        month_end = 12
        
        for month in range(month_start, month_end + 1):
            contribution, created = Contribution.objects.get_or_create(
                user=request.user,
                contribution_type=monthly_type,
                year=year,
                month=month,
                defaults={
                    'amount_due': monthly_type.amount,
                    'status': 'pending'
                }
            )
            
            is_late = False
            status_color = ''
            
            if contribution.status == 'paid':
                status_color = 'paid-month'
            elif contribution.status == 'paid_late':
                status_color = 'paid-late-month'
                is_late = True
            elif contribution.status == 'waiting_approval':
                status_color = 'waiting-approval-month'
            elif contribution.status == 'rejected':
                status_color = 'rejected-month'
            elif contribution.status in ['pending', 'partial']:
                if year < current_year:
                    is_late = True
                    status_color = 'overdue-month'
                elif year == current_year:
                    if month < current_month:
                        is_late = True
                        status_color = 'overdue-month'
                    elif month == current_month and current_day > 10:
                        is_late = True
                        status_color = 'pending-late-month'
                    else:
                        status_color = 'pending-month'
                else:
                    status_color = 'future-month'
            
            if is_late and contribution.fine_amount == 0 and contribution.status in ['pending', 'partial']:
                contribution.fine_amount = Decimal('200.00')
                contribution.is_late = True
                contribution.save()
            
            selectable = contribution.status in ['pending', 'partial', 'rejected']
            
            if selectable and contribution.status != 'rejected':
                if earliest_unpaid_year and earliest_unpaid_month:
                    if year > earliest_unpaid_year:
                        selectable = False
                    elif year == earliest_unpaid_year and month > earliest_unpaid_month:
                        selectable = False
            
            amount_due = contribution.amount_due + contribution.fine_amount - contribution.amount_paid
            
            has_rejected_request = CashPaymentRequest.objects.filter(
                contribution=contribution,
                status='declined'
            ).exists()
            
            calendar_months.append({
                'id': contribution.id,
                'month': month,
                'month_name': MONTHS[month],
                'year': year,
                'amount': amount_due if selectable else 0,
                'is_late': is_late,
                'fine': contribution.fine_amount if selectable else 0,
                'status': contribution.status,
                'status_color': status_color,
                'selectable': selectable,
                'has_rejected_request': has_rejected_request
            })
            
            available_years.add(year)
    
    calendar_months.sort(key=lambda x: (x['year'], x['month']))
    available_years = sorted(list(available_years), reverse=True)
    
    quarters = []
    for year in range(current_year, 2051):
        for q_num, months in QUARTER_MONTHS.items():
            quarter_contribution, created = Contribution.objects.get_or_create(
                user=request.user,
                contribution_type=quarterly_type,
                year=year,
                quarter=q_num,
                defaults={
                    'amount_due': quarterly_type.amount,
                    'status': 'pending'
                }
            )
            
            if year > current_year:
                can_pay = False
            else:
                can_pay = quarter_contribution.status in ['pending', 'partial', 'rejected']
            
            amount_due = quarter_contribution.amount_due - quarter_contribution.amount_paid
            progress = (quarter_contribution.amount_paid / quarter_contribution.amount_due) * 100 if quarter_contribution.amount_due > 0 else 0
            
            has_pending_cash_request = CashPaymentRequest.objects.filter(
                contribution=quarter_contribution,
                status='pending'
            ).exists()
            
            has_rejected_cash_request = CashPaymentRequest.objects.filter(
                contribution=quarter_contribution,
                status='declined'
            ).exists()
            
            if has_pending_cash_request and quarter_contribution.status != 'waiting_approval':
                quarter_contribution.status = 'waiting_approval'
                quarter_contribution.save()
                can_pay = False
            
            quarters.append({
                'id': quarter_contribution.id,
                'quarter': q_num,
                'year': year,
                'months': [MONTHS[m] for m in months],
                'amount_due': quarter_contribution.amount_due,
                'amount_paid': quarter_contribution.amount_paid,
                'balance': amount_due,
                'status': quarter_contribution.status,
                'can_pay': can_pay and not has_pending_cash_request,
                'has_pending_request': has_pending_cash_request,
                'has_rejected_request': has_rejected_cash_request,
                'progress': progress
            })
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment_mode = form.cleaned_data['payment_mode']
            selected_months = request.POST.getlist('months')
            selected_quarters = request.POST.getlist('quarterly')
            payment_type = request.POST.get('payment_type')
            partial_amount = request.POST.get('partial_amount')
            mpesa_phone = form.cleaned_data.get('mpesa_phone', '')
            cash_notes = request.POST.get('cash_notes', '')
            
            total_amount = Decimal('0')
            contributions_to_pay = []
            request_again_count = 0
            
            for month_id in selected_months:
                contribution = Contribution.objects.get(id=month_id, user=request.user)
                if contribution.status == 'rejected':
                    amount = contribution.amount_due + contribution.fine_amount - contribution.amount_paid
                    CashPaymentRequest.objects.create(
                        user=request.user,
                        contribution=contribution,
                        amount=amount,
                        notes="Re-request after rejection",
                        status='pending'
                    )
                    contribution.status = 'waiting_approval'
                    contribution.save()
                    request_again_count += 1
                    messages.success(request, f'Your request for {contribution.month_name} {contribution.year} has been sent to admin for approval.')
                else:
                    amount = contribution.amount_due + contribution.fine_amount - contribution.amount_paid
                    total_amount += amount
                    contributions_to_pay.append((contribution, amount))
            
            for quarter_id in selected_quarters:
                contribution = Contribution.objects.get(id=quarter_id, user=request.user)
                if contribution.status == 'rejected':
                    amount = contribution.amount_due - contribution.amount_paid
                    CashPaymentRequest.objects.create(
                        user=request.user,
                        contribution=contribution,
                        amount=amount,
                        notes="Re-request after rejection",
                        status='pending'
                    )
                    contribution.status = 'waiting_approval'
                    contribution.save()
                    request_again_count += 1
                    messages.success(request, f'Your request for Quarter {contribution.quarter} {contribution.year} has been sent to admin for approval.')
                else:
                    if payment_type == 'partial':
                        try:
                            amount = Decimal(partial_amount)
                            if amount <= 0:
                                messages.error(request, 'Partial amount must be greater than 0')
                                return redirect('make_payment')
                            if amount >= contribution.amount_due - contribution.amount_paid:
                                messages.error(request, f'Partial amount must be less than remaining balance of KES {contribution.amount_due - contribution.amount_paid}')
                                return redirect('make_payment')
                            if amount % 1 != 0:
                                messages.error(request, 'Partial amount must be a whole number')
                                return redirect('make_payment')
                        except:
                            messages.error(request, 'Please enter a valid number for partial payment')
                            return redirect('make_payment')
                    else:
                        amount = contribution.amount_due - contribution.amount_paid
                    
                    total_amount += amount
                    contributions_to_pay.append((contribution, amount, payment_type))
            
            if request_again_count > 0 and not contributions_to_pay:
                return redirect('contributions')
            
            if payment_mode == 'cash':
                for item in contributions_to_pay:
                    if len(item) == 3:
                        contribution, amount, ptype = item
                    else:
                        contribution, amount = item
                        ptype = 'full'
                    
                    CashPaymentRequest.objects.create(
                        user=request.user,
                        contribution=contribution,
                        amount=amount,
                        notes=f"{ptype} payment - {cash_notes}" if cash_notes else f"{ptype} payment",
                        status='pending'
                    )
                    contribution.status = 'waiting_approval'
                    contribution.save()
                messages.success(request, 'Cash payment request submitted. Please wait for admin approval.')
                return redirect('contributions')
            
            elif payment_mode == 'mpesa' and total_amount > 0:
                idempotency_key = str(uuid.uuid4())
                payment_transaction = PaymentTransaction.objects.create(
                    user=request.user,
                    amount=total_amount,
                    payment_mode='mpesa',
                    mpesa_phone=mpesa_phone,
                    idempotency_key=idempotency_key,
                    status='pending'
                )
                
                for item in contributions_to_pay:
                    if len(item) == 3:
                        contribution, amount, ptype = item
                    else:
                        contribution, amount = item
                        ptype = 'full'
                    
                    payment_transaction.contributions.add(contribution)
                
                response = initiate_stk_push(mpesa_phone, int(total_amount), idempotency_key)
                if response.get('ResponseCode') == '0':
                    payment_transaction.merchant_request_id = response.get('MerchantRequestID')
                    payment_transaction.checkout_request_id = response.get('CheckoutRequestID')
                    payment_transaction.save()
                    return redirect('payment_pending', transaction_id=payment_transaction.id)
                else:
                    payment_transaction.status = 'failed'
                    payment_transaction.result_desc = response.get('errorMessage', 'Failed to initiate payment')
                    payment_transaction.save()
                    return render(request, 'members/payment_failed.html', {'error': response.get('errorMessage', 'Payment initiation failed')})
            
            elif request_again_count > 0:
                return redirect('contributions')
    else:
        form = PaymentForm()
    
    quarter_years = range(current_year, 2051)
    
    context = {
        'form': form,
        'monthly_months': calendar_months,
        'calendar_months': calendar_months,
        'quarterly_contributions': quarters,
        'available_years': available_years,
        'quarter_years': quarter_years,
        'selected_year': selected_year,
        'selected_quarter_year': selected_quarter_year,
        'today': today,
        'full_quarterly_amount': quarterly_type.amount,
    }
    return render(request, 'members/make_payment.html', context)

@login_required
def request_again_view(request, contribution_id):
    if request.user.is_admin:
        return redirect('admin_dashboard')
    
    contribution = get_object_or_404(Contribution, id=contribution_id, user=request.user)
    
    if contribution.status != 'rejected':
        messages.error(request, 'Only rejected payments can be requested again.')
        return redirect('make_payment')
    
    amount = contribution.amount_due + contribution.fine_amount - contribution.amount_paid
    
    CashPaymentRequest.objects.create(
        user=request.user,
        contribution=contribution,
        amount=amount,
        notes="Re-request after rejection",
        status='pending'
    )
    
    contribution.status = 'waiting_approval'
    contribution.save()
    
    month_name = contribution.month_name if hasattr(contribution, 'month_name') else f'Quarter {contribution.quarter}'
    messages.success(request, f'Your request for {month_name} {contribution.year} has been sent to admin for approval.')
    
    return redirect('make_payment')

@login_required
def quarterly_contributions_view(request):
    if request.user.is_admin:
        return redirect('admin_dashboard')
    
    quarterly_type = ContributionType.objects.get(contribution_type='quarterly', is_active=True)
    current_year = date.today().year
    selected_year = int(request.GET.get('year', current_year))
    
    quarters = []
    for q_num, months in QUARTER_MONTHS.items():
        quarter_contribution, created = Contribution.objects.get_or_create(
            user=request.user,
            contribution_type=quarterly_type,
            year=selected_year,
            quarter=q_num,
            defaults={
                'amount_due': quarterly_type.amount,
                'status': 'pending'
            }
        )
        
        amount_due = quarter_contribution.amount_due
        amount_paid = quarter_contribution.amount_paid
        balance = amount_due - amount_paid
        progress = (amount_paid / amount_due) * 100 if amount_due > 0 else 0
        
        has_pending_cash_request = CashPaymentRequest.objects.filter(
            contribution=quarter_contribution,
            status='pending'
        ).exists()
        
        has_rejected_cash_request = CashPaymentRequest.objects.filter(
            contribution=quarter_contribution,
            status='declined'
        ).exists()
        
        if has_pending_cash_request and quarter_contribution.status != 'waiting_approval':
            quarter_contribution.status = 'waiting_approval'
            quarter_contribution.save()
        
        quarters.append({
            'quarter': q_num,
            'months': [MONTHS[m] for m in months],
            'amount_due': amount_due,
            'amount_paid': amount_paid,
            'balance': balance,
            'status': quarter_contribution.status,
            'paid_at': quarter_contribution.paid_at,
            'contribution': quarter_contribution,
            'has_pending_request': has_pending_cash_request,
            'has_rejected_request': has_rejected_cash_request,
            'progress': progress
        })
    
    years = range(current_year, 2051)
    
    context = {
        'quarters': quarters,
        'years': years,
        'selected_year': selected_year,
    }
    return render(request, 'members/quarterly_contributions.html', context)


@login_required
def pay_quarterly_view(request, quarter):
    if request.user.is_admin:
        return redirect('admin_dashboard')
    
    quarterly_type = ContributionType.objects.get(contribution_type='quarterly', is_active=True)
    current_year = date.today().year
    selected_year = int(request.GET.get('year', current_year))
    
    contribution = get_object_or_404(Contribution, 
        user=request.user,
        contribution_type=quarterly_type,
        year=selected_year,
        quarter=quarter
    )
    
    if contribution.status in ['paid', 'paid_late']:
        return redirect('quarterly_contributions')
    
    remaining_balance = contribution.amount_due - contribution.amount_paid
    progress = (contribution.amount_paid / contribution.amount_due) * 100 if contribution.amount_due > 0 else 0
    
    if request.method == 'POST':
        form = QuarterlyPaymentForm(request.POST)
        if form.is_valid():
            payment_mode = form.cleaned_data['payment_mode']
            payment_type = request.POST.get('payment_type', 'full')
            partial_amount = request.POST.get('partial_amount')
            mpesa_phone = form.cleaned_data.get('mpesa_phone', '')
            cash_notes = request.POST.get('cash_notes', '')
            
            if contribution.status == 'rejected':
                amount = remaining_balance
                CashPaymentRequest.objects.create(
                    user=request.user,
                    contribution=contribution,
                    amount=amount,
                    notes="Re-request after rejection",
                    status='pending'
                )
                contribution.status = 'waiting_approval'
                contribution.save()
                messages.success(request, 'Your request has been submitted for admin approval.')
                return redirect('quarterly_contributions')
            
            if payment_type == 'partial':
                try:
                    amount = Decimal(partial_amount)
                    if amount <= 0:
                        messages.error(request, 'Partial amount must be greater than 0')
                        return redirect('pay_quarterly', quarter=quarter)
                    if amount >= remaining_balance:
                        messages.error(request, f'Partial amount must be less than remaining balance of KES {remaining_balance}')
                        return redirect('pay_quarterly', quarter=quarter)
                    if amount % 1 != 0:
                        messages.error(request, 'Partial amount must be a whole number')
                        return redirect('pay_quarterly', quarter=quarter)
                except:
                    messages.error(request, 'Please enter a valid number for partial payment')
                    return redirect('pay_quarterly', quarter=quarter)
            else:
                amount = remaining_balance
            
            if payment_mode == 'cash':
                CashPaymentRequest.objects.create(
                    user=request.user,
                    contribution=contribution,
                    amount=amount,
                    notes=f"{payment_type} payment - {cash_notes}" if cash_notes else f"{payment_type} payment",
                    status='pending'
                )
                contribution.status = 'waiting_approval'
                contribution.save()
                messages.success(request, 'Cash payment request submitted. Please wait for admin approval.')
                return redirect('quarterly_contributions')
            
            elif payment_mode == 'mpesa':
                idempotency_key = str(uuid.uuid4())
                transaction = PaymentTransaction.objects.create(
                    user=request.user,
                    contribution=contribution,
                    amount=amount,
                    payment_mode='mpesa',
                    mpesa_phone=mpesa_phone,
                    idempotency_key=idempotency_key,
                    status='pending'
                )
                
                response = initiate_stk_push(mpesa_phone, int(amount), idempotency_key)
                
                if response.get('ResponseCode') == '0':
                    transaction.merchant_request_id = response.get('MerchantRequestID')
                    transaction.checkout_request_id = response.get('CheckoutRequestID')
                    transaction.save()
                    return redirect('payment_pending', transaction_id=transaction.id)
                else:
                    transaction.status = 'failed'
                    transaction.result_desc = response.get('errorMessage', 'Failed to initiate payment')
                    transaction.save()
                    return render(request, 'members/payment_failed.html', {'error': 'Payment initiation failed'})
    else:
        form = QuarterlyPaymentForm()
    
    years = range(current_year, 2051)
    
    context = {
        'form': form,
        'quarter': quarter,
        'selected_year': selected_year,
        'years': years,
        'amount_due': contribution.amount_due,
        'amount_paid': contribution.amount_paid,
        'remaining_balance': remaining_balance,
        'progress': progress,
        'status': contribution.status,
    }
    return render(request, 'members/pay_quarterly.html', context)

@login_required
def payment_pending_view(request, transaction_id):
    transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
    
    if transaction.status == 'completed':
        return redirect('payment_success', transaction_id=transaction.id)
    elif transaction.status == 'failed':
        return redirect('payment_failed', transaction_id=transaction.id)
    
    context = {
        'transaction': transaction,
    }
    return render(request, 'members/payment_pending.html', context)

@login_required
def check_payment_status_view(request, transaction_id):
    transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
    
    if transaction.checkout_request_id:
        status_response = query_transaction_status(transaction.checkout_request_id)
        
        if status_response.get('ResultCode') == '0':
            with transaction.atomic():
                transaction.status = 'completed'
                transaction.result_code = '0'
                transaction.result_desc = 'Success'
                transaction.callback_received = True
                transaction.save()
                
                if transaction.contribution:
                    contribution = transaction.contribution
                    contribution.amount_paid += transaction.amount
                    if contribution.amount_paid >= contribution.amount_due + contribution.fine_amount:
                        contribution.status = 'paid_late' if contribution.is_late else 'paid'
                        contribution.paid_at = timezone.now()
                    else:
                        contribution.status = 'partial'
                    contribution.save()
                
                return JsonResponse({'status': 'completed'})
        elif status_response.get('ResultCode'):
            transaction.status = 'failed'
            transaction.result_code = status_response.get('ResultCode')
            transaction.result_desc = status_response.get('ResultDesc')
            transaction.save()
            return JsonResponse({'status': 'failed'})
    
    return JsonResponse({'status': transaction.status})

@login_required
def payment_success_view(request, transaction_id):
    transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
    return render(request, 'members/payment_success.html', {'transaction': transaction})

@login_required
def payment_failed_view(request, transaction_id):
    transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
    return render(request, 'members/payment_failed.html', {'transaction': transaction})