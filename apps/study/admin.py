from django.contrib import admin
from .models import (
    StudyPlan, StudySession, StudyProgress, ReviewSchedule,
    Notification, UserNotificationSettings, LevelTest, TestQuestion, UserTestResult, UserLevel
)

@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'target_words_per_day', 'target_study_time', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'user__username')
    ordering = ('-created_at',)

@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'study_plan', 'start_time', 'study_minutes', 'created_at')
    list_filter = ('start_time', 'created_at')
    search_fields = ('user__username',)
    ordering = ('-start_time', '-created_at')

@admin.register(StudyProgress)
class StudyProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'word', 'proficiency', 'review_count', 'last_reviewed', 'is_bookmarked')
    list_filter = ('proficiency', 'is_bookmarked', 'last_reviewed')
    search_fields = ('user__username', 'word__english', 'word__korean')
    ordering = ('-last_reviewed',)

@admin.register(ReviewSchedule)
class ReviewScheduleAdmin(admin.ModelAdmin):
    list_display = ('user', 'word', 'scheduled_date', 'status', 'completed_at')
    list_filter = ('status', 'scheduled_date')
    search_fields = ('user__username', 'word__english')
    ordering = ('scheduled_date',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'message', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'message']
    ordering = ['-created_at']

@admin.register(UserNotificationSettings)
class UserNotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'review_notifications', 'achievement_notifications', 'reminder_notifications', 'notification_time')
    list_filter = ('review_notifications', 'achievement_notifications', 'reminder_notifications')
    search_fields = ('user__username',)

@admin.register(LevelTest)
class LevelTestAdmin(admin.ModelAdmin):
    list_display = ('title', 'difficulty', 'created_at')
    list_filter = ('difficulty',)
    search_fields = ('title', 'description')

@admin.register(TestQuestion)
class TestQuestionAdmin(admin.ModelAdmin):
    list_display = ('test', 'question_type', 'word', 'points')
    list_filter = ('test', 'question_type')
    search_fields = ('question_text', 'word__english')
    raw_id_fields = ('word',)

@admin.register(UserTestResult)
class UserTestResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'test', 'score', 'level', 'completed_at')
    list_filter = ('level', 'completed_at')
    search_fields = ('user__username',)

@admin.register(UserLevel)
class UserLevelAdmin(admin.ModelAdmin):
    list_display = ('user', 'current_level', 'last_test_date', 'recommended_words_per_day')
    list_filter = ('current_level',)
    search_fields = ('user__username',)
