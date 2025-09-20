from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.utils.dateparse import parse_time
from django.db.models.functions import TruncDate
from .models import StudyPlan, StudySession, StudyProgress, ReviewSchedule, Notification, UserNotificationSettings, WordStudyHistory, LevelTest, UserTestResult, TestQuestion, UserLevel, DailyGoal, StudyNotification, Friendship, FriendRequest, DailyMission, DailyMissionModalShown
from apps.vocabulary.models import Word, PersonalWordList
from apps.accounts.models import CustomUser
from apps.quiz.models import QuizAnswerHistory, WrongAnswerNote, QuizAttempt
from apps.accounts.models import UserProfile
from datetime import datetime, timedelta, time
from django.db.models import Sum, Count, Avg, Q, Max
import json
from .utils import (
    check_and_create_review_notification,
    check_and_create_achievement_notifications,
    check_and_create_reminder_notification
)
import random
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.db import models
from django.core.paginator import Paginator
from gtts import gTTS
import os
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from random import shuffle
from collections import defaultdict
import logging
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

User = get_user_model()

# Create your views here.

class WordJSONEncoder(DjangoJSONEncoder):
    """단어 객체를 JSON으로 변환하는 인코더"""
    def default(self, obj):
        if isinstance(obj, Word):
            return {
                'id': obj.id,
                'english': obj.english,
                'korean': obj.korean,
                'example_sentence': obj.example_sentence,
                'example_translation': obj.example_translation,
                'part_of_speech': obj.part_of_speech,
                'difficulty': obj.difficulty
            }
        return super().default(obj)

class WordEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, Word):
            return {
                'id': obj.id,
                'english': obj.english,
                'korean': obj.korean,
                'example_sentence': obj.example_sentence,
                'example_translation': obj.example_translation,
                'part_of_speech': obj.part_of_speech,
                'difficulty': obj.difficulty
            }
        return super().default(obj)

def get_todays_word():
    """오늘의 단어를 가져오는 함수"""
    today = timezone.localtime().date()
    
    # 오늘의 단어가 이미 설정되어 있는지 확인
    todays_word = Word.objects.filter(daily_word_date=today).first()
    
    if todays_word:
        return todays_word
    
    # 새로운 오늘의 단어 선택
    words = Word.objects.all()
    if words.exists():
        # 이전 오늘의 단어 표시 제거
        Word.objects.filter(daily_word_date=today).update(daily_word_date=None)
        
        # 새로운 단어 선택
        new_word = random.choice(words)
        new_word.daily_word_date = today
        new_word.save()
        
        return new_word
    return None

@login_required
def study_home(request):
    """학습 홈 뷰"""
    user_profile = request.user.profile
    study_plans = StudyPlan.objects.filter(user=request.user).order_by('-created_at')
    
    # 오늘의 단어 가져오기
    todays_word = get_todays_word()
    
    # 오늘 학습한 단어 수 (고유 단어 기준)
    current_time = timezone.localtime(timezone.now())
    today = current_time.date()
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    
    # 한국 시간대로 변환
    today_start = timezone.localtime(today_start)
    today_end = timezone.localtime(today_end)
    
    today_words = StudyProgress.objects.filter(
        user=request.user,
        last_reviewed__range=(today_start, today_end),
        review_count__gt=0
    ).count()
    
    # 연속 출석일 계산
    streak_days = 0
    current_date = today
    while True:
        has_study = StudyProgress.objects.filter(
            user=request.user,
            last_reviewed__date=current_date,
            review_count__gt=0
        ).exists()
        if has_study:
            streak_days += 1
            current_date -= timezone.timedelta(days=1)
        else:
            break
    
    # 주간 달성률 계산 (고유 단어 수 기준)
    week_start = today - timezone.timedelta(days=today.weekday())
    week_end = week_start + timezone.timedelta(days=6)
    
    weekly_goals = user_profile.daily_goal * 7
    weekly_achieved = StudyProgress.objects.filter(
        user=request.user,
        last_reviewed__date__range=[week_start, week_end],
        review_count__gt=0
    ).count()
    
    weekly_achievement_rate = min(100, int((weekly_achieved / weekly_goals) * 100)) if weekly_goals > 0 else 0
    
    # 경험치 계산 (학습한 단어 수 * 10)
    experience = StudyProgress.objects.filter(
        user=request.user,
        review_count__gt=0
    ).count() * 10

    # 틀린 단어 목록 가져오기 (상위 5개)
    wrong_answers = WrongAnswerNote.objects.filter(
        user=request.user
    ).select_related('word').order_by('-created_at')[:5]
    
    context = {
        'user_profile': user_profile,
        'study_plans': study_plans,
        'today_words': today_words,
        'total_studied_words': StudyProgress.objects.filter(user=request.user, review_count__gt=0).count(),
        'weekly_achievement_rate': weekly_achievement_rate,
        'streak_days': streak_days,
        'daily_goal': user_profile.daily_goal,
        'experience': experience,
        'todays_word': todays_word,
        'wrong_answers': wrong_answers,  # 틀린 단어 목록 추가
    }
    
    return render(request, 'study/home.html', context)

@login_required
def wrong_notes(request):
    """오답 노트 뷰"""
    # 사용자의 오답 기록을 가져옵니다
    wrong_answers = WordStudyHistory.objects.filter(
        user=request.user,
        is_correct=False
    ).select_related('word').annotate(
        wrong_count=Count('id'),
        last_attempt=Max('created_at')
    ).values(
        'word__english',
        'word__korean',
        'wrong_count',
        'last_attempt'
    ).order_by('-wrong_count', '-last_attempt')

    wrong_answers_list = list(wrong_answers)
    
    context = {
        'wrong_answers': wrong_answers_list,
        'has_wrong_answers': bool(wrong_answers_list),
        'wrong_answers_count': len(wrong_answers_list)
    }
    
    # 테스트 템플릿 사용 (정상 작동하는 버전)
    template_name = 'study/wrong_notes_test.html'
    return render(request, template_name, context)

