from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone
from .models import Announcement, AnnouncementRead
from .forms import AnnouncementForm

@login_required
def announcements_list_view(request):
    if request.user.is_admin:
        return redirect('admin_announcements')
    
    announcements_list = Announcement.objects.filter(is_active=True).order_by('-created_at')
    
    paginator = Paginator(announcements_list, 10)
    page_number = request.GET.get('page')
    announcements = paginator.get_page(page_number)
    
    read_announcements = set(AnnouncementRead.objects.filter(
        user=request.user,
        announcement__in=announcements
    ).values_list('announcement_id', flat=True))
    
    announcements_with_status = []
    for announcement in announcements:
        announcements_with_status.append({
            'announcement': announcement,
            'is_read': announcement.id in read_announcements
        })
    
    context = {
        'announcements': announcements_with_status,
        'page_obj': announcements,
        'unread_count': announcements_list.exclude(reads__user=request.user).count()
    }
    return render(request, 'announcements/list.html', context)

@login_required
def announcement_detail_view(request, announcement_id):
    if request.user.is_admin:
        return redirect('admin_announcement_detail', announcement_id=announcement_id)
    
    announcement = get_object_or_404(Announcement, id=announcement_id, is_active=True)
    
    AnnouncementRead.objects.get_or_create(
        announcement=announcement,
        user=request.user
    )
    
    context = {
        'announcement': announcement,
    }
    return render(request, 'announcements/detail.html', context)