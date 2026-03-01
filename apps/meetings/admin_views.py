from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.contrib import messages
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.utils import timezone
from .models import Meeting, MeetingAttendance, MeetingFacilitationPayment
from .forms import MeetingForm, MeetingSummaryForm

admin_required = lambda view: login_required(user_passes_test(lambda u: u.is_admin)(view))

@admin_required
def admin_meetings_view(request):
    meetings_list = Meeting.objects.all().order_by('-date')
    
    paginator = Paginator(meetings_list, 15)
    page_number = request.GET.get('page')
    meetings = paginator.get_page(page_number)
    
    context = {
        'meetings': meetings,
        'page_obj': meetings,
    }
    return render(request, 'admin/meetings.html', context)

@admin_required
def admin_create_meeting_view(request):
    if request.method == 'POST':
        form = MeetingForm(request.POST)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.created_by = request.user
            meeting.save()
            messages.success(request, 'Meeting created successfully.')
            return redirect('admin_meetings')
    else:
        form = MeetingForm()
    
    context = {
        'form': form,
    }
    return render(request, 'admin/create_meeting.html', context)

@admin_required
def admin_meeting_detail_view(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id)
    attendances = meeting.attendances.all().select_related('member')
    
    accepted_count = attendances.filter(status='accepted').count()
    absent_count = attendances.filter(status='absent').count()
    apology_count = attendances.filter(status='absent_with_apology').count()
    pending_count = attendances.filter(status='pending').count()
    
    context = {
        'meeting': meeting,
        'attendances': attendances,
        'accepted_count': accepted_count,
        'absent_count': absent_count,
        'apology_count': apology_count,
        'pending_count': pending_count,
    }
    return render(request, 'admin/meeting_detail.html', context)

@admin_required
def admin_edit_meeting_view(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id)
    
    if request.method == 'POST':
        form = MeetingForm(request.POST, instance=meeting)
        if form.is_valid():
            form.save()
            messages.success(request, 'Meeting updated successfully.')
            return redirect('admin_meetings')
    else:
        form = MeetingForm(instance=meeting)
    
    context = {
        'form': form,
        'meeting': meeting,
    }
    return render(request, 'admin/edit_meeting.html', context)

@admin_required
def admin_add_summary_view(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id)
    
    if request.method == 'POST':
        form = MeetingSummaryForm(request.POST, instance=meeting)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.status = 'completed'
            meeting.save()
            messages.success(request, 'Meeting summary added successfully.')
            return redirect('admin_meeting_detail', meeting_id=meeting.id)
    else:
        form = MeetingSummaryForm(instance=meeting)
    
    context = {
        'form': form,
        'meeting': meeting,
    }
    return render(request, 'admin/add_summary.html', context)

@admin_required
def admin_attendance_report_view(request):
    meetings = Meeting.objects.filter(status='completed').order_by('-date')
    
    attendance_stats = []
    for meeting in meetings:
        stats = {
            'meeting': meeting,
            'total': meeting.attendances.count(),
            'accepted': meeting.attendances.filter(status='accepted').count(),
            'absent': meeting.attendances.filter(status='absent').count(),
            'apology': meeting.attendances.filter(status='absent_with_apology').count(),
            'paid': meeting.attendances.filter(payment_status='paid').count(),
            'unpaid': meeting.attendances.filter(payment_status='unpaid').count(),
        }
        attendance_stats.append(stats)
    
    context = {
        'attendance_stats': attendance_stats,
    }
    return render(request, 'admin/attendance_report.html', context)

@admin_required
def admin_member_attendance_view(request, member_id):
    from apps.accounts.models import User
    member = get_object_or_404(User, id=member_id, is_admin=False)
    
    attendances = MeetingAttendance.objects.filter(
        member=member
    ).select_related('meeting').order_by('-meeting__date')
    
    total_meetings = attendances.count()
    attended = attendances.filter(status='accepted').count()
    absent = attendances.filter(status='absent').count()
    apology = attendances.filter(status='absent_with_apology').count()
    
    attendance_rate = (attended / total_meetings * 100) if total_meetings > 0 else 0
    
    context = {
        'member': member,
        'attendances': attendances,
        'total_meetings': total_meetings,
        'attended': attended,
        'absent': absent,
        'apology': apology,
        'attendance_rate': round(attendance_rate, 2),
    }
    return render(request, 'admin/member_attendance.html', context)