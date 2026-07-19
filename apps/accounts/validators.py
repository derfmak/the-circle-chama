import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class CustomPasswordValidator:
    def __init__(self, min_length=12):
        self.min_length = min_length

    def validate(self, password, user=None):
        if not password:
            raise ValidationError(_('Password cannot be empty.'))

        if len(password) < self.min_length:
            raise ValidationError(_(f'Password must be at least {self.min_length} characters long.'))

        if user:
            email = user.email.lower() if user.email else ''
            if email:
                email_prefix = email.split('@')[0]
                if email_prefix in password.lower():
                    raise ValidationError(_('Password cannot contain parts of your email.'))

                email_parts = email_prefix.replace('.', ' ').replace('_', ' ').split()
                for part in email_parts:
                    if len(part) > 3 and part in password.lower():
                        raise ValidationError(_('Password cannot contain parts of your email.'))

            first_name = user.first_name.lower() if user.first_name else ''
            last_name = user.last_name.lower() if user.last_name else ''

            if first_name and first_name in password.lower():
                raise ValidationError(_('Password cannot contain your first name.'))
            if last_name and last_name in password.lower():
                raise ValidationError(_('Password cannot contain your last name.'))

            username = user.username.lower() if hasattr(user, 'username') and user.username else ''
            if username and username in password.lower():
                raise ValidationError(_('Password cannot contain your username.'))

        common_patterns = [
            'password', '123456', 'qwerty', 'abc123', 'admin', 'letmein', 'welcome',
            'monkey', 'dragon', 'master', 'hello', 'freedom', 'whatever', 'trustno1',
            '123456789', '12345678', '1234567', '123456', '12345'
        ]

        for pattern in common_patterns:
            if pattern in password.lower():
                raise ValidationError(_('Password is too common. Choose a more secure password.'))

        if re.search(r'(.)\1{2,}', password):
            raise ValidationError(_('Password cannot have consecutive repeating characters.'))

        keyboard_rows = [
            'qwertyuiop', 'asdfghjkl', 'zxcvbnm',
            '1234567890', '!@#$%^&*()'
        ]
        for row in keyboard_rows:
            for i in range(len(row) - 3):
                pattern = row[i:i+4]
                if pattern in password.lower() or pattern[::-1] in password.lower():
                    raise ValidationError(_('Password contains sequential keyboard patterns.'))

        numeric_sequences = ['0123', '1234', '2345', '3456', '4567', '5678', '6789', '7890', '0987']
        for seq in numeric_sequences:
            if seq in password:
                raise ValidationError(_('Password contains sequential numbers.'))

        if not re.search(r'[A-Z]', password):
            raise ValidationError(_('Password must contain at least one uppercase letter.'))
        if not re.search(r'[a-z]', password):
            raise ValidationError(_('Password must contain at least one lowercase letter.'))
        if not re.search(r'\d', password):
            raise ValidationError(_('Password must contain at least one digit.'))
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(_('Password must contain at least one special character.'))

        if re.match(r'^[A-Z]+$', password):
            raise ValidationError(_('Password cannot be all uppercase letters.'))
        if re.match(r'^[a-z]+$', password):
            raise ValidationError(_('Password cannot be all lowercase letters.'))
        if re.match(r'^\d+$', password):
            raise ValidationError(_('Password cannot be all numbers.'))
        if re.match(r'^[!@#$%^&*(),.?":{}|<>]+$', password):
            raise ValidationError(_('Password cannot be all special characters.'))

        if len(password) > 128:
            raise ValidationError(_('Password is too long. Maximum length is 128 characters.'))

    def get_help_text(self):
        return _(
            f'Your password must be at least {self.min_length} characters long, contain uppercase, '
            'lowercase, digits, special characters, and cannot contain personal information. '
            'Avoid common patterns and sequential characters.'
        )