from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Event, EventApplication, EventWinnerHistory
from .forms import EventForm

admin_required = lambda view: login_required(user_passes_test(lambda u: u.is_admin)(view))

@admin_required
def admin_events_view(request):
    events_list = Event.objects.all().order_by('-year', '-month')
    
    paginator = Paginator(events_list, 10)
    page_number = request.GET.get('page')
    events = paginator.get_page(page_number)
    
    context = {
        'events': events,
        'page_obj': events,
    }
    return render(request, 'admin/events.html', context)

@admin_required
def admin_create_event_view(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event created successfully.')
            return redirect('admin_events')
    else:
        form = EventForm()
    
    context = {
        'form': form,
    }
    return render(request, 'admin/create_event.html', context)

@admin_required
def admin_event_applications_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    applications = event.applications.all().select_related('applicant')
    
    winner_exists = event.winner is not None
    
    if request.method == 'POST' and not winner_exists:
        application_id = request.POST.get('application_id')
        
        with transaction.atomic():
            winner_application = get_object_or_404(EventApplication, id=application_id, event=event)
            
            event.winner = winner_application.applicant
            event.is_completed = True
            event.save()
            
            winner_application.status = 'approved'
            winner_application.save()
            
            EventWinnerHistory.objects.create(
                member=winner_application.applicant,
                event=event
            )
            
            EventApplication.objects.filter(
                event=event
            ).exclude(id=application_id).update(status='rejected')
            
            messages.success(request, f'Winner selected: {winner_application.applicant.get_full_name()}')
            return redirect('admin_event_applications', event_id=event.id)
    
    context = {
        'event': event,
        'applications': applications,
        'winner_exists': winner_exists,
        'winner_history': EventWinnerHistory.objects.filter(event=event).first(),
    }
    return render(request, 'admin/event_applications.html', context)

@admin_required
def admin_event_winners_view(request):
    winners = EventWinnerHistory.objects.all().select_related('member', 'event').order_by('-won_at')
    
    context = {
        'winners': winners,
    }
    return render(request, 'admin/event_winners.html', context)