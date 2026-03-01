from django.contrib import admin
from .models import Event, EventApplication, EventWinnerHistory

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['name', 'month', 'year', 'application_deadline', 'winner_name', 'is_completed']
    list_filter = ['is_completed', 'year', 'month']
    search_fields = ['name', 'winner__email', 'winner__first_name', 'winner__last_name']
    readonly_fields = ['created_at']
    
    def winner_name(self, obj):
        if obj.winner:
            return f"{obj.winner.get_full_name() or obj.winner.email}"
        return "-"
    winner_name.short_description = 'Winner'

@admin.register(EventApplication)
class EventApplicationAdmin(admin.ModelAdmin):
    list_display = ['applicant_name', 'event_name', 'event_date', 'event_venue', 'event', 'status', 'applied_at']
    list_filter = ['status', 'event__year', 'event__month']
    search_fields = ['applicant__email', 'applicant_name', 'event_name', 'id_number']
    readonly_fields = ['applied_at', 'updated_at']
    fieldsets = (
        ('Applicant Information', {
            'fields': ('applicant', 'applicant_name', 'id_number')
        }),
        ('Event Details', {
            'fields': ('event', 'event_name', 'event_date', 'event_venue', 'reason')
        }),
        ('Status', {
            'fields': ('status', 'applied_at', 'updated_at')
        }),
    )

@admin.register(EventWinnerHistory)
class EventWinnerHistoryAdmin(admin.ModelAdmin):
    list_display = ['member_name', 'event_name', 'won_at']
    list_filter = ['event__year']
    search_fields = ['member__email', 'member__first_name', 'member__last_name', 'event__name']
    readonly_fields = ['won_at']
    
    def member_name(self, obj):
        return f"{obj.member.get_full_name() or obj.member.email}"
    member_name.short_description = 'Member'
    
    def event_name(self, obj):
        return obj.event.name
    event_name.short_description = 'Event'