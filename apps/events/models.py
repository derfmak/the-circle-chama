from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

class Event(models.Model):
    APRIL = 4
    AUGUST = 8
    DECEMBER = 12
    
    MONTH_CHOICES = [
        (APRIL, 'April'),
        (AUGUST, 'August'),
        (DECEMBER, 'December'),
    ]
    
    name = models.CharField(max_length=200, default='Quarterly Kyathi Bidding/Applications')
    month = models.PositiveIntegerField(choices=MONTH_CHOICES)
    year = models.PositiveIntegerField()
    application_deadline = models.DateTimeField()
    winner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_events')
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'events_event'
        unique_together = ['month', 'year']
        indexes = [
            models.Index(fields=['year', 'month']),
            models.Index(fields=['is_completed']),
        ]
        ordering = ['-year', '-month']
    
    def clean(self):
        current_year = timezone.now().year
        if self.year < current_year:
            raise ValidationError({'year': f'Year cannot be in the past. Must be {current_year} or later.'})
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class EventApplication(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='event_applications')
    applicant_name = models.CharField(max_length=200)
    id_number = models.CharField(max_length=20)
    event_name = models.CharField(max_length=200)
    event_date = models.DateField()
    event_venue = models.CharField(max_length=255)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'events_eventapplication'
        unique_together = ['event', 'applicant']
        indexes = [
            models.Index(fields=['event', 'status']),
            models.Index(fields=['applicant', 'status']),
        ]

class EventWinnerHistory(models.Model):
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='event_wins')
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    won_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'events_eventwinnerhistory'
        indexes = [
            models.Index(fields=['member']),
        ]