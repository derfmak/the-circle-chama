from django.contrib import admin
from .models import Announcement, AnnouncementRead

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_by', 'created_at', 'is_active', 'is_edited']
    list_filter = ['is_active', 'is_edited', 'created_at']
    search_fields = ['title', 'content']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at', 'is_edited']

@admin.register(AnnouncementRead)
class AnnouncementReadAdmin(admin.ModelAdmin):
    list_display = ['announcement', 'user', 'read_at']
    list_filter = ['read_at']
    search_fields = ['user__email', 'announcement__title']
    readonly_fields = ['read_at']