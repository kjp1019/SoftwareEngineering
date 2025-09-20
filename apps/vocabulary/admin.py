from django.contrib import admin
from .models import Word, WordBookmark

@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    """단어 관리자 설정"""
    list_display = ('english', 'korean', 'part_of_speech', 'difficulty', 'created_at')
    list_filter = ('difficulty', 'part_of_speech')
    search_fields = ('english', 'korean')
    ordering = ('english',)

@admin.register(WordBookmark)
class WordBookmarkAdmin(admin.ModelAdmin):
    """단어 북마크 관리자 설정"""
    list_display = ('user', 'word', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'word__english')
