import secrets
import string
import re
import os
from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction, models
from django.conf import settings
from django.core.files.images import get_image_dimensions
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from .models import User, PasswordResetCode, LoginSession, MemberApplication
from .forms import (
    MemberLoginForm, AdminLoginForm, PasswordChangeForm,
    InitialPasswordChangeForm, ForgotPasswordForm,
    ResetCodeForm, ResetPasswordForm, MemberApplicationForm
)
from .utils import rate_limit, get_client_ip, log_security_event
from apps.members.models import Contribution

User = get_user_model()


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


def home_view(request):
    total_members = User.objects.filter(is_admin=False, is_active=True).count()

    total_pooled = Contribution.objects.filter(
        status__in=['paid', 'paid_late']
    ).aggregate(total=models.Sum('amount_paid'))['total'] or 0

    oldest_member = User.objects.filter(is_admin=False, is_active=True).order_by('date_joined').first()
    if oldest_member:
        years_strong = timezone.now().year - oldest_member.date_joined.year
        if years_strong < 1:
            years_strong = 1
    else:
        years_strong = 7

    current_month = timezone.now().month
    current_year = timezone.now().year
    monthly_total = Contribution.objects.filter(
        status__in=['paid', 'paid_late'],
        month=current_month,
        year=current_year
    ).aggregate(total=models.Sum('amount_paid'))['total'] or 0

    monthly_contributors = Contribution.objects.filter(
        status__in=['paid', 'paid_late'],
        month=current_month,
        year=current_year
    ).values('user').distinct().count()

    context = {
        'total_members': total_members,
        'total_pooled': total_pooled,
        'years_strong': years_strong,
        'monthly_total': monthly_total,
        'monthly_contributors': monthly_contributors,
    }
    return render(request, 'public/home.html', context)


def about_view(request):
    total_members = User.objects.filter(is_admin=False, is_active=True).count()

    total_pooled = Contribution.objects.filter(
        status__in=['paid', 'paid_late']
    ).aggregate(total=models.Sum('amount_paid'))['total'] or 0

    oldest_member = User.objects.filter(is_admin=False, is_active=True).order_by('date_joined').first()
    if oldest_member:
        years_strong = timezone.now().year - oldest_member.date_joined.year
        if years_strong < 1:
            years_strong = 1
    else:
        years_strong = 7

    context = {
        'total_members': total_members,
        'total_pooled': total_pooled,
        'years_strong': years_strong,
    }
    return render(request, 'public/about.html', context)


def contact_view(request):
    return render(request, 'public/contact.html')


def privacy_view(request):
    return render(request, 'public/privacy.html')


def terms_view(request):
    return render(request, 'public/terms.html')


def validate_user_session(request, expected_is_admin):
    if not request.user.is_authenticated:
        return None
    if request.user.is_admin != expected_is_admin:
        logout(request)
        return False
    return True


@rate_limit(limit=5, period=60)
def member_login_view(request):
    if request.user.is_authenticated:
        if request.user.is_admin:
            logout(request)
            return redirect('login')
        return redirect('member_dashboard')

    if request.method == 'POST':
        form = MemberLoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)

            if user is not None and not user.is_admin:
                LoginSession.objects.filter(user=user, is_active=True).update(is_active=False)

                if not user.password_changed:
                    login(request, user)
                    request.session['require_password_change'] = True
                    return redirect('initial_password_change')

                login(request, user)
                create_login_session(request, user)
                log_security_event(request, 'login_success', user)
                return redirect('member_dashboard')

            log_security_event(request, 'login_failed', email)
    else:
        form = MemberLoginForm()

    return render(request, 'public/login.html', {'form': form, 'is_admin': False})


@rate_limit(limit=5, period=60)
def admin_login_view(request):
    if request.user.is_authenticated:
        if not request.user.is_admin:
            logout(request)
            return redirect('admin_login')
        return redirect('admin_dashboard')

    if request.method == 'POST':
        form = AdminLoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)

            if user is not None and user.is_admin:
                LoginSession.objects.filter(user=user, is_active=True).update(is_active=False)

                if not user.password_changed:
                    login(request, user)
                    request.session['require_password_change'] = True
                    return redirect('admin_initial_password_change')

                login(request, user)
                create_login_session(request, user)
                log_security_event(request, 'admin_login_success', user)
                return redirect('admin_dashboard')

            log_security_event(request, 'admin_login_failed', email)
    else:
        form = AdminLoginForm()

    return render(request, 'public/admin_login.html', {'form': form})


def create_login_session(request, user):
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


