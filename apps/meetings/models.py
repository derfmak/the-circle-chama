from django.db import models
from django.conf import settings
from django.utils import timezone

class Meeting(models.Model):
    SCHEDULED = 'scheduled'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (SCHEDULED, 'Scheduled'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
    ]
    
    title = models.CharField(max_length=200)
    date = models.DateTimeField()
    venue = models.CharField(max_length=255)
    purpose = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=SCHEDULED)
    summary = models.TextField(blank=True, null=True)
    facilitation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=500)
    mpesa_number = models.CharField(max_length=15, default='2547XXXXXXXX')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_meetings')
    
    class Meta:
        db_table = 'meetings_meeting'
        indexes = [
            models.Index(fields=['date', 'status']),
            models.Index(fields=['status']),
        ]
        ordering = ['-date']

class MeetingAttendance(models.Model):
    ACCEPTED = 'accepted'
    ABSENT = 'absent'
    ABSENT_WITH_APOLOGY = 'absent_with_apology'
    
    STATUS_CHOICES = [
        (ACCEPTED, 'Accepted'),
        (ABSENT, 'Absent'),
        (ABSENT_WITH_APOLOGY, 'Absent with Apology'),
    ]
    
    PENDING = 'pending'
    PAID = 'paid'
    UNPAID = 'unpaid'
    
    PAYMENT_STATUS = [
        (PENDING, 'Pending'),
        (PAID, 'Paid'),
        (UNPAID, 'Unpaid'),
    ]
    
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='attendances')
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meeting_attendances')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES)
    apology_reason = models.TextField(blank=True, null=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default=PENDING)
    facilitation_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    responded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'meetings_meetingattendance'
        unique_together = ['meeting', 'member']
        indexes = [
            models.Index(fields=['meeting', 'status']),
            models.Index(fields=['member', 'status']),
        ]

class MeetingFacilitationPayment(models.Model):
    MPESA = 'mpesa'
    CASH = 'cash'
    
    MODE_CHOICES = [
        (MPESA, 'M-Pesa'),
        (CASH, 'Cash'),
    ]
    
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
    ]
    
    attendance = models.OneToOneField(MeetingAttendance, on_delete=models.CASCADE, related_name='facilitation_payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=500)
    payment_mode = models.CharField(max_length=10, choices=MODE_CHOICES)
    mpesa_receipt = models.CharField(max_length=50, blank=True, null=True)
    mpesa_phone = models.CharField(max_length=15, blank=True, null=True)
    idempotency_key = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    merchant_request_id = models.CharField(max_length=100, blank=True, null=True)
    checkout_request_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'meetings_meetingfacilitationpayment'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['idempotency_key']),
        ]