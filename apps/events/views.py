from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from django.utils import timezone
from datetime import date
from .models import Event, EventApplication, EventWinnerHistory
from .forms import EventApplicationForm, EventForm

MONTH_NAMES = {
    4: 'April',
    8: 'August',
    12: 'December'
}

@login_required
def events_list_view(request):
    if request.user.is_admin:
        return redirect('admin_events')
    
    current_year = date.today().year
    
    events = Event.objects.filter(year__gte=current_year-1).order_by('-year', '-month')
    
    user_applications = EventApplication.objects.filter(
        applicant=request.user,
        event__in=events
    )
    
    applications_map = {a.event_id: a for a in user_applications}
    
    winner_history = EventWinnerHistory.objects.filter(
        member=request.user
    ).select_related('event')
    
    won_event_ids = [w.event_id for w in winner_history]
    
    events_with_status = []
    for event in events:
        application = applications_map.get(event.id)
        has_won_before = event.id in won_event_ids
        
        events_with_status.append({
            'event': event,
            'application': application,
            'can_apply': not application and not has_won_before and not event.is_completed,
            'has_won_before': has_won_before,
            'month_name': MONTH_NAMES.get(event.month, 'Unknown')
        })
    
    context = {
        'events': events_with_status,
        'winner_history': winner_history,
    }
    return render(request, 'events/list.html', context)

@login_required
def apply_event_view(request, event_id):
    if request.user.is_admin:
        return redirect('admin_events')
    
    event = get_object_or_404(Event, id=event_id)
    
    if event.is_completed:
        messages.error(request, 'Applications are closed for this event.')
        return redirect('events_list')
    
    existing_win = EventWinnerHistory.objects.filter(member=request.user).first()
    if existing_win:
        messages.error(request, 'You have already won an event. You must wait for all members to win before applying again.')
        return redirect('events_list')
    
    existing_application = EventApplication.objects.filter(
        event=event,
        applicant=request.user
    ).first()
    
    if existing_application:
        messages.error(request, 'You have already applied for this event.')
        return redirect('events_list')
    
    if request.method == 'POST':
        form = EventApplicationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                application = EventApplication.objects.create(
                    event=event,
                    applicant=request.user,
                    applicant_name=form.cleaned_data['applicant_name'],
                    id_number=form.cleaned_data['id_number'],
                    event_name=form.cleaned_data['event_name'],
                    event_date=form.cleaned_data['event_date'],
                    event_venue=form.cleaned_data['event_venue'],
                    reason=form.cleaned_data['reason']
                )
            
            messages.success(request, 'Your application has been submitted successfully.')
            return redirect('events_list')
    else:
        form = EventApplicationForm()
    
    context = {
        'form': form,
        'event': event,
        'month_name': MONTH_NAMES.get(event.month, 'Unknown'),
    }
    return render(request, 'events/apply.html', context)

@login_required
def application_status_view(request, application_id):
    if request.user.is_admin:
        return redirect('admin_events')
    
    application = get_object_or_404(EventApplication, id=application_id, applicant=request.user)
    
    context = {
        'application': application,
        'event': application.event,
    }
    return render(request, 'events/status.html', context)