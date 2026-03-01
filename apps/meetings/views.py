import uuid
from decimal import Decimal
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Count, Q
from .models import Meeting, MeetingAttendance, MeetingFacilitationPayment
from .forms import MeetingResponseForm, FacilitationPaymentForm, MeetingSummaryForm, MeetingForm
from apps.payments.mpesa import initiate_stk_push, query_transaction_status

@login_required
def meetings_list_view(request):
    if request.user.is_admin:
        return redirect('admin_meetings')
    
    today = timezone.now()
    
    upcoming_meetings = Meeting.objects.filter(
        date__gte=today,
        status='scheduled'
    ).order_by('date')
    
    past_meetings = Meeting.objects.filter(
        date__lt=today
    ).order_by('-date')[:10]
    
    user_attendances = MeetingAttendance.objects.filter(
        member=request.user,
        meeting__in=list(upcoming_meetings) + list(past_meetings)
    )
    
    attendance_map = {a.meeting_id: a for a in user_attendances}
    
    upcoming_with_status = []
    for meeting in upcoming_meetings:
        attendance = attendance_map.get(meeting.id)
        upcoming_with_status.append({
            'meeting': meeting,
            'attendance': attendance,
            'can_respond': not attendance or attendance.status not in ['accepted', 'absent', 'absent_with_apology']
        })
    
    past_with_status = []
    for meeting in past_meetings:
        attendance = attendance_map.get(meeting.id)
        past_with_status.append({
            'meeting': meeting,
            'attendance': attendance,
            'has_summary': bool(meeting.summary)
        })
    
    context = {
        'upcoming_meetings': upcoming_with_status,
        'past_meetings': past_with_status,
    }
    return render(request, 'meetings/list.html', context)

@login_required
def meeting_detail_view(request, meeting_id):
    if request.user.is_admin:
        return redirect('admin_meeting_detail', meeting_id=meeting_id)
    
    meeting = get_object_or_404(Meeting, id=meeting_id)
    
    try:
        attendance = MeetingAttendance.objects.get(meeting=meeting, member=request.user)
    except MeetingAttendance.DoesNotExist:
        attendance = None
    
    context = {
        'meeting': meeting,
        'attendance': attendance,
    }
    return render(request, 'meetings/detail.html', context)

@login_required
def respond_meeting_view(request, meeting_id):
    if request.user.is_admin:
        return redirect('admin_meetings')
    
    meeting = get_object_or_404(Meeting, id=meeting_id, status='scheduled')
    
    if meeting.date < timezone.now():
        return redirect('meetings_list')
    
    try:
        attendance = MeetingAttendance.objects.get(meeting=meeting, member=request.user)
        if attendance.status in ['accepted', 'absent', 'absent_with_apology']:
            return redirect('meetings_list')
    except MeetingAttendance.DoesNotExist:
        attendance = None
    
    if request.method == 'POST':
        form = MeetingResponseForm(request.POST)
        if form.is_valid():
            response = form.cleaned_data['response']
            apology_reason = form.cleaned_data.get('apology_reason', '')
            
            with transaction.atomic():
                attendance, created = MeetingAttendance.objects.get_or_create(
                    meeting=meeting,
                    member=request.user,
                    defaults={
                        'status': response,
                        'apology_reason': apology_reason if response == 'absent_with_apology' else '',
                        'payment_status': 'pending'
                    }
                )
                
                if not created:
                    attendance.status = response
                    attendance.apology_reason = apology_reason if response == 'absent_with_apology' else ''
                    attendance.save()
                
                if response == 'accepted':
                    return redirect('pay_facilitation', attendance_id=attendance.id)
                elif response == 'absent_with_apology':
                    return redirect('pay_facilitation', attendance_id=attendance.id)
                else:
                    attendance.payment_status = 'unpaid'
                    attendance.save()
                    
                    from apps.members.models import Debt
                    Debt.objects.create(
                        user=request.user,
                        amount=meeting.facilitation_fee,
                        description=f'Meeting facilitation fee - {meeting.title} ({meeting.date.strftime("%Y-%m-%d")})'
                    )
                    
                    return redirect('meetings_list')
    else:
        form = MeetingResponseForm()
    
    context = {
        'form': form,
        'meeting': meeting,
    }
    return render(request, 'meetings/respond.html', context)

