from django.contrib import admin
from .models import Meeting, MeetingAttendance, MeetingFacilitationPayment

@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ['title', 'date', 'venue', 'status', 'facilitation_fee', 'created_at']
    list_filter = ['status', 'date']
    search_fields = ['title', 'venue', 'purpose']
    date_hierarchy = 'date'

@admin.register(MeetingAttendance)
class MeetingAttendanceAdmin(admin.ModelAdmin):
    list_display = ['meeting', 'member', 'status', 'payment_status', 'responded_at']
    list_filter = ['status', 'payment_status']
    search_fields = ['member__email', 'member__first_name', 'meeting__title']

@admin.register(MeetingFacilitationPayment)
class MeetingFacilitationPaymentAdmin(admin.ModelAdmin):
    list_display = ['attendance', 'amount', 'payment_mode', 'status', 'created_at']
    list_filter = ['status', 'payment_mode']
    search_fields = ['attendance__member__email', 'mpesa_receipt']
    readonly_fields = ['idempotency_key']