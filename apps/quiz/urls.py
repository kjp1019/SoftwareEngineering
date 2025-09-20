from django.urls import path
from . import views

app_name = 'quiz'

urlpatterns = [
    # 퀴즈 홈
    path('', views.quiz_home, name='quiz_home'),
    
    # 일반 단어 테스트
    path('word-test/', views.word_test, name='word_test'),
    
    # 타이머 퀴즈
    path('timer/', views.quiz_timer, name='quiz_timer'),
    
    # 사용자 생성 퀴즈
    path('list/', views.quiz_list, name='quiz_list'),
    path('create/', views.quiz_create, name='quiz_create'),
    path('<int:quiz_id>/', views.quiz_detail, name='quiz_detail'),
    path('<int:quiz_id>/delete/', views.quiz_delete, name='quiz_delete'),
    path('<int:quiz_id>/start/', views.quiz_start, name='quiz_start'),
    path('<int:quiz_id>/submit/', views.quiz_submit, name='quiz_submit'),
    
    # 퀴즈 응시 기록
    path('history/<int:attempt_id>/', views.quiz_history_detail, name='quiz_history_detail'),
    
    # 한->영 객관식 퀴즈
    path('ko-to-en/multiple/', views.ko_to_en_multiple, name='ko_to_en_multiple'),
    
    # 오답 노트
    path('wrong-answers/', views.wrong_answer_notes, name='wrong_answer_notes'),
    path('all-wrong-answers/', views.all_wrong_answer_notes, name='all_wrong_answer_notes'),
    path('wrong-answers/add/', views.add_wrong_answer, name='add_wrong_answer'),
    path('wrong-answers/<int:note_id>/toggle-mastered/', views.toggle_mastered, name='toggle_mastered'),
    
    # 한->영 주관식(타이핑) 퀴즈
    path('ko-to-en/typing/', views.ko_to_en_typing, name='ko_to_en_typing'),
    
    # 영어->한국어 객관식 퀴즈
    path('en-to-ko-multiple/', views.en_to_ko_multiple, name='en_to_ko_multiple'),
    
    # 영어->한국어 주관식(타이핑) 퀴즈
    path('en-to-ko-typing/', views.en_to_ko_typing, name='en_to_ko_typing'),
    
    # 즐겨찾기 단어 퀴즈
    path('bookmark/multiple/', views.bookmark_multiple, name='bookmark_multiple'),
    path('bookmark/typing/', views.bookmark_typing, name='bookmark_typing'),
] 