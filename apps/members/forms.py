from django import forms
from django.utils import timezone
from .models import ContributionType, Contribution, PaymentTransaction
import re

class ContributionTypeForm(forms.ModelForm):
    class Meta:
        model = ContributionType
        fields = ['name', 'contribution_type', 'amount', 'description', 'deadline_day']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'deadline_day': forms.NumberInput(attrs={'min': 1, 'max': 31}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['contribution_type'].widget.attrs.update({'class': 'form-control'})
        self.fields['amount'].widget.attrs.update({'class': 'form-control', 'step': '0.01', 'min': '0'})
        self.fields['description'].widget.attrs.update({'class': 'form-control'})
        self.fields['deadline_day'].widget.attrs.update({'class': 'form-control'})
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise forms.ValidationError('Amount must be greater than zero.')
        return amount

class PaymentForm(forms.Form):
    payment_mode = forms.ChoiceField(
        choices=PaymentTransaction.MODE_CHOICES,
        widget=forms.RadioSelect
    )
    mpesa_phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '254712345678'
        })
    )
    
    def clean_mpesa_phone(self):
        phone = self.cleaned_data.get('mpesa_phone')
        payment_mode = self.cleaned_data.get('payment_mode')
        
        if payment_mode == 'mpesa':
            if not phone:
                raise forms.ValidationError('Phone number is required for M-Pesa payment.')
            phone = phone.strip().replace(' ', '').replace('-', '')
            if not re.match(r'^254[17]\d{8}$', phone):
                raise forms.ValidationError('M-Pesa number must start with 2541 or 2547 and have 12 digits.')
        return phone

class QuarterlyPaymentForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0'
        })
    )
    payment_mode = forms.ChoiceField(
        choices=PaymentTransaction.MODE_CHOICES,
        widget=forms.RadioSelect
    )
    mpesa_phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '254712345678'
        })
    )
    
    def clean_mpesa_phone(self):
        phone = self.cleaned_data.get('mpesa_phone')
        payment_mode = self.cleaned_data.get('payment_mode')
        
        if payment_mode == 'mpesa':
            if not phone:
                raise forms.ValidationError('Phone number is required for M-Pesa payment.')
            phone = phone.strip().replace(' ', '').replace('-', '')
            if not re.match(r'^254[17]\d{8}$', phone):
                raise forms.ValidationError('M-Pesa number must start with 2541 or 2547 and have 12 digits.')
        return phone

class MonthSelectionForm(forms.Form):
    months = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        available_months = kwargs.pop('available_months', [])
        super().__init__(*args, **kwargs)
        
        month_choices = []
        for month in available_months:
            month_choices.append(
                (str(month['id']), f"{month['month_name']} {month['year']} - KES {month['amount']}")
            )
        self.fields['months'].choices = month_choices

class FilterContributionsForm(forms.Form):
    type = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Status'),
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('paid_late', 'Paid Late'),
            ('partial', 'Partial'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    year = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search member...'
        })
    )
    
    def __init__(self, *args, **kwargs):
        type_choices = kwargs.pop('type_choices', [])
        year_choices = kwargs.pop('year_choices', [])
        super().__init__(*args, **kwargs)
        self.fields['type'].choices = [('', 'All Types')] + type_choices
        self.fields['year'].choices = [('', 'All Years')] + [(str(y), str(y)) for y in year_choices]