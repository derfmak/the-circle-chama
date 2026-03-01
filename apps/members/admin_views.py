import secrets
import string
from datetime import timedelta, date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.core.mail import send_mail
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.conf import settings
from django.http import JsonResponse
from apps.accounts.models import User, PasswordResetCode
from apps.members.models import MemberProfile, ContributionType, Contribution, PaymentTransaction
from apps.meetings.models import Meeting, MeetingAttendance
from apps.payments.mpesa import initiate_stk_push
import re
from .models import MemberProfile, ContributionType, Contribution, PaymentTransaction, CashPaymentRequest

MONTHS = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April',
    5: 'May', 6: 'June', 7: 'July', 8: 'August',
    9: 'September', 10: 'October', 11: 'November', 12: 'December'
}

admin_required = lambda view: login_required(user_passes_test(lambda u: u.is_admin)(view))

def generate_secure_password(length=16):
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in '!@#$%^&*' for c in password)):
            return password

def generate_reset_code():
    return ''.join(secrets.choice(string.digits) for _ in range(6))

def admin_login_view(request):
    if request.user.is_authenticated and request.user.is_admin:
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        
        if user is not None and user.is_admin:
            login(request, user)
            if not user.password_changed:
                return redirect('admin_initial_password_change')
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid email or password')
    
    return render(request, 'admin/admin_login.html')

