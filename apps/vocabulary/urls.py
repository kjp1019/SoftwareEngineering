from django.urls import path
from . import views

app_name = 'vocabulary'

urlpatterns = [
    path('words/', views.word_list, name='word_list'),  # 단어 목록
    path('words/add/', views.word_add, name='word_add'),
    path('words/<int:word_id>/edit/', views.word_edit, name='word_edit'),
    path('words/<int:word_id>/delete/', views.word_delete, name='word_delete'),
    path('words/<int:word_id>/', views.word_detail, name='word_detail'),  # 단어 상세
    path('words/<int:word_id>/toggle_bookmark/', views.toggle_bookmark, name='toggle_bookmark'),
    path('words/<int:word_id>/toggle_personal/', views.toggle_personal_word, name='toggle_personal_word'),
    path('words/bookmarked/', views.bookmarked_words, name='bookmarked_words'),
    path('personal/', views.personal_word_list, name='personal_word_list'),
] 