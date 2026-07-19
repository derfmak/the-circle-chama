from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, MemberApplication, PasswordResetCode, LoginSession, SecurityLog
from django.utils import timezone

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'is_admin', 'is_active', 'date_joined']
    list_filter = ['is_admin', 'is_active', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name', 'id_number', 'phone_number']
    ordering = ['-date_joined']
    readonly_fields = ['date_joined', 'last_login']

    fieldsets = [
        (None, {'fields': ['email', 'password']}),
        ('Personal Information', {'fields': ['first_name', 'last_name', 'phone_number', 'id_number', 'profile_picture']}),
        ('Permissions', {'fields': ['is_active', 'is_admin', 'is_superuser', 'is_staff', 'groups', 'user_permissions']}),
        ('Security', {'fields': ['password_changed', 'password_expires_at']}),
        ('Important Dates', {'fields': ['date_joined', 'last_login']}),
    ]

    add_fieldsets = [
        (None, {
            'classes': ['wide'],
            'fields': ['email', 'first_name', 'last_name', 'phone_number', 'id_number', 'password1', 'password2'],
        }),
    ]


@admin.register(MemberApplication)
class MemberApplicationAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'phone_number', 'id_number', 'status', 'created_at']
    list_filter = ['status', 'created_at', 'updated_at']
    search_fields = ['full_name', 'email', 'id_number', 'phone_number']
    readonly_fields = ['created_at', 'updated_at', 'ip_address', 'user_agent']
    ordering = ['-created_at']

    fieldsets = [
        ('Applicant Information', {'fields': ['full_name', 'email', 'phone_number', 'id_number']}),
        ('Agreements', {'fields': ['agreed_to_terms', 'agreed_to_privacy']}),
        ('Status', {'fields': ['status', 'reviewed_by', 'reviewed_at', 'review_notes']}),
        ('Metadata', {'fields': ['ip_address', 'user_agent', 'created_at', 'updated_at']}),
    ]

    actions = ['approve_applications', 'reject_applications', 'hold_applications']

    def approve_applications(self, request, queryset):
        updated = queryset.update(status='approved', reviewed_at=timezone.now(), reviewed_by=request.user)
        self.message_user(request, f'{updated} applications approved.')
    approve_applications.short_description = 'Approve selected applications'

    def reject_applications(self, request, queryset):
        updated = queryset.update(status='rejected', reviewed_at=timezone.now(), reviewed_by=request.user)
        self.message_user(request, f'{updated} applications rejected.')
    reject_applications.short_description = 'Reject selected applications'

    def hold_applications(self, request, queryset):
        updated = queryset.update(status='on_hold', reviewed_at=timezone.now(), reviewed_by=request.user)
        self.message_user(request, f'{updated} applications placed on hold.')
    hold_applications.short_description = 'Hold selected applications'


@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'created_at', 'expires_at', 'used', 'is_valid']
    list_filter = ['used', 'created_at']
    search_fields = ['user__email', 'code']
    readonly_fields = ['created_at']

    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.boolean = True
    is_valid.short_description = 'Valid'


@admin.register(LoginSession)
class LoginSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'created_at', 'last_activity', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__email', 'ip_address', 'session_key']
    readonly_fields = ['created_at', 'last_activity']

    actions = ['terminate_sessions']

    def terminate_sessions(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} sessions terminated.')
    terminate_sessions.short_description = 'Terminate selected sessions'


@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'ip_address', 'user_identifier', 'path', 'created_at']
    list_filter = ['event_type', 'created_at']
    search_fields = ['ip_address', 'user_identifier', 'path']
    readonly_fields = ['event_type', 'ip_address', 'user_agent', 'user_identifier', 'path', 'method', 'details', 'created_at']
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False