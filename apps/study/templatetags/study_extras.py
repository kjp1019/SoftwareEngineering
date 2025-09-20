from django import template
from pprint import pformat

register = template.Library()

@register.filter
def proficiency_color(value):
    """숙련도에 따른 색상 클래스를 반환합니다."""
    if value < 2:
        return 'danger'
    elif value < 3:
        return 'warning'
    elif value < 4:
        return 'info'
    elif value < 5:
        return 'primary'
    return 'success'

@register.filter
def multiply(value, arg):
    """두 수를 곱합니다."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def calculate_progress(current, total):
    if total == 0:
        return 0
    return (current / total) * 100

@register.filter
def type(value):
    return value.__class__.__name__

@register.filter
def pprint(value):
    return pformat(value)

@register.filter
def subtract(value, arg):
    """두 값의 차이를 반환하는 템플릿 필터"""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def to_seconds(value):
    """분을 초로 변환"""
    try:
        return float(value) * 60
    except (ValueError, TypeError):
        return 0

@register.filter
def format_study_time(value):
    """학습 시간을 분:초 형식으로 포맷팅"""
    try:
        minutes = int(float(value))  # 정수 부분이 분
        seconds = int((float(value) - minutes) * 60)  # 소수 부분을 초로 변환
        
        if minutes > 0:
            return f"{minutes}분 {seconds}초"
        else:
            return f"{seconds}초"
    except (ValueError, TypeError):
        return "0초"

@register.filter
def get_minutes(value):
    """시간(초)을 분으로 변환"""
    try:
        total_seconds = float(value) * 60  # 분을 초로 변환
        return int(total_seconds // 60)
    except (ValueError, TypeError):
        return 0

@register.filter
def get_seconds(value):
    """시간(초)의 초 부분만 반환"""
    try:
        total_seconds = float(value) * 60  # 분을 초로 변환
        return int(total_seconds % 60)
    except (ValueError, TypeError):
        return 0 