from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """주어진 값에 인자를 곱합니다."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0 