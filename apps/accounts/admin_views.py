import secrets
import string
from datetime import timedelta
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
from .models import User, PasswordResetCode, LoginSession
from apps.members.models import MemberProfile, ContributionType, Contribution
from .forms import AdminLoginForm, AdminForgotPasswordForm, AdminVerifyCodeForm, AdminResetPasswordForm, AdminInitialPasswordChangeForm

def admin_required(view_func):
    return login_required(user_passes_test(lambda u: u.is_admin)(view_func))

def validate_admin_session(request):
    if not request.user.is_authenticated:
        return False
    if not request.user.is_admin:
        logout(request)
        return False
    return True

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
    if request.user.is_authenticated:
        if request.user.is_admin:
            return redirect('admin_dashboard')
        logout(request)
        return redirect('admin_login')
    
    if request.method == 'POST':
        form = AdminLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            LoginSession.objects.filter(user=user, is_active=True).update(is_active=False)
            login(request, user)
            create_login_session(request, user)
            if not user.password_changed:
                return redirect('admin_initial_password_change')
            return redirect('admin_dashboard')
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = AdminLoginForm()
    
    return render(request, 'admin/admin_login.html', {'form': form})

def create_login_session(request, user):
    from apps.accounts.models import LoginSession
    session_key = request.session.session_key
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    LoginSession.objects.create(
        user=user,
        session_key=session_key,
        ip_address=ip,
        user_agent=user_agent,
        is_active=True
    )

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def admin_forgot_password_view(request):
    if request.method == 'POST':
        form = AdminForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
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
    else:
        form = AdminForgotPasswordForm()
    
    return render(request, 'admin/admin_forgot_password.html', {'form': form})

def admin_verify_code_view(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('admin_forgot_password')
    
    if request.method == 'POST':
        form = AdminVerifyCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
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
    else:
        form = AdminVerifyCodeForm()
    
    return render(request, 'admin/admin_verify_code.html', {'form': form})

def admin_reset_password_view(request):
    code_id = request.session.get('reset_code_id')
    if not code_id:
        return redirect('admin_forgot_password')
    
    if request.method == 'POST':
        form = AdminResetPasswordForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']
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
    else:
        form = AdminResetPasswordForm()
    
    return render(request, 'admin/admin_reset_password.html', {'form': form})

def admin_initial_password_change_view(request):
    if not validate_admin_session(request):
        return redirect('admin_login')
    
    if request.user.password_changed:
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        form = AdminInitialPasswordChangeForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']
            request.user.set_password(password)
            request.user.password_changed = True
            request.user.save()
            update_session_auth_hash(request, request.user)
            
            messages.success(request, 'Password changed successfully.')
            return redirect('admin_dashboard')
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = AdminInitialPasswordChangeForm()
    
    return render(request, 'admin/admin_initial_password_change.html', {'form': form})

def admin_logout_view(request):
    from apps.accounts.models import LoginSession
    LoginSession.objects.filter(
        user=request.user,
        session_key=request.session.session_key
    ).update(is_active=False)
    logout(request)
    return redirect('admin_login')

@admin_required
def admin_dashboard_view(request):
    if not validate_admin_session(request):
        return redirect('admin_login')
    
    total_members = User.objects.filter(is_admin=False, is_active=True).count()
    
    from apps.members.models import Contribution
    from apps.meetings.models import Meeting, MeetingAttendance
    from apps.message.models import ContactMessage
    
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
    new_messages_count = ContactMessage.objects.filter(status='new').count()
    recent_messages = ContactMessage.objects.order_by('-created_at')[:5]
    
    context = {
        'total_members': total_members,
        'total_contributions': total_contributions,
        'monthly_contributions': monthly_contributions,
        'quarterly_contributions': quarterly_contributions,
        'total_meetings': total_meetings,
        'attendance_rate': round(attendance_rate, 2),
        'recent_members': recent_members,
        'new_messages_count': new_messages_count,
        'recent_messages': recent_messages,
    }
    return render(request, 'admin/dashboard.html', context)

@admin_required
def admin_members_list_view(request):
    if not validate_admin_session(request):
        return redirect('admin_login')
    
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
    if not validate_admin_session(request):
        return redirect('admin_login')
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone_number = request.POST.get('phone_number', '').strip()
        id_number = request.POST.get('id_number', '').strip()
        date_joined_str = request.POST.get('date_joined', '').strip()
        
        errors = []
        
        if not first_name or len(first_name) < 2:
            errors.append('First name must be at least 2 characters.')
        if not last_name or len(last_name) < 2:
            errors.append('Last name must be at least 2 characters.')
        if not email or '@' not in email:
            errors.append('Valid email is required.')
        if User.objects.filter(email=email).exists():
            errors.append('Email already exists.')
        if not phone_number or len(phone_number) < 10:
            errors.append('Valid phone number is required.')
        if not id_number:
            errors.append('ID number is required.')
        if User.objects.filter(id_number=id_number).exists():
            errors.append('ID number already exists.')
        
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
                    naive_date = timezone.datetime.strptime(date_joined_str, '%Y-%m-%d')
                    user.date_joined = timezone.make_aware(naive_date)
                    user.save()
                
                MemberProfile.objects.create(user=user)
                
                send_mail(
                    subject='Welcome to THE CIRCLE - Login Credentials',
                    message=f'''Welcome to THE CIRCLE Chama!
                    
Your account has been created. Here are your login credentials:

Email: {email}
Temporary Password: {password}

Please login at https://your-domain.com/login/ and change your password immediately.
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
    
    return render(request, 'admin/create_member.html')

@admin_required
def admin_edit_member_view(request, member_id):
    if not validate_admin_session(request):
        return redirect('admin_login')
    
    member = get_object_or_404(User, id=member_id, is_admin=False)
    
    if request.method == 'POST':
        member.first_name = request.POST.get('first_name', member.first_name).strip()
        member.last_name = request.POST.get('last_name', member.last_name).strip()
        member.phone_number = request.POST.get('phone_number', member.phone_number).strip()
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
    if not validate_admin_session(request):
        return redirect('admin_login')
    
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