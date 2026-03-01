from django import forms
from django.utils import timezone
from .models import Meeting, MeetingAttendance
import re

class MeetingForm(forms.ModelForm):
    class Meta:
        model = Meeting
        fields = ['title', 'date', 'venue', 'purpose', 'facilitation_fee', 'mpesa_number']
        widgets = {
            'date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'min': timezone.now().strftime('%Y-%m-%dT%H:%M')
            }),
            'purpose': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Purpose of the meeting...'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Monthly General Meeting'
            }),
            'venue': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Conference Room A / Zoom Link'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['facilitation_fee'].widget.attrs.update({
            'class': 'form-control',
            'min': '500',
            'step': '50',
            'value': '500'
        })
        self.fields['mpesa_number'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '254712345678'
        })
    
    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date and date < timezone.now():
            raise forms.ValidationError('Meeting date cannot be in the past.')
        return date
    
    def clean_facilitation_fee(self):
        fee = self.cleaned_data.get('facilitation_fee')
        if fee:
            if fee < 500:
                raise forms.ValidationError('Facilitation fee cannot be less than KES 500.')
            if fee % 50 != 0:
                raise forms.ValidationError('Facilitation fee must be in increments of KES 50.')
        return fee
    
    def clean_mpesa_number(self):
        number = self.cleaned_data.get('mpesa_number')
        if number:
            number = number.strip().replace(' ', '')
            if not re.match(r'^254[17]\d{8}$', number):
                raise forms.ValidationError('M-Pesa number must start with 2541 or 2547 and have 12 digits total.')
        return number

class MeetingResponseForm(forms.Form):
    ACCEPTED = 'accepted'
    ABSENT = 'absent'
    ABSENT_WITH_APOLOGY = 'absent_with_apology'
    
    RESPONSE_CHOICES = [
        (ACCEPTED, 'Accept'),
        (ABSENT, 'Absent'),
        (ABSENT_WITH_APOLOGY, 'Absent with Apology'),
    ]
    
    response = forms.ChoiceField(
        choices=RESPONSE_CHOICES, 
        widget=forms.RadioSelect(attrs={'class': 'form-radio'})
    )
    apology_reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Please provide reason for absence...'
        }),
        required=False
    )
    
    def clean(self):
        cleaned_data = super().clean()
        response = cleaned_data.get('response')
        apology_reason = cleaned_data.get('apology_reason')
        
        if response == self.ABSENT_WITH_APOLOGY and not apology_reason:
            raise forms.ValidationError('Please provide a reason for your apology.')

class FacilitationPaymentForm(forms.Form):
    MPESA = 'mpesa'
    CASH = 'cash'
    
    MODE_CHOICES = [
        (MPESA, 'M-Pesa'),
        (CASH, 'Cash'),
    ]
    
    payment_mode = forms.ChoiceField(
        choices=MODE_CHOICES, 
        widget=forms.RadioSelect(attrs={'class': 'form-radio'})
    )
    mpesa_phone = forms.CharField(
        max_length=12, 
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '254712345678'
        })
    )
    
    def clean_mpesa_phone(self):
        phone = self.cleaned_data.get('mpesa_phone')
        payment_mode = self.cleaned_data.get('payment_mode')
        
        if payment_mode == self.MPESA:
            if not phone:
                raise forms.ValidationError('Phone number is required for M-Pesa payment.')
            phone = phone.strip().replace(' ', '')
            if not re.match(r'^254[17]\d{8}$', phone):
                raise forms.ValidationError('M-Pesa number must start with 2541 or 2547 and have 12 digits total.')
        return phone

class MeetingSummaryForm(forms.ModelForm):
    class Meta:
        model = Meeting
        fields = ['summary']
        widgets = {
            'summary': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Brief summary of meeting discussions and outcomes...'
            })
        }