@csrf_protect
@require_http_methods(["GET", "POST"])
def become_member_view(request):
    if request.method == 'POST':
        form = MemberApplicationForm(request.POST)

        if form.is_valid():
            full_name = form.cleaned_data.get('full_name')
            id_number = form.cleaned_data.get('id_number')
            phone_number = form.cleaned_data.get('phone_number')
            email = form.cleaned_data.get('email')
            agree_terms = form.cleaned_data.get('agree_terms')
            agree_privacy = form.cleaned_data.get('agree_privacy')

            if not agree_terms or not agree_privacy:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'You must agree to both the Terms of Service and Privacy Policy.'
                    }, status=400)
                messages.error(request, 'You must agree to both the Terms of Service and Privacy Policy.')
                return render(request, 'public/become_member.html', {'form': form})

            if User.objects.filter(email=email).exists():
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'errors': {'email': ['This email is already registered.']}
                    }, status=400)
                messages.error(request, 'This email is already registered.')
                return render(request, 'public/become_member.html', {'form': form})

            if User.objects.filter(phone_number=phone_number).exists():
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'errors': {'phone_number': ['This phone number is already registered.']}
                    }, status=400)
                messages.error(request, 'This phone number is already registered.')
                return render(request, 'public/become_member.html', {'form': form})

            if User.objects.filter(id_number=id_number).exists():
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'errors': {'id_number': ['This ID number is already registered.']}
                    }, status=400)
                messages.error(request, 'This ID number is already registered.')
                return render(request, 'public/become_member.html', {'form': form})

            if MemberApplication.objects.filter(email=email, status='pending').exists():
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'You already have a pending application. Please wait for review.'
                    }, status=400)
                messages.warning(request, 'You already have a pending application. Please wait for review.')
                return render(request, 'public/become_member.html', {'form': form})

            if MemberApplication.objects.filter(id_number=id_number, status='pending').exists():
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'An application with this ID number is already pending review.'
                    }, status=400)
                messages.warning(request, 'An application with this ID number is already pending review.')
                return render(request, 'public/become_member.html', {'form': form})

            application = MemberApplication.objects.create(
                full_name=full_name,
                id_number=id_number,
                phone_number=phone_number,
                email=email,
                agreed_to_terms=agree_terms,
                agreed_to_privacy=agree_privacy,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

            try:
                from django.core.mail import send_mail
                send_mail(
                    subject='Elites Pioneer Club - Application Received',
                    message=f'''Dear {full_name},

Thank you for applying to join Elites Pioneer Club.

Your application has been received and is currently being reviewed by the committee.

Application Reference: #{application.id}

You will receive a follow-up email once your application has been reviewed.

If you have any questions, please contact us at: {settings.ADMIN_EMAIL}

Best regards,
Elites Pioneer Club Committee''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )

                send_mail(
                    subject='New Member Application - Elites Pioneer Club',
                    message=f'''A new membership application has been submitted.

Applicant: {full_name}
Email: {email}
Phone: {phone_number}
ID Number: {id_number}
Application ID: #{application.id}

Please review this application in the admin panel.

Best regards,
Elites Pioneer Club System''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.ADMIN_EMAIL],
                    fail_silently=True,
                )
            except:
                pass

            log_security_event(request, 'member_application_submitted', application.id)

            request.session['application_id'] = application.id

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Your application has been submitted successfully!',
                    'application_id': application.id
                })

            messages.success(request, 'Your application has been submitted successfully!')
            return redirect('application_success')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errors = {}
                for field, error_list in form.errors.items():
                    errors[field] = [str(error) for error in error_list]
                return JsonResponse({
                    'success': False,
                    'errors': errors
                }, status=400)

            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = MemberApplicationForm()

    return render(request, 'public/become_member.html', {'form': form})


def application_success_view(request):
    application_id = request.session.get('application_id')
    if not application_id:
        return redirect('home')

    try:
        application = MemberApplication.objects.get(id=application_id)
        return render(request, 'public/application_success.html', {'application': application})
    except MemberApplication.DoesNotExist:
        return redirect('home')


@login_required
def initial_password_change_view(request):
    if not validate_user_session(request, False):
        return redirect('login')

    if not request.session.get('require_password_change'):
        return redirect('member_dashboard')

    if request.method == 'POST':
        form = InitialPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            with transaction.atomic():
                request.user.set_password(form.cleaned_data['new_password'])
                request.user.password_changed = True
                request.user.save()
                del request.session['require_password_change']
                request.session.modified = True
            log_security_event(request, 'initial_password_set', request.user.id)
            messages.success(request, 'Password set successfully. Please login.')
            return redirect('member_dashboard')
    else:
        form = InitialPasswordChangeForm(user=request.user)

    return render(request, 'accounts/initial_password_change.html', {'form': form})