def admin_forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email, is_admin=True)
            code = generate_reset_code()
            expires_at = timezone.now() + timedelta(minutes=30)
            
            PasswordResetCode.objects.create(
                user=user,
                code=code,
                expires_at=expires_at
            )
            
            send_mail(
                subject='Password Reset Code - THE CIRCLE Admin',
                message=f'''Your password reset code is: {code}
                
This code will expire in 30 minutes.

If you did not request this reset, please ignore this email.

THE CIRCLE Admin''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            
            request.session['reset_email'] = email
            messages.success(request, 'Reset code sent to your email.')
            return redirect('admin_verify_code')
            
        except User.DoesNotExist:
            messages.error(request, 'No admin account found with this email.')
    
    return render(request, 'admin/admin_forgot_password.html')

def admin_verify_code_view(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('admin_forgot_password')
    
    if request.method == 'POST':
        code = request.POST.get('code')
        try:
            reset_code = PasswordResetCode.objects.get(
                user__email=email,
                code=code,
                used=False,
                expires_at__gt=timezone.now()
            )
            request.session['reset_code_id'] = reset_code.id
            return redirect('admin_reset_password')
        except PasswordResetCode.DoesNotExist:
            messages.error(request, 'Invalid or expired code.')
    
    return render(request, 'admin/admin_verify_code.html')

def admin_reset_password_view(request):
    code_id = request.session.get('reset_code_id')
    if not code_id:
        return redirect('admin_forgot_password')
    
    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'admin/admin_reset_password.html')
        
        if len(password) < 12:
            messages.error(request, 'Password must be at least 12 characters.')
            return render(request, 'admin/admin_reset_password.html')
        
        try:
            reset_code = PasswordResetCode.objects.get(id=code_id, used=False)
            with transaction.atomic():
                reset_code.user.set_password(password)
                reset_code.user.password_changed = True
                reset_code.user.save()
                reset_code.used = True
                reset_code.save()
            
            del request.session['reset_email']
            del request.session['reset_code_id']
            
            messages.success(request, 'Password reset successful. Please login.')
            return redirect('admin_login')
            
        except PasswordResetCode.DoesNotExist:
            messages.error(request, 'Invalid reset request.')
            return redirect('admin_forgot_password')
    
    return render(request, 'admin/admin_reset_password.html')

def admin_initial_password_change_view(request):
    if not request.user.is_authenticated or not request.user.is_admin:
        return redirect('admin_login')
    
    if request.user.password_changed:
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'admin/admin_initial_password_change.html')
        
        if len(password) < 12:
            messages.error(request, 'Password must be at least 12 characters.')
            return render(request, 'admin/admin_initial_password_change.html')
        
        request.user.set_password(password)
        request.user.password_changed = True
        request.user.save()
        update_session_auth_hash(request, request.user)
        
        messages.success(request, 'Password changed successfully.')
        return redirect('admin_dashboard')
    
    return render(request, 'admin/admin_initial_password_change.html')

def admin_logout_view(request):
    logout(request)
    return redirect('admin_login')

@admin_required
def admin_dashboard_view(request):
    total_members = User.objects.filter(is_admin=False, is_active=True).count()
    
    total_contributions = Contribution.objects.filter(
        status__in=['paid', 'paid_late']
    ).aggregate(total=Sum('amount_paid'))['total'] or 0
    
    monthly_contributions = Contribution.objects.filter(
        contribution_type__contribution_type='monthly',
        status__in=['paid', 'paid_late']
    ).aggregate(total=Sum('amount_paid'))['total'] or 0
    
    quarterly_contributions = Contribution.objects.filter(
        contribution_type__contribution_type='quarterly',
        status__in=['paid', 'paid_late']
    ).aggregate(total=Sum('amount_paid'))['total'] or 0
    
    total_meetings = Meeting.objects.filter(status='completed').count()
    
    attendance_rate = 0
    if total_meetings > 0:
        total_attendances = MeetingAttendance.objects.filter(status='accepted').count()
        total_possible = MeetingAttendance.objects.count()
        if total_possible > 0:
            attendance_rate = (total_attendances / total_possible) * 100
    
    recent_members = User.objects.filter(is_admin=False).order_by('-date_joined')[:5]
    
    context = {
        'total_members': total_members,
        'total_contributions': total_contributions,
        'monthly_contributions': monthly_contributions,
        'quarterly_contributions': quarterly_contributions,
        'total_meetings': total_meetings,
        'attendance_rate': round(attendance_rate, 2),
        'recent_members': recent_members,
    }
    return render(request, 'admin/dashboard.html', context)

@admin_required
def admin_members_list_view(request):
    members_list = User.objects.filter(is_admin=False).order_by('-date_joined')
    paginator = Paginator(members_list, 20)
    page_number = request.GET.get('page')
    members = paginator.get_page(page_number)
    context = {
        'members': members,
        'page_obj': members,
    }
    return render(request, 'admin/members_list.html', context)

@admin_required
def admin_create_member_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone_number = request.POST.get('phone_number', '').strip().replace(' ', '').replace('-', '')
        id_number = request.POST.get('id_number', '').strip()
        date_joined_str = request.POST.get('date_joined', '').strip()
        
        errors = []
        
        if not first_name or len(first_name) < 2:
            errors.append('First name must be at least 2 characters.')
        
        if not last_name or len(last_name) < 2:
            errors.append('Last name must be at least 2 characters.')
        
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not email or not re.match(email_regex, email):
            errors.append('Valid email is required.')
        elif User.objects.filter(email=email).exists():
            errors.append('Email already exists.')
        
        phone_valid = False
        if re.match(r'^254[17]\d{8}$', phone_number):
            phone_valid = True
        elif re.match(r'^01\d{8}$', phone_number):
            phone_valid = True
            phone_number = '254' + phone_number[1:]
        elif re.match(r'^07\d{8}$', phone_number):
            phone_valid = True
            phone_number = '254' + phone_number[1:]
        
        if not phone_valid:
            errors.append('Phone number must be 2547XXXXXXXX, 01XXXXXXXX, or 07XXXXXXXX (10 digits).')
        elif User.objects.filter(phone_number=phone_number).exists():
            errors.append('Phone number already exists.')
        
        if not id_number:
            errors.append('ID number is required.')
        elif not id_number.isdigit():
            errors.append('ID number must contain only digits.')
        elif len(id_number) != 8:
            errors.append('ID number must be exactly 8 digits.')
        elif User.objects.filter(id_number=id_number).exists():
            errors.append('ID number already exists.')
        
        join_date = timezone.now().date()
        if date_joined_str:
            try:
                join_date = timezone.datetime.strptime(date_joined_str, '%Y-%m-%d').date()
                if join_date > timezone.now().date():
                    errors.append('Date joined cannot be in the future.')
            except ValueError:
                errors.append('Invalid date format. Use YYYY-MM-DD.')
        
        if errors:
            return render(request, 'admin/create_member.html', {'errors': errors, 'data': request.POST})
        
        try:
            with transaction.atomic():
                password = generate_secure_password()
                
                user = User.objects.create_user(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=phone_number,
                    id_number=id_number,
                    password=password,
                    password_changed=False,
                    password_expires_at=timezone.now() + timedelta(hours=24)
                )
                
                if date_joined_str:
                    user.date_joined = timezone.datetime.strptime(date_joined_str, '%Y-%m-%d')
                else:
                    user.date_joined = timezone.now()
                user.save()
                
                MemberProfile.objects.create(user=user)
                
                if join_date < timezone.now().date():
                    monthly_type = ContributionType.objects.filter(contribution_type='monthly').first()
                    if monthly_type:
                        start_date = join_date.replace(day=1)
                        end_date = timezone.now().date().replace(day=1)
                        
                        current = start_date
                        while current <= end_date:
                            Contribution.objects.create(
                                user=user,
                                contribution_type=monthly_type,
                                month=current.month,
                                year=current.year,
                                amount_due=monthly_type.amount,
                                amount_paid=0,
                                fine_amount=0,
                                status='pending'
                            )
                            
                            if current.month == 12:
                                current = current.replace(year=current.year + 1, month=1)
                            else:
                                current = current.replace(month=current.month + 1)
                
                send_mail(
                    subject='Welcome to THE CIRCLE - Login Credentials',
                    message=f'''Welcome to THE CIRCLE Chama!
                    
Your account has been created. Here are your login credentials:

Email: {email}
Temporary Password: {password}

Please login at http://127.0.0.1:8000/login/ and change your password immediately.
This password expires in 24 hours.

Best regards,
THE CIRCLE Admin''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                
                messages.success(request, f'Member {first_name} {last_name} created successfully. Login credentials sent to {email}.')
                return redirect('admin_members_list')
                
        except Exception as e:
            return render(request, 'admin/create_member.html', {'errors': [str(e)], 'data': request.POST})
    
    context = {
        'now': timezone.now()
    }
    return render(request, 'admin/create_member.html', context)

@admin_required
def admin_edit_member_view(request, member_id):
    member = get_object_or_404(User, id=member_id, is_admin=False)
    
    if request.method == 'POST':
        member.first_name = request.POST.get('first_name', member.first_name).strip()
        member.last_name = request.POST.get('last_name', member.last_name).strip()
        phone_number = request.POST.get('phone_number', member.phone_number).strip().replace(' ', '').replace('-', '')
        
        phone_valid = False
        if re.match(r'^254[17]\d{8}$', phone_number):
            phone_valid = True
        elif re.match(r'^01\d{8}$', phone_number):
            phone_number = '254' + phone_number[1:]
            phone_valid = True
        elif re.match(r'^07\d{8}$', phone_number):
            phone_number = '254' + phone_number[1:]
            phone_valid = True
        
        if not phone_valid:
            messages.error(request, 'Invalid phone number format.')
            return redirect('admin_edit_member', member_id=member.id)
        
        member.phone_number = phone_number
        member.is_active = request.POST.get('is_active') == 'on'
        
        profile = member.memberprofile
        profile.is_dropped = request.POST.get('is_dropped') == 'on'
        if profile.is_dropped and not profile.dropped_at:
            profile.dropped_at = timezone.now()
        elif not profile.is_dropped:
            profile.dropped_at = None
        
        member.save()
        profile.save()
        
        messages.success(request, 'Member updated successfully.')
        return redirect('admin_members_list')
    
    context = {
        'member': member,
    }
    return render(request, 'admin/edit_member.html', context)

@admin_required
def admin_delete_member_view(request, member_id):
    member = get_object_or_404(User, id=member_id, is_admin=False)
    
    if request.method == 'POST':
        member.is_active = False
        member.save()
        messages.success(request, 'Member deactivated successfully.')
        return redirect('admin_members_list')
    
    context = {
        'member': member,
    }
    return render(request, 'admin/delete_member.html', context)

@admin_required
def admin_contributions_view(request):
    contribution_types = ContributionType.objects.filter(is_active=True)
    selected_type = request.GET.get('type')
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    contributions = Contribution.objects.select_related(
        'user', 'contribution_type'
    ).filter(
        status__in=['paid', 'paid_late', 'partial', 'waiting_approval', 'rejected']
    ).order_by('-year', '-month')
    
    if selected_type:
        contributions = contributions.filter(contribution_type_id=selected_type)
    if status:
        contributions = contributions.filter(status=status)
    if search:
        contributions = contributions.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    contribution_list = []
    for c in contributions:
        month_name = MONTHS.get(c.month, '') if c.month else ''
        contribution_list.append({
            'id': c.id,
            'user': c.user,
            'contribution_type': c.contribution_type,
            'year': c.year,
            'month': c.month,
            'month_name': month_name,
            'quarter': c.quarter,
            'amount_due': c.amount_due,
            'fine_amount': c.fine_amount,
            'amount_paid': c.amount_paid,
            'status': c.status,
            'paid_at': c.paid_at,
            'is_late': c.is_late,
            'get_status_display': c.get_status_display(),
        })
    
    paginator = Paginator(contribution_list, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'contribution_types': contribution_types,
        'contributions': page_obj,
        'page_obj': page_obj,
        'selected_type': selected_type,
        'status': status,
        'search': search,
        'MONTHS': MONTHS,
    }
    return render(request, 'admin/contributions.html', context)

@admin_required
def admin_create_contribution_type_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        contribution_type = request.POST.get('contribution_type', '').strip()
        amount = request.POST.get('amount', '0').strip()
        description = request.POST.get('description', '').strip()
        deadline_day = request.POST.get('deadline_day', '').strip() or None
        
        if not name or not contribution_type or not amount:
            messages.error(request, 'All required fields must be filled.')
            return render(request, 'admin/create_contribution_type.html')
        
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            messages.error(request, 'Invalid amount.')
            return render(request, 'admin/create_contribution_type.html')
        
        ContributionType.objects.create(
            name=name,
            contribution_type=contribution_type,
            amount=amount,
            description=description,
            deadline_day=int(deadline_day) if deadline_day else None
        )
        
        messages.success(request, 'Contribution type created successfully.')
        return redirect('admin_contributions')
    
    return render(request, 'admin/create_contribution_type.html')

@admin_required
def admin_edit_contribution_view(request, contribution_id):
    contribution = get_object_or_404(Contribution, id=contribution_id)
    
    if request.method == 'POST':
        amount_due = request.POST.get('amount_due', '').strip()
        fine_amount = request.POST.get('fine_amount', '').strip()
        status = request.POST.get('status', '').strip()
        
        try:
            with transaction.atomic():
                if amount_due:
                    contribution.amount_due = float(amount_due)
                if fine_amount:
                    contribution.fine_amount = float(fine_amount)
                if status:
                    contribution.status = status
                
                contribution.save()
                messages.success(request, 'Contribution updated successfully.')
                return redirect('admin_contributions')
        except Exception as e:
            messages.error(request, str(e))
    
    context = {
        'contribution': contribution,
    }
    return render(request, 'admin/edit_contribution.html', context)

@admin_required
def admin_review_cash_request_view(request, payment_id):
    payment = get_object_or_404(CashPaymentRequest, id=payment_id)
    return redirect('admin_payment_approval')

@admin_required
def admin_payment_approval_view(request):
    view_type = request.GET.get('view', 'pending')
    
    if view_type == 'reapproval':
        payments = CashPaymentRequest.objects.filter(
            contribution__status='waiting_reapproval'
        ).select_related('user', 'contribution').order_by('-created_at')
    elif view_type == 'history':
        payments = CashPaymentRequest.objects.filter(
            status__in=['approved', 'declined']
        ).select_related('user', 'contribution', 'reviewed_by').order_by('-reviewed_at')
    else:
        payments = CashPaymentRequest.objects.filter(
            status='pending'
        ).select_related('user', 'contribution').order_by('-created_at')
    
    if request.method == 'POST':
        payment_id = request.POST.get('payment_id')
        action = request.POST.get('action')
        admin_notes = request.POST.get('admin_notes', '')
        
        try:
            payment = CashPaymentRequest.objects.select_for_update().get(
                id=payment_id
            )
        except CashPaymentRequest.DoesNotExist:
            messages.error(request, 'Payment request does not exist.')
            return redirect('admin_payment_approval')
        
        with transaction.atomic():
            if action == 'approve':
                payment.status = 'approved'
                payment.admin_notes = admin_notes
                payment.reviewed_at = timezone.now()
                payment.reviewed_by = request.user
                payment.save()
                
                if payment.contribution:
                    contribution = payment.contribution
                    contribution.amount_paid += payment.amount
                    
                    total_due = contribution.amount_due + contribution.fine_amount
                    
                    if contribution.amount_paid >= total_due:
                        contribution.status = 'paid_late' if contribution.is_late else 'paid'
                        contribution.paid_at = timezone.now()
                    else:
                        contribution.status = 'partial'
                    
                    contribution.save()
                
                messages.success(request, 'Payment approved successfully.')
                
            elif action == 'reject':
                payment.status = 'declined'
                payment.admin_notes = admin_notes
                payment.reviewed_at = timezone.now()
                payment.reviewed_by = request.user
                payment.save()
                
                if payment.contribution:
                    contribution = payment.contribution
                    contribution.status = 'rejected'
                    contribution.save()
                
                messages.info(request, 'Payment rejected.')
        
        return redirect('admin_payment_approval')
    
    paginator = Paginator(payments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    pending_count = CashPaymentRequest.objects.filter(status='pending').count()
    reapproval_count = CashPaymentRequest.objects.filter(contribution__status='waiting_reapproval').count()
    history_count = CashPaymentRequest.objects.filter(status__in=['approved', 'declined']).count()
    
    context = {
        'payments': page_obj,
        'page_obj': page_obj,
        'view_type': view_type,
        'pending_count': pending_count,
        'reapproval_count': reapproval_count,
        'history_count': history_count,
    }
    return render(request, 'admin/payment_approval.html', context)
    
    paginator = Paginator(payments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    pending_count = CashPaymentRequest.objects.filter(status='pending').count()
    history_count = CashPaymentRequest.objects.filter(status__in=['approved', 'declined']).count()
    
    context = {
        'payments': page_obj,
        'page_obj': page_obj,
        'view_type': view_type,
        'pending_count': pending_count,
        'history_count': history_count,
    }
    return render(request, 'admin/payment_approval.html', context)

@admin_required
def admin_contribution_report_view(request):
    selected_year = request.GET.get('year', timezone.now().year)
    selected_month = request.GET.get('month', '')
    selected_member = request.GET.get('member', '')
    member_search = request.GET.get('member_search', '')
    status_filter = request.GET.get('status', '')
    
    today = timezone.now().date()
    current_year = today.year
    current_month = today.month
    
    years = Contribution.objects.values_list('year', flat=True).distinct().order_by('-year')
    months = range(1, 13)
    
    base_contributions = Contribution.objects.select_related(
        'user', 'contribution_type'
    ).filter(
        contribution_type__contribution_type__in=['monthly', 'quarterly']
    )
    
    if status_filter:
        base_contributions = base_contributions.filter(status=status_filter)
    
    if selected_year:
        base_contributions = base_contributions.filter(year=selected_year)
    
    if selected_member:
        base_contributions = base_contributions.filter(user_id=selected_member)
    elif member_search:
        base_contributions = base_contributions.filter(
            Q(user__first_name__icontains=member_search) |
            Q(user__last_name__icontains=member_search) |
            Q(user__email__icontains=member_search)
        )
    
    contribution_list = []
    
    for contribution in base_contributions:
        include = False
        
        if contribution.status in ['paid', 'paid_late', 'partial']:
            include = True
        elif contribution.status == 'pending':
            if contribution.contribution_type.contribution_type == 'monthly' and contribution.month:
                if contribution.year < current_year:
                    include = True
                elif contribution.year == current_year and contribution.month < current_month:
                    include = True
                elif contribution.year == current_year and contribution.month == current_month and today.day > 10:
                    include = True
            elif contribution.contribution_type.contribution_type == 'quarterly':
                include = True
        
        if include:
            contribution.total_due = contribution.amount_due + contribution.fine_amount
            
            if contribution.status in ['paid', 'paid_late', 'partial']:
                payment = PaymentTransaction.objects.filter(
                    contribution=contribution,
                    status='completed'
                ).first()
                if payment:
                    contribution.payment_method = payment.payment_mode
                    contribution.mpesa_receipt = payment.mpesa_receipt
                else:
                    cash_request = CashPaymentRequest.objects.filter(
                        contribution=contribution,
                        status='approved'
                    ).first()
                    if cash_request:
                        contribution.payment_method = 'cash'
                        contribution.mpesa_receipt = 'Cash'
            
            contribution_list.append(contribution)
    
    if selected_month:
        contribution_list = [
            c for c in contribution_list 
            if c.contribution_type.contribution_type != 'monthly' or c.month == int(selected_month)
        ]
    
    paginator = Paginator(contribution_list, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    total_expected = sum(c.amount_due for c in contribution_list)
    total_collected = sum(c.amount_paid for c in contribution_list if c.status in ['paid', 'paid_late', 'partial'])
    total_fines = sum(c.fine_amount for c in contribution_list if c.status in ['paid', 'paid_late', 'partial'])
    
    collection_rate = 0
    if total_expected > 0:
        collection_rate = (total_collected / total_expected) * 100
    
    context = {
        'contributions': page_obj,
        'page_obj': page_obj,
        'years': years,
        'months': months,
        'year': int(selected_year) if selected_year else None,
        'month': int(selected_month) if selected_month else None,
        'member_search': member_search,
        'selected_member_id': selected_member,
        'status': status_filter,
        'total_expected': total_expected,
        'total_collected': total_collected,
        'total_fines': total_fines,
        'collection_rate': round(collection_rate, 2),
    }
    return render(request, 'admin/contribution_report.html', context)