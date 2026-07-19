from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import User
import re


class MemberLoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Email Address',
        'autocomplete': 'email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Password',
        'autocomplete': 'current-password',
        'onpaste': 'return false;',
        'ondrop': 'return false;'
    }))


class AdminLoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Admin Email',
        'autocomplete': 'email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Password',
        'autocomplete': 'current-password',
        'onpaste': 'return false;',
        'ondrop': 'return false;'
    }))


class MemberApplicationForm(forms.Form):
    full_name = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'e.g. Jane Wanjiku Otieno',
        'autocomplete': 'name'
    }))
    id_number = forms.CharField(max_length=8, min_length=8, required=True, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'e.g. 30112233',
        'inputmode': 'numeric',
        'autocomplete': 'off'
    }))
    phone_number = forms.CharField(max_length=15, required=True, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'e.g. 0712345678',
        'inputmode': 'numeric',
        'autocomplete': 'tel'
    }))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'e.g. jane@example.com',
        'autocomplete': 'email'
    }))
    agree_terms = forms.BooleanField(required=False)
    agree_privacy = forms.BooleanField(required=False)

    def clean_full_name(self):
        name = self.cleaned_data.get('full_name', '').strip()
        if len(name) < 3:
            raise ValidationError('Full name must be at least 3 characters.')
        if not re.match(r'^[A-Za-z\s\'-]+$', name):
            raise ValidationError('Name can only contain letters, spaces, apostrophes, and hyphens.')
        return name

    def clean_id_number(self):
        id_number = self.cleaned_data.get('id_number', '').strip()
        if not re.match(r'^\d{8}$', id_number):
            raise ValidationError('ID number must be exactly 8 digits, numbers only.')
        return id_number

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip().replace(' ', '').replace('-', '')
        if not re.match(r'^(07|01)\d{8}$', phone) and not re.match(r'^254[17]\d{8}$', phone):
            raise ValidationError('Phone number must be a valid Kenyan number.')
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError('This email is already registered.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        agree_terms = cleaned_data.get('agree_terms')
        agree_privacy = cleaned_data.get('agree_privacy')

        if not agree_terms:
            self.add_error('agree_terms', 'You must agree to the Terms of Service.')
        if not agree_privacy:
            self.add_error('agree_privacy', 'You must agree to the Privacy Policy.')

        return cleaned_data


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Registered Email'
    }))


class ResetCodeForm(forms.Form):
    code = forms.CharField(max_length=6, min_length=6, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter 6-digit code',
        'autocomplete': 'off'
    }))


class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'New Password',
        'onpaste': 'return false;'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Confirm Password',
        'onpaste': 'return false;'
    }))

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        if password:
            validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            raise ValidationError('Passwords do not match.')

        return cleaned_data


class InitialPasswordChangeForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'New Password',
        'onpaste': 'return false;'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Confirm New Password',
        'onpaste': 'return false;'
    }))

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        if self.user:
            validate_password(password, self.user)
        return password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            raise ValidationError('Passwords do not match.')

        return cleaned_data


class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Current Password',
        'onpaste': 'return false;'
    }))
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'New Password',
        'onpaste': 'return false;'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Confirm New Password',
        'onpaste': 'return false;'
    }))

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        if self.user:
            validate_password(password, self.user)
        return password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            raise ValidationError('Passwords do not match.')

        return cleaned_data


class AdminForgotPasswordForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Admin Email'
    }))


class AdminVerifyCodeForm(forms.Form):
    code = forms.CharField(max_length=6, min_length=6, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter 6-digit code',
        'autocomplete': 'off'
    }))


class AdminResetPasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'New Password',
        'onpaste': 'return false;'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Confirm Password',
        'onpaste': 'return false;'
    }))

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        if password:
            validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            raise ValidationError('Passwords do not match.')

        return cleaned_data


class AdminInitialPasswordChangeForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'New Password',
        'onpaste': 'return false;'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Confirm Password',
        'onpaste': 'return false;'
    }))

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        if self.user:
            validate_password(password, self.user)
        return password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            raise ValidationError('Passwords do not match.')

        return cleaned_data