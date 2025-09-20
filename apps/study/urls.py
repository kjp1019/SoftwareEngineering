from django.urls import path
from . import views

app_name = 'study'

urlpatterns = [
    # 데일리 미션 관련 URL
    path('daily-mission/', views.daily_mission, name='daily_mission'),
    path('daily-mission/submit/', views.submit_daily_mission, name='submit_daily_mission'),
    path('daily-mission/result/', views.daily_mission_result, name='daily_mission_result'),
    path('daily-mission/modal-shown/', views.daily_mission_modal_shown, name='daily_mission_modal_shown'),

    # 통계 관련 URL
    path('statistics/', views.statistics, name='statistics'),

    # 학습 계획 관련 URL
    path('plans/', views.study_plan_list, name='plan_list'),
    path('plans/create/', views.study_plan_create, name='plan_create'),
    path('plans/<int:plan_id>/', views.study_plan_detail, name='plan_detail'),
    path('plans/<int:plan_id>/edit/', views.study_plan_edit, name='plan_edit'),
    path('plans/<int:plan_id>/delete/', views.study_plan_delete, name='plan_delete'),

    # 학습 세션 관련 URL
    path('session/start/', views.study_session_start, name='session_start'),
    path('session/<int:session_id>/', views.study_session_detail, name='session_detail'),
    path('session/<int:session_id>/end/', views.study_session_end, name='session_end'),
    path('session/save-time/', views.study_session_save_time, name='session_save_time'),

    # 학습 모드 관련 URL
    path('plans/<int:plan_id>/flashcard/', views.flashcard_study, name='flashcard_study'),
    path('plans/<int:plan_id>/vocabulary/', views.vocabulary_study, name='vocabulary_study'),
    path('plans/<int:plan_id>/review/', views.review_study, name='review_study'),

    # 학습 진도 관련 URL
    path('progress/word/<int:word_id>/', views.word_progress_update, name='word_progress_update'),
    path('progress/', views.study_progress, name='progress'),

    # 학습 시간 관련 URL
    path('plans/<int:plan_id>/stats/', views.study_stats_api, name='stats_api'),
    path('save_study_time/', views.save_study_time, name='save_study_time'),

    # 북마크 관련 URL
    path('bookmarks/', views.bookmark_list, name='bookmark_list'),
    path('bookmarks/<int:word_id>/toggle/', views.bookmark_toggle, name='bookmark_toggle'),

    # 복습 일정 관련 URL
    path('schedules/', views.review_schedule_list, name='schedule_list'),
    path('schedules/<int:schedule_id>/update/', views.review_schedule_update, name='schedule_update'),

    # 알림 관련 URL
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/settings/', views.notification_settings, name='notification_settings'),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/<int:notification_id>/delete/', views.delete_notification, name='delete_notification'),
    path('notifications/delete-all/', views.delete_all_notifications, name='delete_all_notifications'),

    # 학습 모드 URL
    path('flashcard/', views.flashcard_study, name='flashcard'),
    path('wordlist/', views.word_list_study, name='wordlist'),
    path('review/', views.review_list, name='review'),
    path('review/start/<int:word_id>/', views.review_start, name='review_start'),
    path('daily-words/', views.daily_words, name='daily_words'),
    path('wrong-notes/', views.wrong_notes, name='wrong_notes'),

    # TTS 관련 URL
    path('text-to-speech/', views.text_to_speech, name='text_to_speech'),

    path('', views.study_home, name='study_home'),

    # 레벨 테스트 관련 URL
    path('level-test/start/', views.level_test_start, name='level_test_start'),
    path('level-test/<int:test_id>/question/<int:question_number>/', views.level_test_question, name='level_test_question'),
    path('level-test/<int:test_id>/complete/', views.level_test_complete, name='level_test_complete'),

    # 친구 관련 URL
    path('friends/', views.friend_list, name='friend_list'),
    path('friend_search/', views.friend_search, name='friend_search'),
    path('friend_request/<int:user_id>/', views.send_friend_request, name='send_friend_request'),
    path('friend_request/<int:request_id>/accept/', views.accept_friend_request, name='accept_friend_request'),
    path('friend_request/<int:request_id>/reject/', views.reject_friend_request, name='reject_friend_request'),
    path('friendship/<int:friendship_id>/delete/', views.delete_friendship, name='delete_friendship'),
    path('friend/<int:friend_id>/wordbook/', views.friend_wordbook, name='friend_wordbook'),

    path('reset-today-sessions/', views.reset_today_sessions, name='reset_today_sessions'),
] 