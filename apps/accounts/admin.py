from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PasswordResetCode, LoginSession

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'is_admin', 'is_active', 'date_joined']
    list_filter = ['is_admin', 'is_active', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name', 'id_number']
    ordering = ['-date_joined']
    
    fieldsets = [
        (None, {'fields': ['email', 'password']}),
        ('Personal info', {'fields': ['first_name', 'last_name', 'phone_number', 'id_number']}),
        ('Permissions', {'fields': ['is_active', 'is_admin', 'is_superuser', 'groups', 'user_permissions']}),
        ('Status', {'fields': ['password_changed', 'password_expires_at']}),
        ('Important dates', {'fields': ['date_joined', 'last_login']}),
    ]
    
    add_fieldsets = [
        (None, {
            'classes': ['wide'],
            'fields': ['email', 'first_name', 'last_name', 'phone_number', 'id_number', 'password1', 'password2'],
        }),
    ]

@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'created_at', 'expires_at', 'used']
    list_filter = ['used', 'created_at']
    search_fields = ['user__email', 'code']

@admin.register(LoginSession)
class LoginSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'created_at', 'last_activity', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__email', 'ip_address']