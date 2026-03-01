from django import template

register = template.Library()

MONTH_NAMES = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April',
    5: 'May', 6: 'June', 7: 'July', 8: 'August',
    9: 'September', 10: 'October', 11: 'November', 12: 'December'
}

@register.filter
def month_name(month_number):
    try:
        month_num = int(month_number)
        return MONTH_NAMES.get(month_num, '')
    except (ValueError, TypeError):
        return ''