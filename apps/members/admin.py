from django.contrib import admin
from .models import MemberProfile, ContributionType, Contribution, PaymentTransaction, Debt

@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'registration_fee_paid', 'is_dropped', 'registration_fee_paid_at']
    list_filter = ['registration_fee_paid', 'is_dropped']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']

@admin.register(ContributionType)
class ContributionTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'contribution_type', 'amount', 'deadline_day', 'is_active']
    list_filter = ['contribution_type', 'is_active']
    search_fields = ['name']

@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = ['user', 'contribution_type', 'year', 'month', 'quarter', 'amount_due', 'amount_paid', 'status', 'is_late']
    list_filter = ['status', 'is_late', 'year', 'contribution_type']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    date_hierarchy = 'created_at'

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'payment_mode', 'status', 'created_at', 'approved_by']
    list_filter = ['status', 'payment_mode', 'is_late_payment']
    search_fields = ['user__email', 'mpesa_receipt', 'idempotency_key']
    readonly_fields = ['idempotency_key', 'callback_data']

@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'description', 'is_cleared', 'created_at']
    list_filter = ['is_cleared']
    search_fields = ['user__email', 'description']