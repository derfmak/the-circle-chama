from django import template

register = template.Library()

MONTHS = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April',
    5: 'May', 6: 'June', 7: 'July', 8: 'August',
    9: 'September', 10: 'October', 11: 'November', 12: 'December'
}

@register.filter
def month_name(month_number):
    try:
        return MONTHS.get(int(month_number), '')
    except (ValueError, TypeError):
        return ''