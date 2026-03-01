from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from .models import Announcement
from .forms import AnnouncementForm

admin_required = lambda view: login_required(user_passes_test(lambda u: u.is_admin)(view))

@admin_required
def admin_announcements_view(request):
    announcements_list = Announcement.objects.all().order_by('-created_at')
    
    paginator = Paginator(announcements_list, 15)
    page_number = request.GET.get('page')
    announcements = paginator.get_page(page_number)
    
    context = {
        'announcements': announcements,
        'page_obj': announcements,
    }
    return render(request, 'admin/announcements.html', context)

@admin_required
def admin_create_announcement_view(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = request.user
            announcement.is_active = True
            announcement.save()
            messages.success(request, 'Announcement created successfully.')
            return redirect('admin_announcements')
    else:
        form = AnnouncementForm()
    
    context = {
        'form': form,
    }
    return render(request, 'admin/create_announcement.html', context)

@admin_required
def admin_edit_announcement_view(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)
    
    if not announcement.is_active:
        messages.error(request, 'Cannot edit a deleted announcement.')
        return redirect('admin_announcements')
    
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.is_edited = True
            announcement.save()
            messages.success(request, 'Announcement updated successfully.')
            return redirect('admin_announcements')
    else:
        form = AnnouncementForm(instance=announcement)
    
    context = {
        'form': form,
        'announcement': announcement,
    }
    return render(request, 'admin/edit_announcement.html', context)

@admin_required
def admin_delete_announcement_view(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)
    
    if not announcement.is_active:
        messages.error(request, 'Announcement is already deleted.')
        return redirect('admin_announcements')
    
    if request.method == 'POST':
        announcement.is_active = False
        announcement.save()
        messages.success(request, 'Announcement deactivated successfully.')
        return redirect('admin_announcements')
    
    context = {
        'announcement': announcement,
    }
    return render(request, 'admin/delete_announcement.html', context)