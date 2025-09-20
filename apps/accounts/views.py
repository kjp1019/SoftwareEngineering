from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import CustomUser, UserProfile, Attendance
from apps.vocabulary.models import Word
from apps.study.models import StudyProgress, UserLevel, StudyPlan
from django.utils import timezone
import random
from datetime import datetime, timedelta
from django.http import JsonResponse
import logging
from apps.study.views import get_todays_word
from django.contrib.admin.views.decorators import staff_member_required
from apps.study.models import DailyMission, DailyMissionModalShown

logger = logging.getLogger(__name__)

# @login_required
def home(request):
    """메인 페이지"""
    context = {}
    
    if request.user.is_authenticated:
        # 전체 학습 진도 조회
        study_progress = StudyProgress.objects.filter(
            user=request.user,
            review_count__gt=0
        )
        
        # 오늘의 학습 현황 (한국 시간 기준)
        current_time = timezone.localtime(timezone.now())
        today = current_time.date()
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        
        # 한국 시간대로 변환
        today_start = timezone.localtime(today_start)
        today_end = timezone.localtime(today_end)
        
        today_progress = study_progress.filter(
            last_reviewed__range=(today_start, today_end)
        ).count()
        
        # 총 학습한 단어 수
        total_studied_words = study_progress.count()
        
        # 오늘의 단어 가져오기
        todays_word = get_todays_word()
        
        # 사용자의 일일 목표
        daily_goal = getattr(request.user.profile, 'daily_goal', 20)  # 기본값 20
        
        # 데일리 미션 완료 여부 확인
        daily_mission_completed = DailyMission.objects.filter(
            user=request.user,
            date=today,
            is_completed=True
        ).exists()
        
        # 데일리 미션 모달 표시 여부 확인
        daily_mission_modal_shown = DailyMissionModalShown.objects.filter(
            user=request.user,
            date=today,
            shown=True
        ).exists()
        
        context.update({
            'today_progress': today_progress,
            'daily_goal': daily_goal,
            'todays_word': todays_word,
            'total_studied_words': total_studied_words,
            'user_profile': request.user.profile,
            'daily_mission_completed': daily_mission_completed,
            'daily_mission_modal_shown': daily_mission_modal_shown
        })
    
    return render(request, 'accounts/home.html', context)

def signup_view(request):
    """회원가입 뷰"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        nickname = request.POST.get('nickname')
        agree = request.POST.get('agree')

        # 유효성 검사
        if not all([username, email, password1, password2, agree]):
            messages.error(request, '모든 필수 항목을 입력해주세요.')
            return redirect('accounts:signup')

        if password1 != password2:
            messages.error(request, '비밀번호가 일치하지 않습니다.')
            return redirect('accounts:signup')

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, '이미 사용 중인 아이디입니다.')
            return redirect('accounts:signup')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, '이미 사용 중인 이메일입니다.')
            return redirect('accounts:signup')

        # 닉네임 중복 체크
        if nickname and UserProfile.objects.filter(nickname=nickname).exists():
            messages.error(request, '이미 사용 중인 닉네임입니다.')
            return redirect('accounts:signup')

        # 사용자 생성 (모든 일반 사용자는 학생으로 생성)
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password1,
            is_student=True,
            nickname=nickname if nickname else ''  # 닉네임이 있으면 바로 저장
        )

        # 프로필 생성 및 닉네임 저장
        if nickname:
            user.profile.nickname = nickname
            user.profile.save()
            user.save()  # User 모델의 변경사항도 저장

        login(request, user)
        messages.success(request, '회원가입이 완료되었습니다.')
        return redirect('accounts:home')

    return render(request, 'accounts/signup.html')

def login_view(request):
    """로그인 뷰"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            if user.is_superuser:
                return redirect('admin_home')
            return redirect('accounts:home')
        else:
            messages.error(request, '아이디 또는 비밀번호가 올바르지 않습니다.')
    
    return render(request, 'accounts/login.html')

@login_required
def logout_view(request):
    """로그아웃 뷰"""
    logout(request)
    return redirect('accounts:login')