@login_required
def pay_facilitation_view(request, attendance_id):
    if request.user.is_admin:
        return redirect('admin_meetings')
    
    attendance = get_object_or_404(MeetingAttendance, id=attendance_id, member=request.user)
    
    if attendance.payment_status == 'paid':
        return redirect('meetings_list')
    
    if request.method == 'POST':
        form = FacilitationPaymentForm(request.POST)
        if form.is_valid():
            payment_mode = form.cleaned_data['payment_mode']
            mpesa_phone = form.cleaned_data.get('mpesa_phone', '')
            
            idempotency_key = str(uuid.uuid4())
            
            if payment_mode == 'cash':
                payment = MeetingFacilitationPayment.objects.create(
                    attendance=attendance,
                    amount=attendance.meeting.facilitation_fee,
                    payment_mode='cash',
                    idempotency_key=idempotency_key,
                    status='pending'
                )
                attendance.payment_status = 'pending'
                attendance.facilitation_paid = Decimal('0')
                attendance.save()
                return redirect('meetings_list')
            
            elif payment_mode == 'mpesa':
                payment = MeetingFacilitationPayment.objects.create(
                    attendance=attendance,
                    amount=attendance.meeting.facilitation_fee,
                    payment_mode='mpesa',
                    mpesa_phone=mpesa_phone,
                    idempotency_key=idempotency_key,
                    status='pending'
                )
                
                response = initiate_stk_push(
                    mpesa_phone, 
                    int(attendance.meeting.facilitation_fee), 
                    idempotency_key
                )
                
                if response.get('ResponseCode') == '0':
                    payment.merchant_request_id = response.get('MerchantRequestID')
                    payment.checkout_request_id = response.get('CheckoutRequestID')
                    payment.save()
                    attendance.payment_status = 'pending'
                    attendance.save()
                    return redirect('facilitation_payment_pending', payment_id=payment.id)
                else:
                    payment.status = 'failed'
                    payment.save()
                    return render(request, 'meetings/payment_failed.html', {'error': 'Payment initiation failed'})
    else:
        form = FacilitationPaymentForm()
    
    context = {
        'form': form,
        'attendance': attendance,
        'meeting': attendance.meeting,
        'amount': attendance.meeting.facilitation_fee,
    }
    return render(request, 'meetings/pay_facilitation.html', context)

@login_required
def facilitation_payment_pending_view(request, payment_id):
    payment = get_object_or_404(MeetingFacilitationPayment, id=payment_id, attendance__member=request.user)
    
    if payment.status == 'completed':
        return redirect('facilitation_payment_success', payment_id=payment.id)
    elif payment.status == 'failed':
        return redirect('facilitation_payment_failed', payment_id=payment.id)
    
    context = {
        'payment': payment,
        'meeting': payment.attendance.meeting,
    }
    return render(request, 'meetings/payment_pending.html', context)

@login_required
def check_facilitation_status_view(request, payment_id):
    payment = get_object_or_404(MeetingFacilitationPayment, id=payment_id, attendance__member=request.user)
    
    if payment.checkout_request_id:
        status_response = query_transaction_status(payment.checkout_request_id)
        
        if status_response.get('ResultCode') == '0':
            with transaction.atomic():
                payment.status = 'completed'
                payment.completed_at = timezone.now()
                payment.save()
                
                attendance = payment.attendance
                attendance.payment_status = 'paid'
                attendance.facilitation_paid = payment.amount
                attendance.save()
                
                return JsonResponse({'status': 'completed'})
        elif status_response.get('ResultCode'):
            payment.status = 'failed'
            payment.save()
            
            attendance = payment.attendance
            attendance.payment_status = 'unpaid'
            attendance.save()
            
            from apps.members.models import Debt
            Debt.objects.create(
                user=request.user,
                amount=payment.attendance.meeting.facilitation_fee,
                description=f'Meeting facilitation fee - {payment.attendance.meeting.title}'
            )
            
            return JsonResponse({'status': 'failed'})
    
    return JsonResponse({'status': payment.status})

@login_required
def facilitation_payment_success_view(request, payment_id):
    payment = get_object_or_404(MeetingFacilitationPayment, id=payment_id, attendance__member=request.user)
    return render(request, 'meetings/payment_success.html', {'payment': payment})

@login_required
def facilitation_payment_failed_view(request, payment_id):
    payment = get_object_or_404(MeetingFacilitationPayment, id=payment_id, attendance__member=request.user)
    return render(request, 'meetings/payment_failed.html', {'payment': payment})