from django import forms
from django.utils import timezone
from .models import Event, EventApplication
from datetime import datetime, time

class EventForm(forms.ModelForm):
    application_deadline = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    class Meta:
        model = Event
        fields = ['name', 'month', 'year', 'application_deadline']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_year = timezone.now().year
        year_choices = [(y, str(y)) for y in range(current_year, current_year + 5)]
        
        self.fields['name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Quarterly Kyathi Bidding/Applications'
        })
        self.fields['name'].initial = 'Quarterly Kyathi Bidding/Applications'
        
        self.fields['month'].widget.attrs.update({
            'class': 'form-control'
        })
        
        self.fields['year'] = forms.ChoiceField(
            choices=year_choices,
            widget=forms.Select(attrs={'class': 'form-control'})
        )
    
    def clean_year(self):
        year = int(self.cleaned_data.get('year'))
        current_year = timezone.now().year
        if year < current_year:
            raise forms.ValidationError(f'Year must be {current_year} or later.')
        return year
    
    def clean_application_deadline(self):
        deadline_date = self.cleaned_data.get('application_deadline')
        if deadline_date:
            midnight_deadline = datetime.combine(deadline_date, time(23, 59, 59))
            midnight_deadline = timezone.make_aware(midnight_deadline) if timezone.is_naive(midnight_deadline) else midnight_deadline
            
            if midnight_deadline < timezone.now():
                raise forms.ValidationError('Application deadline cannot be in the past.')
            return midnight_deadline
        return deadline_date

class EventApplicationForm(forms.Form):
    applicant_name = forms.CharField(max_length=200, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Your Full Name'
    }))
    id_number = forms.CharField(max_length=20, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'ID Number'
    }))
    event_name = forms.CharField(max_length=200, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Name of Your Event'
    }))
    event_date = forms.DateField(widget=forms.DateInput(attrs={
        'class': 'form-control',
        'type': 'date',
        'min': timezone.now().strftime('%Y-%m-%d')
    }))
    event_venue = forms.CharField(max_length=255, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Event Venue'
    }))
    reason = forms.CharField(widget=forms.Textarea(attrs={
        'class': 'form-control',
        'rows': 4,
        'placeholder': 'Why should this event be awarded to you?'
    }))
    
    def clean_id_number(self):
        id_number = self.cleaned_data.get('id_number')
        if not id_number.isalnum():
            raise forms.ValidationError('ID number must be alphanumeric.')
        return id_number
    
    def clean_event_date(self):
        event_date = self.cleaned_data.get('event_date')
        if event_date and event_date < timezone.now().date():
            raise forms.ValidationError('Event date cannot be in the past.')
        return event_date