from django.contrib import admin
from .models import MpesaCredential, StkPushLog, IdempotencyKey

@admin.register(MpesaCredential)
class MpesaCredentialAdmin(admin.ModelAdmin):
    list_display = ['environment', 'shortcode', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(StkPushLog)
class StkPushLogAdmin(admin.ModelAdmin):
    list_display = ['merchant_request_id', 'checkout_request_id', 'phone_number', 'amount', 'response_code', 'callback_received', 'created_at']
    list_filter = ['callback_received', 'response_code', 'created_at']
    search_fields = ['merchant_request_id', 'checkout_request_id', 'mpesa_receipt_number', 'phone_number']
    readonly_fields = ['merchant_request_id', 'checkout_request_id', 'raw_callback', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ['key', 'used', 'transaction_type', 'amount', 'created_at', 'used_at']
    list_filter = ['used', 'transaction_type']
    search_fields = ['key']
    readonly_fields = ['created_at']