@login_required
def statistics(request):
    """학습 통계 대시보드 뷰"""
    user = request.user
    # 누적 통계
    total_words_studied = StudyProgress.objects.filter(user=user, review_count__gt=0).count()
    mastered_words = StudyProgress.objects.filter(user=user, proficiency=5).count()
    needs_review = StudyProgress.objects.filter(user=user, proficiency__lt=5, review_count__gt=0).count()
    
    # 디버그 로그 추가
    print(f"\n=== 학습 통계 디버깅 ===")
    print(f"사용자: {user.username} (ID: {user.id})")
    print(f"전체 학습 단어 수: {total_words_studied}")
    print(f"완벽히 암기한 단어 수: {mastered_words}")
    print(f"복습이 필요한 단어 수: {needs_review}")
    print("=======================\n")
    
    total_study_minutes = StudySession.objects.filter(user=user, end_time__isnull=False).aggregate(total=Sum('study_minutes'))['total'] or 0
    total_study_minutes = round(total_study_minutes)  # 정수로 반올림
    total_study_hours = round(total_study_minutes / 60, 1)
    
    # 시간과 분 계산
    hours = total_study_minutes // 60
    minutes = total_study_minutes % 60

    # 오늘 날짜 (한국시간)
    today = timezone.localtime().date()
    week_ago = today - timedelta(days=6)
    month_ago = today - timedelta(days=29)

    # 주간/월간 학습 데이터 (파이썬에서 직접 변환)
    week_counts = defaultdict(int)
    month_counts = defaultdict(int)
    accuracy_week = defaultdict(list)

    progresses = StudyProgress.objects.filter(user=user, review_count__gt=0)
    for p in progresses:
        reviewed_local = timezone.localtime(p.last_reviewed)
        reviewed_date = reviewed_local.date()
        if week_ago <= reviewed_date <= today:
            week_counts[reviewed_date] += 1
            accuracy_week[reviewed_date].append(p.proficiency)
        if month_ago <= reviewed_date <= today:
            month_counts[reviewed_date] += 1

    # 주간 데이터 리스트화 (누락된 날짜는 0)
    week_dates = [week_ago + timedelta(days=i) for i in range(7)]
    weekly_counts = [week_counts[d] for d in week_dates]
    weekly_labels = [d.strftime('%m-%d') for d in week_dates]
    # 월간 데이터 리스트화
    month_dates = [month_ago + timedelta(days=i) for i in range(30)]
    monthly_counts = [month_counts[d] for d in month_dates]
    monthly_labels = [d.strftime('%m-%d') for d in month_dates]

    # 주간 정확도
    accuracy_data = []
    for d in week_dates:
        if accuracy_week[d]:
            avg = sum(accuracy_week[d]) / len(accuracy_week[d])
            accuracy_data.append(round(avg, 1))
        else:
            accuracy_data.append(0)

    # 오늘 학습한 단어 수
    today_words_studied = week_counts[today]
    
    # 일일 목표 가져오기
    daily_goal = DailyGoal.objects.filter(
        user=user,
        date=today
    ).first()
    
    if not daily_goal:
        daily_goal = DailyGoal.objects.create(
            user=user,
            date=today,
            words=user.profile.daily_goal,
            study_time=5  # 기본값 5분 설정 (필드 참조 제거)
        )
    
    daily_achievement = min(int(today_words_studied / daily_goal.words * 100), 100) if daily_goal.words > 0 else 0

    # 최근 퀴즈 기록 가져오기
    recent_quiz_attempts = QuizAttempt.objects.filter(
        user=request.user,
        completed_at__isnull=False
    ).order_by('-completed_at')[:5]

    context = {
        'total_words_studied': total_words_studied,
        'mastered_words': mastered_words,
        'needs_review': needs_review,
        'total_study_hours': total_study_hours,
        'total_study_minutes': total_study_minutes,
        'study_hours': hours,  # 시간 추가
        'study_minutes': minutes,  # 분 추가
        'daily_goal': daily_goal,
        'daily_achievement': daily_achievement,
        'today_words_studied': today_words_studied,
        'weekly_labels': weekly_labels,
        'weekly_counts': weekly_counts,
        'monthly_labels': monthly_labels,
        'monthly_counts': monthly_counts,
        'accuracy_data': accuracy_data,
        'recent_quiz_attempts': recent_quiz_attempts,
        'any_weekly_data': any(weekly_counts),  # 주간 데이터 존재 여부
        'any_monthly_data': any(monthly_counts),  # 월간 데이터 존재 여부
    }
    
    return render(request, 'study/statistics.html', context)

@login_required
def daily_words(request):
    """오늘의 단어 목록을 보여줍니다."""
    # 사용자의 학습 계획 가져오기
    study_plan = StudyPlan.objects.filter(user=request.user, is_active=True).first()
    target_words_count = 10  # 기본값
    
    if study_plan:
        target_words_count = study_plan.target_words_per_day
    
    # 오늘 날짜 가져오기 (한국 시간 기준)
    today = timezone.localtime().date()
    
    # 이미 학습한 단어 제외
    learned_words = StudyProgress.objects.filter(
        user=request.user,
        review_count__gt=0
    ).values_list('word_id', flat=True)
    
    # 오늘의 단어 가져오기 (날짜 기준으로 캐싱)
    daily_words = Word.objects.filter(
        daily_word_date=today
    ).exclude(
        id__in=learned_words
    )[:target_words_count]
    
    # 오늘의 단어가 없거나 부족한 경우 새로 생성
    if not daily_words or daily_words.count() < target_words_count:
        # 이전 오늘의 단어 표시 제거
        Word.objects.filter(daily_word_date=today).update(daily_word_date=None)
        
        # 새로운 단어 선택
        new_words = Word.objects.exclude(
            id__in=learned_words
        ).order_by('?')[:target_words_count]
        
        # 선택된 단어들을 오늘의 단어로 표시
        for word in new_words:
            word.daily_word_date = today
            word.save()
        
        daily_words = new_words
    
    if not daily_words:
        messages.info(request, '모든 단어를 학습하셨습니다! 복습을 통해 단어 실력을 더욱 향상시켜보세요.')
    
    return render(request, 'study/daily_words.html', {
        'daily_words': daily_words,
        'today': today
    })

@login_required
def review_list(request):
    """복습 목록"""
    # 복습이 필요한 단어들을 가져옵니다
    review_schedules = ReviewSchedule.objects.filter(
        user=request.user,
        scheduled_date__lte=timezone.now(),
        status='pending'
    ).select_related('word').order_by('scheduled_date')

    return render(request, 'study/review_list.html', {
        'review_schedules': review_schedules
    })

# 학습 계획 관련 뷰
@login_required
def study_plan_list(request):
    plans = StudyPlan.objects.filter(user=request.user)
    return render(request, 'study/plan_list.html', {'plans': plans})

@login_required
def study_plan_create(request):
    # 이미 학습 계획이 있는지 확인
    existing_plan = StudyPlan.objects.filter(user=request.user).first()
    if existing_plan:
        messages.error(request, '이미 학습 계획이 존재합니다. 레벨 테스트를 통해 자동으로 생성된 학습 계획만 사용할 수 있습니다.')
        return redirect('study:plan_list')

    if request.method == 'POST':
        title = request.POST.get('title')
        target_words = request.POST.get('target_words_per_day')
        target_study_time = request.POST.get('target_study_time')

        # 유효성 검사
        if not all([title, target_words, target_study_time]):
            messages.error(request, '모든 필수 항목을 입력해주세요.')
            return redirect('study:plan_create')

        try:
            target_words = int(target_words)
            target_study_time = int(target_study_time)
            
            # 학습 시간은 5분에서 30분 사이
            if target_study_time < 5 or target_study_time > 30:
                messages.error(request, '학습 시간은 5분에서 30분 사이여야 합니다.')
                return redirect('study:plan_create')
            
            # 학습 단어 수는 10개 단위로 10개에서 100개까지
            if target_words < 10 or target_words > 100 or target_words % 10 != 0:
                messages.error(request, '학습할 단어 수는 10개 단위로 10개에서 100개까지 설정할 수 있습니다.')
                return redirect('study:plan_create')
                
            plan = StudyPlan.objects.create(
                user=request.user,
                title=title,
                target_words_per_day=target_words,
                target_study_time=target_study_time
            )
            messages.success(request, '학습 계획이 생성되었습니다.')
            return redirect('study:plan_detail', plan_id=plan.id)
        except ValueError:
            messages.error(request, '올바른 숫자를 입력해주세요.')
            return redirect('study:plan_create')
            
    return render(request, 'study/plan_create.html')

@login_required
def study_plan_detail(request, plan_id):
    """학습 계획 상세 보기"""
    plan = get_object_or_404(StudyPlan, id=plan_id, user=request.user)
    
    # 오늘의 학습 현황 (한국 시간 기준)
    current_time = timezone.localtime(timezone.now())
    today = current_time.date()
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    
    # 한국 시간대로 변환
    today_start = timezone.localtime(today_start)
    today_end = timezone.localtime(today_end)
    
    # 오늘 학습한 단어 수
    today_progress = StudyProgress.objects.filter(
        user=request.user,
        last_reviewed__range=(today_start, today_end),
        review_count__gt=0
    ).count()
    
    # 사용자의 일일 목표
    daily_goal = getattr(request.user.profile, 'daily_goal', 20)  # 기본값 20
    
    # 오늘의 학습 시간 계산
    daily_study_time = StudySession.objects.filter(
        user=request.user,
        start_time__range=(today_start, today_end)
    ).aggregate(total=Sum('daily_study_minutes'))['total'] or 0
    
    # 전체 학습 시간 계산
    total_study_time = StudySession.objects.filter(
        user=request.user,
        end_time__isnull=False
    ).aggregate(total=Sum('study_minutes'))['total'] or 0
    
    return render(request, 'study/plan_detail.html', {
        'plan': plan,
        'daily_goal': daily_goal,
        'today_progress': today_progress,
        'total_study_time': total_study_time,
        'daily_study_time': daily_study_time  # 오늘의 학습 시간 추가
    })

