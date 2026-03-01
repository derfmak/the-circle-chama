from django.db import models
from django.conf import settings
import uuid

class MpesaCredential(models.Model):
    environment = models.CharField(max_length=20, choices=[('sandbox', 'Sandbox'), ('production', 'Production')], unique=True)
    consumer_key = models.CharField(max_length=255)
    consumer_secret = models.CharField(max_length=255)
    passkey = models.CharField(max_length=255)
    shortcode = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments_mpesacredential'

class StkPushLog(models.Model):
    merchant_request_id = models.CharField(max_length=100, unique=True, db_index=True)
    checkout_request_id = models.CharField(max_length=100, unique=True, db_index=True)
    phone_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    account_reference = models.CharField(max_length=50)
    transaction_desc = models.CharField(max_length=255)
    response_code = models.CharField(max_length=10, null=True, blank=True)
    response_description = models.TextField(null=True, blank=True)
    customer_message = models.TextField(null=True, blank=True)
    callback_received = models.BooleanField(default=False)
    callback_result_code = models.CharField(max_length=10, null=True, blank=True)
    callback_result_desc = models.TextField(null=True, blank=True)
    mpesa_receipt_number = models.CharField(max_length=50, null=True, blank=True)
    transaction_date = models.DateTimeField(null=True, blank=True)
    raw_callback = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments_stkpushlog'
        indexes = [
            models.Index(fields=['merchant_request_id']),
            models.Index(fields=['checkout_request_id']),
            models.Index(fields=['mpesa_receipt_number']),
            models.Index(fields=['callback_received']),
        ]

class IdempotencyKey(models.Model):
    key = models.CharField(max_length=100, unique=True, db_index=True)
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    transaction_type = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'payments_idempotencykey'
        indexes = [
            models.Index(fields=['key', 'used']),
        ]