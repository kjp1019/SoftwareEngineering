from django.contrib import admin
from .models import Quiz, QuizQuestion, QuizAttempt, QuizAnswerHistory

class QuizQuestionInline(admin.TabularInline):
    """퀴즈 상세 페이지에서 문제를 함께 관리할 수 있도록 설정"""
    model = QuizQuestion
    extra = 1

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """퀴즈 관리자 설정"""
    list_display = ('title', 'quiz_type', 'difficulty', 'created_by', 'created_at', 'is_public')
    list_filter = ('quiz_type', 'difficulty', 'is_public', 'created_at')
    search_fields = ('title', 'description', 'created_by__username')
    inlines = [QuizQuestionInline]
    ordering = ('-created_at',)

@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    """퀴즈 문제 관리자 설정"""
    list_display = ('quiz', 'word', 'order')
    list_filter = ('quiz__quiz_type', 'quiz__difficulty')
    search_fields = ('quiz__title', 'word__english', 'word__korean')
    ordering = ('quiz', 'order')

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    """퀴즈 응시 기록 관리자 설정"""
    list_display = ('user', 'quiz', 'started_at', 'completed_at', 'score', 'accuracy_rate')
    list_filter = ('quiz__quiz_type', 'started_at')
    search_fields = ('user__username', 'quiz__title')
    ordering = ('-started_at',)

@admin.register(QuizAnswerHistory)
class QuizAnswerHistoryAdmin(admin.ModelAdmin):
    """퀴즈 답안 기록 관리자 설정"""
    list_display = ('attempt', 'question', 'is_correct', 'answered_at')
    list_filter = ('is_correct', 'answered_at')
    search_fields = ('attempt__user__username', 'question__quiz__title')
    ordering = ('-answered_at',)