@login_required
def admin_initial_password_change_view(request):
    if not validate_user_session(request, True):
        return redirect('admin_login')

    if not request.session.get('require_password_change'):
        return redirect('admin_dashboard')

    if request.method == 'POST':
        form = InitialPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            with transaction.atomic():
                request.user.set_password(form.cleaned_data['new_password'])
                request.user.password_changed = True
                request.user.save()
                del request.session['require_password_change']
                request.session.modified = True
            log_security_event(request, 'admin_initial_password_set', request.user.id)
            messages.success(request, 'Password set successfully. Please login.')
            return redirect('admin_dashboard')
    else:
        form = InitialPasswordChangeForm(user=request.user)

    return render(request, 'accounts/admin_initial_password_change.html', {'form': form})


@rate_limit(limit=3, period=3600)
def forgot_password_view(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                code = generate_reset_code()
                expires = timezone.now() + timedelta(minutes=30)

                if not request.session.session_key:
                    request.session.create()

                PasswordResetCode.objects.filter(
                    user=user,
                    used=False
                ).update(used=True)

                reset_code = PasswordResetCode.objects.create(
                    user=user,
                    code=code,
                    expires_at=expires,
                    session_key=request.session.session_key
                )

                try:
                    user.email_user(
                        subject='Elites Pioneer Club - Password Reset Code',
                        message=f'Your password reset code is: {code}\n\nThis code expires in 30 minutes.\n\nIf you did not request this, please ignore and contact support.'
                    )
                except:
                    pass

                request.session['reset_email'] = email
                request.session['reset_session_key'] = request.session.session_key
                log_security_event(request, 'password_reset_requested', user.id)
                messages.success(request, 'Reset code sent to your email.')
                return redirect('verify_reset_code')

            except User.DoesNotExist:
                messages.success(request, 'If an account exists with this email, a reset code has been sent.')
                return redirect('forgot_password')
    else:
        form = ForgotPasswordForm()

    return render(request, 'accounts/forgot_password.html', {'form': form})


@rate_limit(limit=5, period=300)
def verify_reset_code_view(request):
    email = request.session.get('reset_email')
    session_key = request.session.get('reset_session_key')

    if not email or not session_key:
        return redirect('forgot_password')

    if request.method == 'POST':
        form = ResetCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            try:
                reset_code = PasswordResetCode.objects.get(
                    user__email=email,
                    code=code,
                    used=False,
                    expires_at__gt=timezone.now(),
                    session_key=session_key
                )
                request.session['reset_code_id'] = reset_code.id
                log_security_event(request, 'reset_code_verified', reset_code.id)
                return redirect('reset_password')
            except PasswordResetCode.DoesNotExist:
                form.add_error('code', 'Invalid or expired code.')
                log_security_event(request, 'reset_code_invalid', email)
    else:
        form = ResetCodeForm()

    return render(request, 'accounts/verify_code.html', {'form': form})


def reset_password_view(request):
    code_id = request.session.get('reset_code_id')
    session_key = request.session.get('reset_session_key')

    if not code_id or not session_key:
        return redirect('forgot_password')

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            try:
                reset_code = PasswordResetCode.objects.get(
                    id=code_id,
                    used=False,
                    session_key=session_key
                )

                with transaction.atomic():
                    reset_code.user.set_password(form.cleaned_data['new_password'])
                    reset_code.user.password_changed = True
                    reset_code.user.save()
                    reset_code.used = True
                    reset_code.save()

                del request.session['reset_email']
                del request.session['reset_code_id']
                del request.session['reset_session_key']

                log_security_event(request, 'password_reset_success', reset_code.user.id)
                messages.success(request, 'Password reset successful. Please login.')
                return redirect('login')

            except PasswordResetCode.DoesNotExist:
                log_security_event(request, 'password_reset_expired', code_id)
                return redirect('forgot_password')
    else:
        form = ResetPasswordForm()

    return render(request, 'accounts/reset_password.html', {'form': form})


@login_required
def logout_view(request):
    LoginSession.objects.filter(
        user=request.user,
        session_key=request.session.session_key
    ).update(is_active=False)
    log_security_event(request, 'logout', request.user.id)
    logout(request)
    return redirect('home')


@login_required
def profile_view(request):
    if not validate_user_session(request, False):
        return redirect('login')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_phone':
            new_phone = request.POST.get('new_phone', '').strip().replace(' ', '').replace('-', '')
            current_phone = request.user.phone_number

            phone_valid = False
            if re.match(r'^254[17]\d{8}$', new_phone):
                phone_valid = True
            elif re.match(r'^01\d{8}$', new_phone):
                new_phone = '254' + new_phone[1:]
                phone_valid = True
            elif re.match(r'^07\d{8}$', new_phone):
                new_phone = '254' + new_phone[1:]
                phone_valid = True

            if not phone_valid:
                messages.error(request, 'Invalid phone number format.')
                return redirect('profile')

            if new_phone == current_phone:
                messages.error(request, 'New phone number must be different from current number.')
                return redirect('profile')

            if User.objects.filter(phone_number=new_phone).exclude(id=request.user.id).exists():
                messages.error(request, 'Phone number already in use.')
                return redirect('profile')

            request.user.phone_number = new_phone
            request.user.save()

            try:
                from django.core.mail import send_mail
                send_mail(
                    subject='Elites Pioneer Club - Phone Number Updated',
                    message=f'''Dear {request.user.get_full_name()},

Your phone number has been successfully updated to: {new_phone}

If you did not make this change, please contact admin immediately.

Best regards,
Elites Pioneer Club Admin''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[request.user.email],
                    fail_silently=False,
                )
            except:
                pass

            log_security_event(request, 'phone_updated', request.user.id)
            messages.success(request, 'Phone number updated successfully. A confirmation email has been sent.')
            return redirect('profile')

        elif action == 'upload_picture':
            if 'profile_picture' in request.FILES:
                profile_pic = request.FILES['profile_picture']

                allowed_extensions = ['jpg', 'jpeg', 'png', 'gif']
                allowed_mime_types = ['image/jpeg', 'image/png', 'image/gif']

                ext = profile_pic.name.split('.')[-1].lower()
                if ext not in allowed_extensions:
                    messages.error(request, 'Invalid file type. Only JPG, PNG, and GIF are allowed.')
                    return redirect('profile')

                if profile_pic.content_type not in allowed_mime_types:
                    messages.error(request, 'Invalid file type. Only JPG, PNG, and GIF are allowed.')
                    return redirect('profile')

                if profile_pic.size > 10 * 1024 * 1024:
                    messages.error(request, 'Image size must be less than 10MB.')
                    return redirect('profile')

                try:
                    width, height = get_image_dimensions(profile_pic)
                    if width > 4000 or height > 4000:
                        messages.error(request, 'Image dimensions too large. Maximum 4000x4000 pixels.')
                        return redirect('profile')
                except:
                    messages.error(request, 'Invalid image file.')
                    return redirect('profile')

                if request.user.profile_picture:
                    request.user.delete_old_profile_picture()

                request.user.profile_picture = profile_pic
                request.user.save()
                log_security_event(request, 'profile_picture_uploaded', request.user.id)
                messages.success(request, 'Profile picture updated successfully.')

            return redirect('profile')

        elif action == 'remove_picture':
            if request.user.profile_picture:
                request.user.delete_old_profile_picture()
                request.user.profile_picture = None
                request.user.save()
                log_security_event(request, 'profile_picture_removed', request.user.id)
                messages.success(request, 'Profile picture removed successfully.')
            return redirect('profile')

        elif action == 'change_password':
            form = PasswordChangeForm(user=request.user, data=request.POST)
            if form.is_valid():
                current_password = form.cleaned_data['current_password']
                new_password = form.cleaned_data['new_password']

                if not request.user.check_password(current_password):
                    form.add_error('current_password', 'Current password is incorrect.')
                elif current_password == new_password:
                    form.add_error('new_password', 'New password must be different from current password.')
                else:
                    request.user.set_password(new_password)
                    request.user.save()

                    LoginSession.objects.filter(
                        user=request.user,
                        session_key=request.session.session_key
                    ).update(is_active=False)

                    try:
                        from django.core.mail import send_mail
                        send_mail(
                            subject='Elites Pioneer Club - Password Changed',
                            message=f'''Dear {request.user.get_full_name()},

Your password has been successfully changed.

If you did not make this change, please contact admin immediately.

Best regards,
Elites Pioneer Club Admin''',
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[request.user.email],
                            fail_silently=False,
                        )
                    except:
                        pass

                    log_security_event(request, 'password_changed', request.user.id)
                    messages.success(request, 'Password changed successfully. Please login with your new password.')
                    return redirect('logout')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, error)
                return redirect('profile')
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'members/profile.html', {'form': form, 'user': request.user})