from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
from django.core.mail import send_mail
from django.core.validators import FileExtensionValidator, validate_image_file_extension
from django.conf import settings
import os


def profile_pic_path(instance, filename):
    ext = filename.split('.')[-1].lower()
    filename = f"profile_{instance.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
    return os.path.join('profile_pics', filename)


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')

        return self.create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        return self.get(email=email)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=15)
    id_number = models.CharField(max_length=20, unique=True)
    date_joined = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    password_changed = models.BooleanField(default=False)
    password_expires_at = models.DateTimeField(null=True, blank=True)
    profile_picture = models.ImageField(
        upload_to=profile_pic_path,
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif']),
            validate_image_file_extension,
        ],
        max_length=255
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone_number', 'id_number']

    class Meta:
        db_table = 'accounts_user'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['id_number']),
        ]

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_short_name(self):
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        send_mail(subject, message, from_email or settings.DEFAULT_FROM_EMAIL, [self.email], **kwargs)

    def delete_old_profile_picture(self):
        if self.profile_picture:
            if os.path.isfile(self.profile_picture.path):
                os.remove(self.profile_picture.path)


class MemberApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('on_hold', 'On Hold'),
    ]

    full_name = models.CharField(max_length=100)
    id_number = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField()
    agreed_to_terms = models.BooleanField(default=False)
    agreed_to_privacy = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_applications')
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_memberapplication'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'status']),
            models.Index(fields=['id_number', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.full_name} - {self.id_number} ({self.status})"


class PasswordResetCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_codes')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    session_key = models.CharField(max_length=100)

    class Meta:
        db_table = 'accounts_passwordresetcode'
        indexes = [
            models.Index(fields=['user', 'code']),
            models.Index(fields=['session_key']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.code}"

    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at


class LoginSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_sessions')
    session_key = models.CharField(max_length=100, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'accounts_loginsession'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_key']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.ip_address}"


class SecurityLog(models.Model):
    EVENT_TYPES = [
        ('login_success', 'Login Success'),
        ('login_failed', 'Login Failed'),
        ('admin_login_success', 'Admin Login Success'),
        ('admin_login_failed', 'Admin Login Failed'),
        ('admin_logout', 'Admin Logout'),
        ('logout', 'Logout'),
        ('password_reset_requested', 'Password Reset Requested'),
        ('password_reset_success', 'Password Reset Success'),
        ('reset_code_verified', 'Reset Code Verified'),
        ('reset_code_invalid', 'Reset Code Invalid'),
        ('password_reset_expired', 'Password Reset Expired'),
        ('password_changed', 'Password Changed'),
        ('initial_password_set', 'Initial Password Set'),
        ('admin_initial_password_set', 'Admin Initial Password Set'),
        ('admin_password_reset_requested', 'Admin Password Reset Requested'),
        ('admin_reset_code_verified', 'Admin Reset Code Verified'),
        ('admin_reset_code_invalid', 'Admin Reset Code Invalid'),
        ('admin_password_reset_success', 'Admin Password Reset Success'),
        ('admin_password_reset_expired', 'Admin Password Reset Expired'),
        ('member_application_submitted', 'Member Application Submitted'),
        ('member_application_approved', 'Member Application Approved'),
        ('member_application_rejected', 'Member Application Rejected'),
        ('member_application_on_hold', 'Member Application On Hold'),
        ('phone_updated', 'Phone Updated'),
        ('profile_picture_uploaded', 'Profile Picture Uploaded'),
        ('profile_picture_removed', 'Profile Picture Removed'),
        ('member_created_by_admin', 'Member Created By Admin'),
        ('member_updated_by_admin', 'Member Updated By Admin'),
        ('member_deactivated_by_admin', 'Member Deactivated By Admin'),
        ('session_expired', 'Session Expired'),
        ('rate_limit_exceeded', 'Rate Limit Exceeded'),
    ]

    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    user_identifier = models.CharField(max_length=200, null=True, blank=True)
    path = models.CharField(max_length=500, blank=True)
    method = models.CharField(max_length=10, blank=True)
    details = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'accounts_securitylog'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['user_identifier']),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.ip_address} - {self.created_at}"