from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta

class MemberProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)
    registration_fee_paid = models.BooleanField(default=False)
    registration_fee_paid_at = models.DateTimeField(null=True, blank=True)
    is_dropped = models.BooleanField(default=False)
    dropped_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'members_memberprofile'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['is_dropped']),
        ]

class ContributionType(models.Model):
    MONTHLY = 'monthly'
    QUARTERLY = 'quarterly'
    REGISTRATION = 'registration'
    MEETING = 'meeting'
    CUSTOM = 'custom'
    
    TYPE_CHOICES = [
        (MONTHLY, 'Monthly Contribution'),
        (QUARTERLY, 'Quarterly Contribution'),
        (REGISTRATION, 'Registration Fee'),
        (MEETING, 'Meeting Facilitation'),
        (CUSTOM, 'Custom Contribution'),
    ]
    
    name = models.CharField(max_length=100)
    contribution_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    deadline_day = models.PositiveIntegerField(null=True, blank=True, help_text="Day of month for deadline")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'members_contributiontype'
        indexes = [
            models.Index(fields=['contribution_type', 'is_active']),
        ]

class Contribution(models.Model):
    PENDING = 'pending'
    PAID = 'paid'
    PAID_LATE = 'paid_late'
    PARTIAL = 'partial'
    WAITING_APPROVAL = 'waiting_approval'
    WAITING_REAPPROVAL = 'waiting_reapproval'
    REJECTED = 'rejected'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PAID, 'Paid'),
        (PAID_LATE, 'Paid with Late'),
        (PARTIAL, 'Partial'),
        (WAITING_APPROVAL, 'Waiting Approval'),
        (WAITING_REAPPROVAL, 'Waiting Reapproval'),
        (REJECTED, 'Rejected'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    contribution_type = models.ForeignKey(ContributionType, on_delete=models.CASCADE)
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField(null=True, blank=True)
    quarter = models.PositiveIntegerField(null=True, blank=True)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)
    is_late = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'members_contribution'
        unique_together = ['user', 'contribution_type', 'year', 'month', 'quarter']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'year', 'month']),
            models.Index(fields=['contribution_type', 'status']),
        ]

class CashPaymentRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cash_requests')
    contribution = models.ForeignKey(Contribution, on_delete=models.CASCADE, related_name='cash_requests')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_cash_requests')
    
    class Meta:
        db_table = 'members_cashpaymentrequest'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def approve(self, admin_user):
        self.status = 'approved'
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.save()
        
        contribution = self.contribution
        contribution.amount_paid += self.amount
        if contribution.amount_paid >= contribution.amount_due + contribution.fine_amount:
            if contribution.is_late:
                contribution.status = 'paid_late'
            else:
                contribution.status = 'paid'
            contribution.paid_at = timezone.now()
        else:
            contribution.status = 'partial'
        contribution.save()
    
    def decline(self, admin_user, notes):
        self.status = 'declined'
        self.admin_notes = notes
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.save()
        
        contribution = self.contribution
        contribution.status = 'rejected'
        contribution.save()

class PaymentTransaction(models.Model):
    MPESA = 'mpesa'
    CASH = 'cash'
    
    MODE_CHOICES = [
        (MPESA, 'M-Pesa'),
        (CASH, 'Cash'),
    ]
    
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
        (CANCELLED, 'Cancelled'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    contribution = models.ForeignKey(Contribution, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_mode = models.CharField(max_length=10, choices=MODE_CHOICES)
    mpesa_receipt = models.CharField(max_length=50, null=True, blank=True)
    mpesa_phone = models.CharField(max_length=15, null=True, blank=True)
    idempotency_key = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    merchant_request_id = models.CharField(max_length=100, null=True, blank=True)
    checkout_request_id = models.CharField(max_length=100, null=True, blank=True)
    result_code = models.CharField(max_length=10, null=True, blank=True)
    result_desc = models.TextField(null=True, blank=True)
    callback_received = models.BooleanField(default=False)
    callback_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_payments')
    approved_at = models.DateTimeField(null=True, blank=True)
    is_late_payment = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'members_paymenttransaction'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['idempotency_key']),
            models.Index(fields=['merchant_request_id']),
            models.Index(fields=['checkout_request_id']),
        ]

class Debt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    contribution = models.ForeignKey(Contribution, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_cleared = models.BooleanField(default=False)
    cleared_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'members_debt'
        indexes = [
            models.Index(fields=['user', 'is_cleared']),
        ]