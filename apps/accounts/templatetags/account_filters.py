from django import template
from django.template.defaultfilters import floatformat

register = template.Library()

@register.filter
def calculate_progress(current, total):
    """현재 경험치와 목표 경험치를 기반으로 진행률을 계산합니다."""
    if total == 0:
        return 0
    return (current / total) * 100

@register.filter
def div(value, arg):
    """나눗셈 연산을 수행합니다."""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def mul(value, arg):
    """곱셈 연산을 수행합니다."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def sub(value, arg):
    """뺄셈 연산을 수행합니다."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0 