@login_required
def study_plan_edit(request, plan_id):
    plan = get_object_or_404(StudyPlan, id=plan_id, user=request.user)
    if request.method == 'POST':
        title = request.POST.get('title')
        target_words = request.POST.get('target_words_per_day')
        target_study_time = request.POST.get('target_study_time')

        # 유효성 검사
        if not all([title, target_words, target_study_time]):
            messages.error(request, '모든 필수 항목을 입력해주세요.')
            return redirect('study:plan_edit', plan_id=plan.id)

        try:
            target_words = int(target_words)
            target_study_time = int(target_study_time)
            
            if target_study_time < 5 or target_study_time > 180:
                messages.error(request, '학습 시간은 5분에서 180분 사이여야 합니다.')
                return redirect('study:plan_edit', plan_id=plan.id)
                
            plan.title = title
            plan.target_words_per_day = target_words
            plan.target_study_time = target_study_time
            plan.save()
            
            # daily_goal 동기화
            request.user.profile.daily_goal = target_words
            request.user.profile.save()
            
            messages.success(request, '학습 계획이 수정되었습니다.')
            return redirect('study:plan_detail', plan_id=plan.id)
        except ValueError:
            messages.error(request, '올바른 숫자를 입력해주세요.')
            return redirect('study:plan_edit', plan_id=plan.id)
            
    return render(request, 'study/plan_edit.html', {'plan': plan})

@login_required
def study_plan_delete(request, plan_id):
    plan = get_object_or_404(StudyPlan, id=plan_id, user=request.user)
    if request.method == 'POST':
        plan.delete()
        messages.success(request, '학습 계획이 삭제되었습니다.')
        return redirect('study:plan_list')
    return render(request, 'study/plan_delete.html', {'plan': plan})

# 학습 세션 관련 뷰
@login_required
def study_session_start(request):
    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        study_type = request.POST.get('study_type')
        plan = get_object_or_404(StudyPlan, id=plan_id, user=request.user)
        
        # 학습 유형에 따라 적절한 URL로 리다이렉트
        if study_type == 'flashcard':
            return redirect('study:flashcard_study', plan_id=plan_id)
        elif study_type == 'word_list':
            return redirect('study:vocabulary_study', plan_id=plan_id)
        elif study_type == 'review':
            return redirect('study:review_study', plan_id=plan_id)
            
    plans = StudyPlan.objects.filter(user=request.user, is_active=True)
    return render(request, 'study/session_start.html', {'plans': plans})

@login_required
def study_session_detail(request, session_id):
    session = get_object_or_404(StudySession, id=session_id, user=request.user)
    progress = session.progress.all()
    return render(request, 'study/session_detail.html', {
        'session': session,
        'progress': progress
    })

@login_required
def study_session_end(request, session_id):
    try:
        session = get_object_or_404(StudySession, id=session_id, user=request.user)
        
        if session.end_time:
            return redirect('study:plan_detail', plan_id=session.study_plan_id)
        
        end_time = timezone.now()
        elapsed_minutes = (end_time - session.start_time).total_seconds() / 60
        
        # study_minutes와 daily_study_minutes 모두 업데이트
        session.study_minutes = round(elapsed_minutes, 2)
        session.daily_study_minutes = round(elapsed_minutes, 2)
        session.end_time = end_time
        session.save()
        
        # 학습 시간 메시지 표시
        minutes = int(elapsed_minutes)
        seconds = int((elapsed_minutes - minutes) * 60)
        if minutes > 0:
            time_str = f"{minutes}분 {seconds}초"
        else:
            time_str = f"{seconds}초"
        messages.success(request, f'학습 세션이 종료되었습니다. (학습 시간: {time_str})')
        
        return redirect('study:plan_detail', plan_id=session.study_plan_id)
    except StudySession.DoesNotExist:
        messages.error(request, '세션을 찾을 수 없습니다.')
        return redirect('study:home')

