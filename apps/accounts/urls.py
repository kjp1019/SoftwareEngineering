from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.home, name='home'),  # 메인 페이지
    path('login/', views.login_view, name='login'),  # 로그인
    path('logout/', views.logout_view, name='logout'),  # 로그아웃
    path('signup/', views.signup_view, name='signup'),  # 회원가입
    path('profile/', views.profile_view, name='profile'),  # 프로필
    path('check-nickname/', views.check_nickname, name='check_nickname'),  # 닉네임 중복 체크
    path('delete-account/', views.delete_account, name='delete_account'),  # 회원탈퇴
    
    # 비밀번호 재설정
    path('password_reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html',
             email_template_name='accounts/password_reset_email.html',
             subject_template_name='accounts/password_reset_subject.txt',
             success_url=reverse_lazy('accounts:password_reset_done')
         ),
         name='password_reset'),
    
    path('password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ),
         name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html',
             success_url=reverse_lazy('accounts:password_reset_complete')
         ),
         name='password_reset_confirm'),
    
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ),
         name='password_reset_complete'),
    path('sync-nicknames/', views.sync_nicknames, name='sync_nicknames'),
] 