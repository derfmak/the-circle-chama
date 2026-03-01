import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class CustomPasswordValidator:
    def validate(self, password, user=None):
        if user:
            email = user.email.lower()
            first_name = user.first_name.lower()
            last_name = user.last_name.lower()
            
            if email.split('@')[0] in password.lower():
                raise ValidationError(_('Password cannot contain parts of your email.'))
            if first_name in password.lower() or last_name in password.lower():
                raise ValidationError(_('Password cannot contain your name.'))
        
        if re.search(r'(.)\1{2,}', password):
            raise ValidationError(_('Password cannot have consecutive repeating characters.'))
        
        if not re.search(r'[A-Z]', password):
            raise ValidationError(_('Password must contain at least one uppercase letter.'))
        if not re.search(r'[a-z]', password):
            raise ValidationError(_('Password must contain at least one lowercase letter.'))
        if not re.search(r'\d', password):
            raise ValidationError(_('Password must contain at least one digit.'))
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(_('Password must contain at least one special character.'))

    def get_help_text(self):
        return _(
            'Your password must be at least 12 characters long, contain uppercase, '
            'lowercase, digits, special characters, and cannot contain personal information.'
        )