@login_required
def study_session_save_time(request):
    """학습 시간 저장 API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            minutes = data.get('minutes', 0)
            
            # 현재 활성화된 학습 세션 가져오기
            session = StudySession.objects.filter(
                user=request.user,
                end_time__isnull=True
            ).first()
            
            if session:
                # study_minutes와 daily_study_minutes 모두 업데이트
                session.study_minutes = minutes
                session.daily_study_minutes = minutes
                session.save()
            
            return JsonResponse({
                'success': True,
                'study_minutes': minutes
            })
            
        except Exception as e:
            print(f"[ERROR] 세션 저장 실패: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
            
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

# 학습 모드 관련 뷰
@login_required
def flashcard_study(request, plan_id):
    """플래시카드 학습 뷰"""
    print("\n=== 플래시카드 학습 시작 디버깅 ===")
    plan = get_object_or_404(StudyPlan, id=plan_id, user=request.user)
    
    # 이미 학습한 단어 제외
    learned_words = StudyProgress.objects.filter(
        user=request.user,
        review_count__gt=0
    ).values_list('word_id', flat=True)
    
    # 학습할 단어 가져오기
    study_words = Word.objects.exclude(
        id__in=learned_words
    ).order_by('?')[:plan.target_words_per_day]
    
    # 학습 세션 생성
    session = StudySession.objects.create(
        user=request.user,
        study_plan=plan,
        study_type='flashcard',
        start_time=timezone.now()
    )
    print(f"[DEBUG] 새 학습 세션 생성됨 (ID: {session.id})")
    print(f"[DEBUG] 시작 시간: {session.start_time}")
    
    # 단어 데이터를 JSON으로 변환
    words_data = [
        {
            'id': word.id,
            'english': word.english,
            'korean': word.korean,
            'example_sentence': word.example_sentence,
            'example_translation': word.example_translation,
            'part_of_speech': word.part_of_speech,
            'difficulty': word.difficulty
        }
        for word in study_words
    ]
    
    print(f"[DEBUG] 학습할 단어 수: {len(study_words)}")
    print("=== 플래시카드 학습 시작 디버깅 종료 ===\n")
    
    context = {
        'plan': plan,
        'session': session,
        'words_json': json.dumps(words_data, cls=WordEncoder, ensure_ascii=False),
        'words': study_words,
    }
    
    return render(request, 'study/flashcard.html', context)

@login_required
def vocabulary_study(request, plan_id):
    """단어장 학습 뷰"""
    print("\n=== 단어장 학습 시작 디버깅 ===")
    plan = get_object_or_404(StudyPlan, id=plan_id, user=request.user)
    
    # 이미 학습한 단어 제외
    learned_words = StudyProgress.objects.filter(
        user=request.user,
        review_count__gt=0
    ).values_list('word_id', flat=True)
    
    # 학습할 단어 가져오기
    study_words = Word.objects.exclude(
        id__in=learned_words
    ).order_by('english')[:plan.target_words_per_day]
    
    # 학습 세션 생성
    session = StudySession.objects.create(
        user=request.user,
        study_plan=plan,
        study_type='word_list',
        start_time=timezone.now()
    )
    print(f"[DEBUG] 새 학습 세션 생성됨 (ID: {session.id})")
    print(f"[DEBUG] 시작 시간: {session.start_time}")
    print(f"[DEBUG] 학습할 단어 수: {study_words.count()}")
    print("=== 단어장 학습 시작 디버깅 종료 ===\n")
    
    return render(request, 'study/vocabulary.html', {
        'plan': plan,
        'words': study_words,
        'session': session
    })

@login_required
def review_study(request, plan_id):
    print("\n=== 복습 학습 디버깅 ===")
    plan = get_object_or_404(StudyPlan, id=plan_id, user=request.user)
    print(f"[DEBUG] 학습 계획 ID: {plan.id}")
    print(f"[DEBUG] 학습 계획 제목: {plan.title}")
    
    # 오답노트에서 마스터되지 않은 단어들 가져오기
    wrong_answer_notes = WrongAnswerNote.objects.filter(
        user=request.user,
        is_mastered=False
    ).select_related('word').order_by('-created_at')
    
    print(f"[DEBUG] 오답노트 단어 수: {wrong_answer_notes.count()}")
    if wrong_answer_notes:
        print("[DEBUG] 오답노트 단어들:")
        for note in wrong_answer_notes:
            print(f"  - {note.word.english} ({note.word.korean})")
    
    # 새로운 학습 세션 생성
    session = StudySession.objects.create(
        user=request.user,
        study_plan=plan,
        study_type='review'
    )
    print(f"[DEBUG] 새 학습 세션 생성됨 (ID: {session.id})")
    print("=== 복습 학습 디버깅 종료 ===\n")
    
    return render(request, 'study/review.html', {
        'plan': plan,
        'wrong_answer_notes': wrong_answer_notes,
        'session': session
    })

@login_required
def word_list_study(request):
    # 사용자의 모든 학습 단어를 가져옴
    progress = StudyProgress.objects.filter(
        user=request.user
    ).select_related('word')
    return render(request, 'study/word_list.html', {'progress': progress})

# 학습 진도 관련 뷰
@login_required
def study_progress(request):
    progress = StudyProgress.objects.filter(
        user=request.user
    ).select_related('word')
    return render(request, 'study/progress.html', {'progress': progress})

@login_required
def word_progress_update(request, word_id):
    """단어 학습 진도 업데이트"""
    if request.method == 'POST':
        print("\n=== 단어 학습 진도 업데이트 시작 ===")
        print(f"[DEBUG] 요청된 단어 ID: {word_id}")
        print(f"[DEBUG] POST 데이터: {request.POST}")
        
        word = get_object_or_404(Word, id=word_id)
        proficiency = int(request.POST.get('proficiency', '1'))
        print(f"[DEBUG] 단어 정보: {word.english} (ID: {word.id})")
        print(f"[DEBUG] 숙련도: {proficiency}")
        
        # 현재 시간을 한국 시간대로 가져옴
        current_time = timezone.now()
        print(f"[DEBUG] 현재 시간 (한국): {current_time}")
        
        # 현재 활성화된 학습 세션 가져오기
        study_session = StudySession.objects.filter(
            user=request.user,
            end_time__isnull=True
        ).order_by('-start_time').first()
        
        print(f"[DEBUG] 현재 학습 세션: {study_session.id if study_session else 'None'}")
        
        # StudyProgress 생성 또는 업데이트
        try:
            progress = StudyProgress.objects.get(user=request.user, word=word)
            old_review_count = progress.review_count
            if proficiency == 5:
                progress.proficiency = 5
            else:
                progress.proficiency = min(progress.proficiency + 1, 5)
            progress.review_count += 1
            progress.study_session = study_session
            progress.last_reviewed = current_time
            progress.save()
            print(f"[DEBUG] 기존 진도 업데이트: ID {progress.id}, 복습 횟수 {old_review_count} -> {progress.review_count}")
        except StudyProgress.DoesNotExist:
            progress = StudyProgress.objects.create(
                user=request.user,
                word=word,
                proficiency=proficiency,
                study_session=study_session,
                last_reviewed=current_time,
                review_count=1
            )
            print(f"[DEBUG] 새로운 진도 생성: ID {progress.id}, 복습 횟수 1")
        
        # 다음 복습 일정 설정
        next_review = current_time.date()
        if int(proficiency) < 3:
            next_review += timedelta(days=1)
        elif int(proficiency) == 3:
            next_review += timedelta(days=3)
        elif int(proficiency) == 4:
            next_review += timedelta(days=7)
        else:
            next_review += timedelta(days=14)
        
        progress.next_review_date = next_review
        progress.save()
        print(f"[DEBUG] 다음 복습 일정 설정: {next_review}")
        
        ReviewSchedule.objects.create(
            user=request.user,
            word=word,
            scheduled_date=next_review
        )
        print(f"[DEBUG] 복습 일정 생성됨: {next_review}")
        
        # 오늘의 학습 현황 확인 (한국 시간 기준)
        today = current_time.date()
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        
        # 한국 시간대로 변환
        today_start = timezone.localtime(today_start)
        today_end = timezone.localtime(today_end)
        
        today_progress = StudyProgress.objects.filter(
            user=request.user,
            last_reviewed__range=(today_start, today_end),
            review_count__gt=0
        ).count()
        print(f"[DEBUG] 오늘의 학습 현황: {today_progress}개")
        
        # 전체 학습 현황 확인
        total_studied = StudyProgress.objects.filter(
            user=request.user,
            review_count__gt=0
        ).count()
        print(f"[DEBUG] 전체 학습 현황: {total_studied}개")
        print("=== 단어 학습 진도 업데이트 완료 ===\n")
        
        messages.success(request, f"{word.english} 단어를 학습했습니다!")
        return redirect('study:daily_words')
    
    return redirect('study:daily_words')

@login_required
def bookmark_list(request):
    """북마크된 단어 목록을 보여주는 뷰"""
    bookmarks = StudyProgress.objects.filter(
        user=request.user,
        is_bookmarked=True
    ).select_related('word').order_by('-last_reviewed')
    
    # 페이지네이션
    paginator = Paginator(bookmarks, 20)  # 페이지당 20개
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_bookmarks': bookmarks.count(),
    }
    return render(request, 'study/bookmarks.html', context)

@login_required
def bookmark_toggle(request, word_id):
    if request.method == 'POST':
        word = get_object_or_404(Word, id=word_id)
        progress, created = StudyProgress.objects.get_or_create(
            user=request.user,
            word=word
        )
        progress.is_bookmarked = not progress.is_bookmarked
        progress.save()
        
        # AJAX 요청인 경우 JSON 응답
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'is_bookmarked': progress.is_bookmarked,
                'message': '북마크가 추가되었습니다.' if progress.is_bookmarked else '북마크가 제거되었습니다.'
            })
            
        # 일반 요청인 경우 메시지 추가 후 리다이렉트
        messages.success(
            request,
            '북마크가 추가되었습니다.' if progress.is_bookmarked else '북마크가 제거되었습니다.'
        )
        
        # 이전 페이지로 리다이렉트, 없으면 학습 진도 페이지로
        return redirect(request.META.get('HTTP_REFERER', 'study:progress'))
        
    # POST 요청이 아닌 경우 400 에러
    return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)

# 복습 일정 관련 뷰
@login_required
def review_schedule_list(request):
    schedules = ReviewSchedule.objects.filter(
        user=request.user,
        status='pending'
    ).select_related('word')
    return render(request, 'study/schedule_list.html', {'schedules': schedules})

@login_required
def review_schedule_update(request, schedule_id):
    if request.method == 'POST':
        schedule = get_object_or_404(ReviewSchedule, id=schedule_id, user=request.user)
        status = request.POST.get('status')
        schedule.status = status
        if status == 'completed':
            schedule.completed_at = timezone.now()
        schedule.save()
        messages.success(request, '복습 일정이 업데이트되었습니다.')
    return redirect('study:schedule_list')

@login_required
def notification_list(request):
    """알림 목록 뷰"""
    notifications = StudyNotification.objects.filter(user=request.user).order_by('-created_at')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # AJAX 요청인 경우 JSON 응답
        notifications_data = [{
            'id': n.id,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for n in notifications]
        return JsonResponse({'notifications': notifications_data})
    else:
        # 일반 요청인 경우 템플릿 렌더링
        return render(request, 'study/notifications.html', {
            'notifications': notifications
        })

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """알림을 읽음으로 표시하는 뷰"""
    try:
        notification = StudyNotification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    except StudyNotification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '알림을 찾을 수 없습니다.'}, status=404)

@login_required
@require_POST
def mark_all_notifications_read(request):
    """모든 알림을 읽음으로 표시하는 뷰"""
    StudyNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success'})

@login_required
@require_POST
def delete_notification(request, notification_id):
    """알림을 삭제하는 뷰"""
    try:
        notification = StudyNotification.objects.get(id=notification_id, user=request.user)
        notification.delete()
        return JsonResponse({'status': 'success'})
    except StudyNotification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '알림을 찾을 수 없습니다.'}, status=404)

@login_required
@require_POST
def delete_all_notifications(request):
    """모든 알림을 삭제하는 뷰"""
    StudyNotification.objects.filter(user=request.user).delete()
    return JsonResponse({'status': 'success'})

@login_required
def notification_settings(request):
    """알림 설정 관리"""
    settings = UserNotificationSettings.get_or_create_settings(request.user)
    
    if request.method == 'POST':
        settings.review_notifications = request.POST.get('review_notifications') == 'on'
        settings.achievement_notifications = request.POST.get('achievement_notifications') == 'on'
        settings.reminder_notifications = request.POST.get('reminder_notifications') == 'on'
        
        notification_time = request.POST.get('notification_time')
        if notification_time:
            settings.notification_time = parse_time(notification_time)
        
        settings.save()
        messages.success(request, '알림 설정이 업데이트되었습니다.')
        return redirect('study:notification_settings')
    
    return render(request, 'study/notification_settings.html', {
        'settings': settings
    })

@login_required
def review_start(request, word_id):
    """특정 단어의 복습을 시작합니다."""
    word = get_object_or_404(Word, id=word_id)
    
    # 복습 세션 생성
    session = StudySession.objects.create(
        user=request.user,
        study_type='review',
        start_time=timezone.now()
    )
    
    # 복습할 단어를 세션에 추가
    session.words.add(word)
    
    # AJAX 요청인 경우 JSON 응답
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'redirect_url': reverse('study:session_detail', args=[session.id])
        })
    
    # 일반 요청인 경우 세션 상세 페이지로 리다이렉트
    return redirect('study:session_detail', session_id=session.id)

def text_to_speech(request):
    """텍스트를 음성으로 변환하여 반환합니다."""
    text = request.GET.get('text', '')
    if not text:
        return HttpResponse(status=400)
    
    # 음성 파일 저장 경로
    audio_dir = os.path.join(settings.MEDIA_ROOT, 'audio')
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir)
    
    # 파일명 생성 (텍스트의 처음 10글자 사용)
    filename = f"{text[:10]}.mp3"
    filepath = os.path.join(audio_dir, filename)
    
    # 이미 파일이 존재하면 재사용
    if not os.path.exists(filepath):
        tts = gTTS(text=text, lang='en')
        tts.save(filepath)
    
    # 오디오 파일을 직접 반환
    with open(filepath, 'rb') as f:
        response = HttpResponse(f.read(), content_type='audio/mpeg')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

def word_detail(request, word_id):
    word = get_object_or_404(Word, id=word_id)
    
    # 단어와 예문의 음성 파일 경로 생성
    word_audio = text_to_speech(word.english)
    example_audio = text_to_speech(word.example, lang='en') if word.example else None
    
    context = {
        'word': word,
        'word_audio': word_audio,
        'example_audio': example_audio,
    }
    return render(request, 'study/word_detail.html', context)

@login_required
def study_stats_api(request, plan_id):
    """학습 통계 API"""
    plan = get_object_or_404(StudyPlan, id=plan_id, user=request.user)
    
    # 오늘 날짜 (한국시간)
    today = timezone.localtime().date()
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    
    # 한국 시간대로 변환
    today_start = timezone.localtime(today_start)
    today_end = timezone.localtime(today_end)
    
    # 오늘의 학습 시간 계산 (종료된 세션 + 현재 진행 중인 세션)
    completed_sessions_time = StudySession.objects.filter(
        user=request.user,
        start_time__range=(today_start, today_end),
        end_time__isnull=False
    ).aggregate(total=Sum('daily_study_minutes'))['total'] or 0
    
    # 현재 진행 중인 세션의 시간 계산
    active_session = StudySession.objects.filter(
        user=request.user,
        start_time__range=(today_start, today_end),
        end_time__isnull=True
    ).first()
    
    active_session_time = 0
    if active_session:
        elapsed_minutes = (timezone.now() - active_session.start_time).total_seconds() / 60
        active_session_time = round(elapsed_minutes, 2)
    
    daily_study_time = completed_sessions_time + active_session_time
    
    # 전체 학습 시간 계산
    total_study_time = StudySession.objects.filter(
        user=request.user,
        end_time__isnull=False
    ).aggregate(total=Sum('study_minutes'))['total'] or 0
    
    # 오늘 학습한 단어 수 계산
    today_progress = StudyProgress.objects.filter(
        user=request.user,
        last_reviewed__date=today,
        review_count__gt=0
    ).count()
    
    return JsonResponse({
        'status': 'success',
        'daily_study_time': round(daily_study_time, 2),
        'total_study_time': round(total_study_time, 2),
        'today_progress': today_progress
    })

@login_required
def level_test_start(request):
    """레벨 테스트 시작"""
    # 이미 진행 중인 테스트가 있는지 확인
    active_test = LevelTest.objects.filter(
        usertestresult__user=request.user,
        usertestresult__completed_at__isnull=True
    ).first()

    if active_test:
        messages.info(request, '이미 진행 중인 테스트가 있습니다.')
        return redirect('study:level_test_continue')

    # 각 난이도별로 20개씩 단어 선택
    easy_words = list(Word.objects.filter(difficulty='easy').order_by('?')[:20])
    medium_words = list(Word.objects.filter(difficulty='medium').order_by('?')[:20])
    hard_words = list(Word.objects.filter(difficulty='hard').order_by('?')[:20])

    # 테스트 생성
    test = LevelTest.objects.create(
        title=f"{request.user.username}의 레벨 테스트",
        description="사용자 레벨을 측정하기 위한 테스트입니다."
    )

    # 모든 단어를 합치고 섞기
    all_words = easy_words + medium_words + hard_words
    shuffle(all_words)

    # 각 단어에 대한 문제 생성
    for word in all_words:
        # 보기 생성 (현재 단어의 난이도에서 3개 추가 선택)
        options = list(Word.objects.filter(
            difficulty=word.difficulty
        ).exclude(
            id=word.id
        ).values_list('korean', flat=True).order_by('?')[:3])
        options.append(word.korean)
        shuffle(options)

        TestQuestion.objects.create(
            test=test,
            question_type='multiple_choice',
            word=word,
            question_text=f"다음 단어의 뜻으로 알맞은 것은? - {word.english}",
            correct_answer=word.korean,
            options=options,
            points=1
        )

    # 테스트 결과 초기 생성
    UserTestResult.objects.create(
        user=request.user,
        test=test,
        score=0,
        level=1,
        answers={}
    )

    return redirect('study:level_test_question', test_id=test.id, question_number=1)

@login_required
def level_test_question(request, test_id, question_number):
    """레벨 테스트 문제 풀기"""
    test = get_object_or_404(LevelTest, id=test_id)
    questions = test.questions.all()
    
    if question_number > questions.count():
        return redirect('study:level_test_complete', test_id=test_id)

    question = questions[question_number - 1]
    
    if request.method == 'POST':
        answer = request.POST.get('answer')
        
        # 답변 저장
        test_result = UserTestResult.objects.get(user=request.user, test=test)
        answers = test_result.answers
        answers[str(question_number)] = {
            'word_id': question.word.id,
            'answer': answer,
            'correct': answer == question.correct_answer,
            'difficulty': question.word.difficulty
        }
        test_result.answers = answers
        test_result.save()

        return redirect('study:level_test_question', test_id=test_id, question_number=question_number + 1)

    # 진행률 계산
    progress = (question_number / questions.count()) * 100

    return render(request, 'study/level_test_question.html', {
        'test': test,
        'question': question,
        'question_number': question_number,
        'total_questions': questions.count(),
        'options': question.options,
        'progress': progress
    })

@login_required
def level_test_complete(request, test_id):
    """레벨 테스트 완료 및 결과 계산"""
    test = get_object_or_404(LevelTest, id=test_id)
    result = get_object_or_404(UserTestResult, user=request.user, test=test)

    # 난이도별 정답률 계산
    difficulty_scores = {
        'easy': {'correct': 0, 'total': 0},
        'medium': {'correct': 0, 'total': 0},
        'hard': {'correct': 0, 'total': 0}
    }

    for answer in result.answers.values():
        difficulty = answer['difficulty']
        difficulty_scores[difficulty]['total'] += 1
        if answer['correct']:
            difficulty_scores[difficulty]['correct'] += 1

    # 각 난이도의 정답률 계산
    accuracy_rates = {}
    for difficulty, scores in difficulty_scores.items():
        if scores['total'] > 0:
            accuracy_rates[difficulty] = (scores['correct'] / scores['total']) * 100
        else:
            accuracy_rates[difficulty] = 0

    # 레벨 결정
    if accuracy_rates['hard'] >= 70:
        level = 5  # 고급
        difficulty = 'hard'
    elif accuracy_rates['hard'] >= 50:
        level = 4  # 중상급
        difficulty = 'hard'
    elif accuracy_rates['medium'] >= 70:
        level = 3  # 중급
        difficulty = 'medium'
    elif accuracy_rates['medium'] >= 50:
        level = 2  # 초급
        difficulty = 'easy'
    else:
        level = 1  # 기초
        difficulty = 'easy'

    # 총점 계산
    total_correct = sum(scores['correct'] for scores in difficulty_scores.values())
    total_questions = sum(scores['total'] for scores in difficulty_scores.values())
    score = int((total_correct / total_questions) * 100)

    # 결과 저장
    result.score = score
    result.level = level
    result.save()

    # 사용자 레벨 업데이트
    UserLevel.objects.update_or_create(
        user=request.user,
        defaults={
            'current_level': level,
            'recommended_words_per_day': 20
        }
    )

    # 레벨 테스트 완료 표시
    request.user.level_test_completed = True
    request.user.save()

    # 레벨별 설명과 학습 계획 설명 생성
    level_descriptions = {
        1: '기초 단계입니다. 기본적인 TOEIC 단어를 학습합니다.',
        2: '초급 단계입니다. 초급 TOEIC 단어를 학습합니다.',
        3: '중급 단계입니다. 중급 TOEIC 단어를 학습합니다.',
        4: '중상급 단계입니다. 중상급 TOEIC 단어를 학습합니다.',
        5: '고급 단계입니다. 고급 TOEIC 단어를 학습합니다.'
    }

    study_plan_descriptions = {
        1: '하루 20개의 기초 단어를 5분 동안 학습합니다.',
        2: '하루 20개의 초급 단어를 5분 동안 학습합니다.',
        3: '하루 20개의 중급 단어를 5분 동안 학습합니다.',
        4: '하루 20개의 중상급 단어를 5분 동안 학습합니다.',
        5: '하루 20개의 고급 단어를 5분 동안 학습합니다.'
    }

    # 기존 학습 계획이 있다면 비활성화
    StudyPlan.objects.filter(user=request.user).update(is_active=False)
    
    # 새로운 학습 계획 생성
    study_plan = StudyPlan.objects.create(
        user=request.user,
        title=f'Level {level} 학습 계획',
        description=study_plan_descriptions[level],
        target_words_per_day=request.user.profile.daily_goal,
        target_study_time=5,  # 5분으로 설정
        difficulty=difficulty,
        is_active=True
    )

    # 난이도별 정답률 정보를 포함한 학습 추천 목록 생성
    recommendations = [
        {
            'title': '난이도별 정답률',
            'description': f'초급: {accuracy_rates["easy"]:.1f}%, 중급: {accuracy_rates["medium"]:.1f}%, 고급: {accuracy_rates["hard"]:.1f}%'
        },
        {
            'title': '추천 학습 난이도',
            'description': f'현재 {difficulty} 난이도의 단어를 학습하는 것이 적합합니다.'
        },
        {
            'title': '학습 계획',
            'description': f'하루 {study_plan.target_words_per_day}개의 단어를 {study_plan.target_study_time}분 동안 학습합니다.'
        }
    ]

    messages.success(request, '레벨 테스트가 완료되었습니다!')
    messages.info(request, f'레벨에 맞는 학습 계획이 자동으로 생성되었습니다. 학습 계획 페이지에서 확인해보세요!')

    return render(request, 'study/level_test_result.html', {
        'result': result,
        'accuracy_rates': accuracy_rates,
        'total_correct': total_correct,
        'total_questions': total_questions,
        'level_description': level_descriptions[level],
        'study_plan_description': study_plan_descriptions[level],
        'recommendations': recommendations
    })

@login_required
def plan_activate(request, plan_id):
    plan = get_object_or_404(StudyPlan, id=plan_id, user=request.user)
    
    # 다른 활성화된 계획 비활성화
    StudyPlan.objects.filter(user=request.user, is_active=True).update(is_active=False)
    
    # 선택한 계획 활성화
    plan.is_active = True
    plan.save()
    
    messages.success(request, '학습 계획이 활성화되었습니다.')
    return redirect('study:home')

@login_required
def plan_deactivate(request, plan_id):
    plan = get_object_or_404(StudyPlan, id=plan_id, user=request.user)
    
    if plan.is_active:
        plan.is_active = False
        plan.save()
        messages.success(request, '학습 계획이 비활성화되었습니다.')
    
    return redirect('study:home')

@login_required
def study_complete(request, word_id):
    """단어 학습 완료 처리"""
    word = get_object_or_404(Word, id=word_id)
    progress = StudyProgress.objects.get_or_create(
        user=request.user,
        word=word
    )[0]
    
    # 학습 완료 처리
    progress.review_count += 1
    progress.last_reviewed = timezone.now()
    progress.save()
    
    # 포인트 지급
    request.user.profile.add_points(5, "단어 학습 완료")
    
    # 연속 학습일 체크
    check_streak(request.user)
    
    return JsonResponse({'status': 'success'})

@login_required
def friend_list(request):
    """친구 목록 페이지"""
    # 친구 목록 가져오기 (양쪽 모두 확인)
    friendships = Friendship.objects.filter(
        models.Q(user1=request.user) | models.Q(user2=request.user)
    ).select_related('user1', 'user2')
    
    # 친구 목록을 (친구, 관계) 튜플의 리스트로 변환
    friends_list = []
    for friendship in friendships:
        # 현재 사용자가 user1인 경우 user2가 친구
        if friendship.user1 == request.user:
            friend = friendship.user2
        # 현재 사용자가 user2인 경우 user1이 친구
        else:
            friend = friendship.user1
        friends_list.append((friend, friendship))
    
    # 받은 친구 요청 가져오기
    received_requests = FriendRequest.objects.filter(
        to_user=request.user,
        is_accepted=False,
        is_rejected=False
    ).select_related('from_user')
    
    # 보낸 친구 요청 가져오기
    sent_requests = FriendRequest.objects.filter(
        from_user=request.user,
        is_accepted=False,
        is_rejected=False
    ).select_related('to_user')
    
    context = {
        'friends_list': friends_list,
        'received_requests': received_requests,
        'sent_requests': sent_requests,
    }
    return render(request, 'study/friends.html', context)

@login_required
@require_POST
def friend_search(request):
    nickname = request.POST.get('nickname', '').strip()
    if not nickname:
        return JsonResponse({'found': False, 'message': '닉네임을 입력하세요.'})
    try:
        # User 모델과 UserProfile 모델 모두에서 검색
        user = User.objects.filter(
            models.Q(nickname=nickname) | 
            models.Q(profile__nickname=nickname)
        ).first()
        
        if user:
            return JsonResponse({
                'found': True,
                'user_id': user.id,
                'nickname': user.nickname or user.profile.nickname,
                'level': getattr(user.profile, 'level', None),
                'exp': getattr(user.profile, 'points', None),
            })
        else:
            return JsonResponse({'found': False, 'message': '해당 닉네임의 사용자가 없습니다.'})
    except Exception as e:
        return JsonResponse({'found': False, 'message': '검색 중 오류가 발생했습니다.'})

@login_required
@require_POST
def send_friend_request(request, user_id):
    """친구 요청 보내기"""
    try:
        to_user = User.objects.get(id=user_id)
        
        # 자기 자신에게 요청할 수 없음
        if to_user == request.user:
            return JsonResponse({'success': False, 'message': '자기 자신에게 친구 요청을 보낼 수 없습니다.'})
        
        # 이미 친구인지 확인
        if Friendship.objects.filter(
            models.Q(user1=request.user, user2=to_user) | 
            models.Q(user1=to_user, user2=request.user)
        ).exists():
            return JsonResponse({'success': False, 'message': '이미 친구입니다.'})
        
        # 이미 요청을 보냈는지 확인
        if FriendRequest.objects.filter(
            from_user=request.user,
            to_user=to_user,
            is_accepted=False,
            is_rejected=False
        ).exists():
            return JsonResponse({'success': False, 'message': '이미 친구 요청을 보냈습니다.'})
        
        # 새로운 친구 요청 생성
        FriendRequest.objects.create(
            from_user=request.user,
            to_user=to_user
        )
        
        return JsonResponse({'success': True, 'message': '친구 신청을 보냈습니다.'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': '대상 사용자가 존재하지 않습니다.'})

@login_required
@require_POST
def accept_friend_request(request, request_id):
    """친구 요청 수락"""
    try:
        friend_request = FriendRequest.objects.get(
            id=request_id,
            to_user=request.user,
            is_accepted=False,
            is_rejected=False
        )
        
        # 친구 요청 수락 처리
        friend_request.is_accepted = True
        friend_request.save()
        
        # 친구 관계 생성 (양쪽 모두에게 표시되도록)
        Friendship.objects.create(
            user1=friend_request.from_user,
            user2=friend_request.to_user
        )
        
        # 상대방의 친구 요청도 수락 처리
        reverse_request = FriendRequest.objects.filter(
            from_user=request.user,
            to_user=friend_request.from_user,
            is_accepted=False,
            is_rejected=False
        ).first()
        
        if reverse_request:
            reverse_request.is_accepted = True
            reverse_request.save()
        
        return JsonResponse({'success': True, 'message': '친구 요청을 수락했습니다.'})
    except FriendRequest.DoesNotExist:
        return JsonResponse({'success': False, 'message': '친구 요청을 찾을 수 없습니다.'})

@login_required
@require_POST
def reject_friend_request(request, request_id):
    """친구 요청 거절"""
    try:
        friend_request = FriendRequest.objects.get(
            id=request_id,
            to_user=request.user,
            is_accepted=False,
            is_rejected=False
        )
        
        friend_request.is_rejected = True
        friend_request.save()
        
        return JsonResponse({'success': True, 'message': '친구 요청을 거절했습니다.'})
    except FriendRequest.DoesNotExist:
        return JsonResponse({'success': False, 'message': '친구 요청을 찾을 수 없습니다.'})

@login_required
@require_POST
def delete_friendship(request, friendship_id):
    """친구 관계 삭제"""
    try:
        friendship = Friendship.objects.filter(
            id=friendship_id
        ).filter(
            models.Q(user1=request.user) | models.Q(user2=request.user)
        ).first()
        
        if friendship:
            friendship.delete()
            return JsonResponse({'success': True, 'message': '친구 관계가 삭제되었습니다.'})
        else:
            return JsonResponse({'success': False, 'message': '친구 관계를 찾을 수 없습니다.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': '친구 관계 삭제 중 오류가 발생했습니다.'})

@login_required
def friend_wordbook(request, friend_id):
    """친구의 단어장 페이지"""
    try:
        # 친구 정보 가져오기
        friend = get_object_or_404(CustomUser, id=friend_id)
        
        # 친구 관계 확인
        friendship = Friendship.objects.filter(
            Q(user1=request.user, user2=friend) | Q(user1=friend, user2=request.user)
        ).first()
        
        if not friendship:
            messages.error(request, '친구 관계가 아닙니다.')
            return redirect('study:friend_list')
        
        # 친구의 개인 단어장 단어 가져오기
        words = PersonalWordList.objects.filter(user=friend).select_related('word').order_by('-created_at')
        
        context = {
            'friend': friend,
            'words': words,
            'friendship': friendship
        }
        return render(request, 'study/friend_wordbook.html', context)
        
    except Exception as e:
        messages.error(request, f'단어장을 불러오는 중 오류가 발생했습니다: {str(e)}')
        return redirect('study:friend_list')

@login_required
def daily_mission(request):
    """데일리 미션 뷰"""
    today = timezone.now().date()
    
    # 오늘의 데일리 미션 가져오기
    daily_mission = DailyMission.objects.filter(
        user=request.user,
        date=today
    ).first()
    
    if not daily_mission:
        # 북마크된 단어가 있는지 확인
        bookmarked_words = Word.objects.filter(
            bookmarks__user=request.user
        ).distinct()
        
        if bookmarked_words.count() < 5:
            messages.warning(request, '북마크된 단어가 5개 미만입니다. 더 많은 단어를 북마크해주세요.')
            return redirect('accounts:home')
        
        # 새로운 데일리 미션 생성
        daily_mission = DailyMission.objects.create(
            user=request.user,
            date=today,
            is_completed=False
        )
        
        # 북마크된 단어들 중에서 무작위로 5개 선택
        mission_words = bookmarked_words.order_by('?')[:5]
        daily_mission.words.add(*mission_words)
    
    # 데일리 미션의 단어들 가져오기
    mission_words = daily_mission.words.all()
    
    # 각 단어에 대한 보기 생성
    word_choices = []
    for word in mission_words:
        # 해당 단어를 제외한 다른 단어들 중에서 3개를 무작위로 선택
        other_words = Word.objects.exclude(id=word.id).order_by('?')[:3]
        choices = list(other_words) + [word]
        random.shuffle(choices)
        word_choices.append({
            'word': word,
            'choices': choices
        })
    
    context = {
        'daily_mission': daily_mission,
        'mission_words': mission_words,
        'word_choices': word_choices,
    }
    
    return render(request, 'study/daily_mission.html', context)

@login_required
def submit_daily_mission(request):
    """데일리 미션 제출 처리"""
    print("\n=== 데일리 미션 제출 시작 ===")
    print(f"[DEBUG] 요청 메소드: {request.method}")
    
    if request.method == 'POST':
        try:
            # 오늘 날짜의 데일리 미션 가져오기
            today = timezone.localtime().date()
            daily_mission = DailyMission.objects.get(
                user=request.user,
                date=today
            )
            print(f"[DEBUG] 데일리 미션 ID: {daily_mission.id}")
            
            # 이미 완료된 미션인지 확인
            if daily_mission.is_completed:
                print("[DEBUG] 이미 완료된 미션입니다.")
                return JsonResponse({
                    'status': 'error',
                    'message': '이미 완료한 미션입니다.'
                })
            
            # 답안 처리
            correct_count = 0
            total_questions = daily_mission.words.count()
            results = []
            
            for word in daily_mission.words.all():
                answer_key = f'word_{word.id}'
                if answer_key not in request.POST:
                    print(f"[DEBUG] 답안 누락: {answer_key}")
                    return JsonResponse({
                        'status': 'error',
                        'message': '모든 문제에 답해주세요.'
                    })
                
                selected_answer_id = int(request.POST[answer_key])
                is_correct = selected_answer_id == word.id
                if is_correct:
                    correct_count += 1
                
                results.append({
                    'word': word.english,
                    'correct_answer': word.korean,
                    'selected_answer': Word.objects.get(id=selected_answer_id).korean,
                    'is_correct': is_correct
                })
                print(f"[DEBUG] 문제 {word.english}: {'정답' if is_correct else '오답'}")
            
            # 점수 계산 (100점 만점)
            score = int((correct_count / total_questions) * 100)
            print(f"[DEBUG] 총 정답 수: {correct_count}/{total_questions}")
            print(f"[DEBUG] 최종 점수: {score}")
            
            # 포인트 계산 (한 문제당 5포인트)
            points_earned = correct_count * 5
            print(f"[DEBUG] 획득 포인트: {points_earned}")
            
            # 사용자 프로필에 포인트 추가
            user_profile = request.user.profile
            user_profile.points += points_earned
            user_profile.save()
            print(f"[DEBUG] 총 포인트: {user_profile.points}")
            
            # 데일리 미션 완료 처리
            daily_mission.is_completed = True
            daily_mission.score = score
            daily_mission.completed_at = timezone.now()
            daily_mission.save()
            print("[DEBUG] 데일리 미션 완료 처리 완료")
            
            # 결과를 세션에 저장
            request.session['daily_mission_results'] = results
            request.session['points_earned'] = points_earned  # 획득한 포인트도 세션에 저장
            print("[DEBUG] 결과 세션 저장 완료")
            
            # 결과 페이지로 리다이렉트
            return JsonResponse({
                'status': 'success',
                'redirect_url': reverse('study:daily_mission_result')
            })
            
        except DailyMission.DoesNotExist:
            print("[DEBUG] 오늘의 데일리 미션을 찾을 수 없습니다.")
            return JsonResponse({
                'status': 'error',
                'message': '오늘의 데일리 미션을 찾을 수 없습니다.'
            })
        except Exception as e:
            print(f"[DEBUG] 오류 발생: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': '제출 중 오류가 발생했습니다.'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': '잘못된 요청입니다.'
    })

@login_required
def daily_mission_result(request):
    """데일리 미션 결과 페이지"""
    print("\n=== 데일리 미션 결과 페이지 시작 ===")
    
    try:
        daily_mission = get_object_or_404(
            DailyMission,
            user=request.user,
            date=timezone.localtime().date(),
            is_completed=True
        )
        print(f"[DEBUG] 데일리 미션 ID: {daily_mission.id}")
        print(f"[DEBUG] 점수: {daily_mission.score}")
        
        # 세션에서 결과 가져오기
        results = request.session.get('daily_mission_results', [])
        points_earned = request.session.get('points_earned', 0)
        print(f"[DEBUG] 세션에서 가져온 결과 수: {len(results)}")
        print(f"[DEBUG] 획득 포인트: {points_earned}")
        
        context = {
            'daily_mission': daily_mission,
            'total_questions': daily_mission.words.count(),
            'correct_count': int(daily_mission.score * daily_mission.words.count() / 100),
            'results': results,
            'points_earned': points_earned
        }
        
        # 세션에서 결과 삭제
        if 'daily_mission_results' in request.session:
            del request.session['daily_mission_results']
        if 'points_earned' in request.session:
            del request.session['points_earned']
        print("[DEBUG] 세션에서 결과 삭제 완료")
        
        print("=== 데일리 미션 결과 페이지 완료 ===\n")
        return render(request, 'study/daily_mission_result.html', context)
        
    except Exception as e:
        print(f"[ERROR] 오류 발생: {str(e)}")
        messages.error(request, '결과를 불러오는 중 오류가 발생했습니다.')
        return redirect('accounts:home')

@login_required
def daily_mission_modal_shown(request):
    """데일리 미션 모달이 표시되었음을 저장하는 뷰"""
    if request.method == 'POST':
        today = timezone.now().date()
        DailyMissionModalShown.objects.update_or_create(
            user=request.user,
            date=today,
            defaults={'shown': True}
        )
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def save_study_time(request):
    try:
        session_id = request.POST.get('session_id')
        study_time = float(request.POST.get('study_time', 0))
        
        print(f"\n=== save_study_time 디버깅 ===")
        print(f"세션 ID: {session_id}")
        print(f"학습 시간(초): {study_time}")
        
        session = StudySession.objects.get(id=session_id, user=request.user)
        
        # 초를 분으로 변환하고 소수점 둘째 자리까지 반올림
        minutes = round(study_time / 60, 2)
        
        # study_minutes와 daily_study_minutes 모두 업데이트
        session.study_minutes = minutes
        session.daily_study_minutes = minutes
        session.save()
        
        print(f"저장된 학습 시간(분): {minutes}")
        print(f"study_minutes: {session.study_minutes}")
        print(f"daily_study_minutes: {session.daily_study_minutes}")
        
        # 총 학습 시간 계산
        total_study_time = StudySession.objects.filter(
            user=request.user,
            end_time__isnull=False
        ).aggregate(total=Sum('study_minutes'))['total'] or 0
        
        print(f"총 누적 학습 시간: {total_study_time}분")
        print("=== save_study_time 디버깅 완료 ===\n")
        
        return JsonResponse({
            'status': 'success',
            'total_study_time': round(total_study_time, 2)
        })
    except StudySession.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '세션을 찾을 수 없습니다.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def reset_today_sessions(request):
    """오늘의 학습 세션을 초기화하는 함수"""
    today = timezone.localtime().date()
    
    # 오늘의 세션 중 종료되지 않은 세션들을 찾아서 종료 처리
    today_sessions = StudySession.objects.filter(
        user=request.user,
        start_time__date=today,
        end_time__isnull=True
    )
    
    for session in today_sessions:
        end_time = timezone.now()
        elapsed_minutes = (end_time - session.start_time).total_seconds() / 60
        
        # study_minutes와 daily_study_minutes 모두 업데이트
        session.study_minutes = round(elapsed_minutes, 2)
        session.daily_study_minutes = round(elapsed_minutes, 2)
        session.end_time = end_time
        session.save()
    
    messages.success(request, f'오늘의 {today_sessions.count()}개의 학습 세션이 초기화되었습니다.')
    return redirect('study:home')