@login_required
def profile_view(request):
    """프로필 뷰"""
    logger.debug("====== 프로필 뷰 시작 ======")
    logger.debug(f"현재 사용자: {request.user.username}")
    
    if request.method == 'POST':
        # 프로필 설정 업데이트
        daily_goal = request.POST.get('daily_goal')
        nickname = request.POST.get('nickname')
        bio = request.POST.get('bio')
        dark_mode = request.POST.get('dark_mode') == 'on'

        # 닉네임 중복 체크 (User와 UserProfile 모두 확인)
        if nickname and nickname != request.user.profile.nickname:
            if (UserProfile.objects.filter(nickname=nickname).exists() or 
                CustomUser.objects.filter(nickname=nickname).exists()):
                messages.error(request, '이미 사용 중인 닉네임입니다.')
                return redirect('accounts:profile')

        profile = request.user.profile
        if daily_goal:
            profile.daily_goal = int(daily_goal)
            # 활성화된 학습 계획의 target_words_per_day도 업데이트
            active_plan = StudyPlan.objects.filter(user=request.user, is_active=True).first()
            if active_plan:
                active_plan.target_words_per_day = int(daily_goal)
                active_plan.save()

        # 닉네임 업데이트
        profile.nickname = nickname
        profile.bio = bio
        profile.dark_mode = dark_mode
        profile.save()

        # User 모델에도 닉네임 저장
        user = request.user
        user.nickname = nickname
        user.save()

        messages.success(request, '프로필이 업데이트되었습니다.')
        return redirect('accounts:profile')

    user = request.user
    today = timezone.now().date()
    logger.debug(f"오늘 날짜: {today}")
    
    # 최근 출석 기록 가져오기
    try:
        latest_attendance = user.attendances.latest('check_date')
        logger.debug(f"최근 출석 기록: {latest_attendance.check_date}, streak_days: {latest_attendance.streak_days}")
        
        if latest_attendance.check_date == today:
            streak_days = latest_attendance.streak_days
            logger.debug(f"오늘 출석했음. 현재 연속 출석일: {streak_days}")
        else:
            streak_days = 0
            logger.debug(f"오늘 아직 출석하지 않음. 마지막 출석일: {latest_attendance.check_date}")
    except Exception as e:
        streak_days = 0
        logger.debug(f"출석 기록이 없음. 에러: {str(e)}")
    
    # 깃허브 스타일 출석 데이터 준비 (최근 5주)
    weeks = []
    start_date = today - timedelta(days=34)  # 5주 전
    logger.debug(f"출석 데이터 시작일: {start_date}")
    
    # 출석 기록을 딕셔너리로 변환 (날짜를 키로 사용)
    attendance_dict = {}
    attendance_records = user.attendances.filter(
        check_date__gte=start_date
    ).order_by('check_date')
    
    logger.debug(f"조회된 출석 기록 수: {attendance_records.count()}")
    
    # 각 출석 기록을 딕셔너리에 저장
    current_streak = 0
    prev_date = None
    
    for attendance in attendance_records:
        current_date = attendance.check_date
        
        # 이전 날짜가 있고, 연속된 날짜인 경우
        if prev_date and (current_date - prev_date).days == 1:
            current_streak += 1
        else:
            current_streak = 1
        
        attendance_dict[current_date] = {
            'attended': True,
            'streak': current_streak
        }
        prev_date = current_date
        logger.debug(f"출석일: {current_date}, 연속일수: {current_streak}")
    
    # 주별 데이터 생성
    current_date = start_date
    while current_date <= today:
        week_number = (current_date - start_date).days // 7
        day_number = (current_date - start_date).days % 7
        
        # 새로운 주 시작
        if day_number == 0:
            weeks.append([])
        
        # 해당 날짜의 출석 정보
        attendance_info = attendance_dict.get(current_date, {'attended': False, 'streak': 0})
        streak = attendance_info['streak']
        
        # 연속 출석 수에 따른 색상 레벨 계산
        if streak >= 10:
            streak_level = 4
        elif streak >= 7:
            streak_level = 3
        elif streak >= 4:
            streak_level = 2
        elif streak >= 1:
            streak_level = 1
        else:
            streak_level = 0
        
        # 날짜 데이터 추가
        weeks[week_number].append({
            'date': current_date,
            'attended': attendance_info['attended'],
            'streak': streak,
            'streak_level': streak_level
        })

        logger.debug(f"날짜: {current_date}, 출석: {attendance_info['attended']}, 연속: {streak}, 레벨: {streak_level}")
        current_date += timedelta(days=1)
    
    logger.debug(f"생성된 주 데이터 수: {len(weeks)}")
    
    # 오늘 학습한 단어 수 계산
    today_words = StudyProgress.objects.filter(
        user=user,
        last_reviewed__date=today
    ).count()

    # 총 학습 단어 수 업데이트
    total_studied = StudyProgress.objects.filter(user=user).count()
    user.profile.total_studied_words = total_studied
    user.profile.save()

    context = {
        'user': user,
        'streak_days': streak_days,
        'weeks': weeks,
        'today_progress': today_words,
        'daily_goal': user.profile.daily_goal,
        'debug': True
    }
    
    return render(request, 'accounts/profile.html', context)

def check_nickname(request):
    """닉네임 중복 체크 API"""
    nickname = request.GET.get('nickname', '').strip()
    exists = UserProfile.objects.filter(nickname=nickname).exists()
    return JsonResponse({'exists': exists})

@login_required
def delete_account(request):
    """회원탈퇴"""
    if request.method == 'POST':
        password = request.POST.get('password')
        user = request.user

        # 비밀번호 확인
        if not user.check_password(password):
            messages.error(request, '비밀번호가 올바르지 않습니다.')
            return redirect('accounts:profile')

        # 로그아웃
        logout(request)
        
        # 계정 삭제
        user.delete()
        
        messages.success(request, '회원탈퇴가 완료되었습니다.')
        return redirect('accounts:home')

    return redirect('accounts:profile')

@staff_member_required
def sync_nicknames(request):
    """UserProfile.nickname → User.nickname 일괄 동기화 (관리자용)"""
    updated = 0
    for profile in UserProfile.objects.all():
        if profile.nickname and (not profile.user.nickname or profile.user.nickname != profile.nickname):
            profile.user.nickname = profile.nickname
            profile.user.save()
            updated += 1
    return JsonResponse({'updated': updated, 'status': 'ok'})
