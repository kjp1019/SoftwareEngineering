from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserProfile

class CustomUserAdmin(UserAdmin):
    """커스텀 사용자 관리자 설정"""
    list_display = ('username', 'email', 'is_student', 'is_teacher', 'is_staff')
    list_filter = ('is_student', 'is_teacher', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email')
    ordering = ('username',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'nickname', 'points', 'level', 'daily_goal', 'created_at']
    search_fields = ['user__username', 'nickname']
    list_filter = ['level', 'daily_goal']
    ordering = ['-created_at']

admin.site.register(CustomUser, CustomUserAdmin)
