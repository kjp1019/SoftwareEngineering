from django.utils import timezone
from datetime import timedelta
from .models import StudyProgress, StudySession, ReviewSchedule, Notification, UserNotificationSettings

def check_and_create_review_notification(user):
    """복습 알림 체크 및 생성"""
    today = timezone.now().date()
    review_count = ReviewSchedule.objects.filter(
        user=user,
        scheduled_date=today,
        status='pending'
    ).count()

    if review_count > 0:
        # 아직 읽지 않은 오늘의 복습 알림이 있는지 확인
        existing_notification = Notification.objects.filter(
            user=user,
            type='review',
            created_at__date=today,
            is_read=False
        ).exists()

        if not existing_notification:
            Notification.create_review_notification(user, review_count)

def check_and_create_achievement_notifications(user):
    """목표 달성 알림 체크 및 생성"""
    # 학습한 총 단어 수 체크
    total_words = StudyProgress.objects.filter(user=user).count()
    achievement_thresholds = {
        100: '100개 단어 학습',
        500: '500개 단어 학습',
        1000: '1000개 단어 학습',
    }

    for threshold, achievement in achievement_thresholds.items():
        if total_words >= threshold:
            # 해당 목표에 대한 알림이 이미 있는지 확인
            existing_notification = Notification.objects.filter(
                user=user,
                type='achievement',
                message__contains=achievement
            ).exists()

            if not existing_notification:
                Notification.create_achievement_notification(user, achievement)

    # 연속 학습일수 체크
    consecutive_days = get_consecutive_study_days(user)
    if consecutive_days in [7, 30, 100]:
        achievement = f'{consecutive_days}일 연속 학습'
        existing_notification = Notification.objects.filter(
            user=user,
            type='achievement',
            message__contains=achievement
        ).exists()

        if not existing_notification:
            Notification.create_achievement_notification(user, achievement)

def check_and_create_reminder_notification(user):
    """학습 독려 알림 체크 및 생성"""
    last_session = StudySession.objects.filter(
        user=user,
        end_time__isnull=False
    ).order_by('-end_time').first()

    if last_session:
        days_since_last_study = (timezone.now().date() - last_session.end_time.date()).days
        reminder_days = [3, 7, 14]  # 3일, 7일, 14일 동안 학습하지 않았을 때

        if days_since_last_study in reminder_days:
            # 같은 날짜에 대한 알림이 이미 있는지 확인
            existing_notification = Notification.objects.filter(
                user=user,
                type='reminder',
                created_at__date=timezone.now().date()
            ).exists()

            if not existing_notification:
                Notification.create_reminder_notification(user, days_since_last_study)

def get_consecutive_study_days(user):
    """연속 학습일수 계산"""
    today = timezone.now().date()
    consecutive_days = 0
    current_date = today

    while True:
        has_study = StudySession.objects.filter(
            user=user,
            start_time__date=current_date,
            end_time__isnull=False
        ).exists()

        if not has_study:
            break

        consecutive_days += 1
        current_date -= timedelta(days=1)

    return consecutive_days

def create_notification(user, notification_type, message):
    """알림을 생성하는 기본 함수"""
    # 사용자의 알림 설정 확인
    settings = UserNotificationSettings.get_or_create_settings(user)
    
    # 알림 설정에 따라 알림 생성 여부 결정
    if notification_type == 'goal' and not settings.achievement_notifications:
        return None
    elif notification_type == 'streak' and not settings.achievement_notifications:
        return None
    elif notification_type == 'mastery' and not settings.achievement_notifications:
        return None
    elif notification_type == 'level' and not settings.achievement_notifications:
        return None
    
    # 알림 생성
    return Notification.objects.create(
        user=user,
        notification_type=notification_type,
        message=message
    )

def create_goal_notification(user, goal_type, count):
    """학습 목표 달성 알림 생성"""
    if goal_type == 'words':
        message = f'축하합니다! 오늘의 단어 학습 목표 {count}개를 달성했습니다! 🎉'
    else:  # time
        message = f'축하합니다! 오늘의 학습 시간 목표 {count}분을 달성했습니다! ⏰'
    return create_notification(user, 'goal', message)

def create_streak_notification(user, days):
    """연속 학습 알림 생성"""
    message = f'대단합니다! {days}일 연속으로 학습을 완료했습니다! 🔥'
    return create_notification(user, 'streak', message)

def create_mastery_notification(user, word):
    """단어 완벽 암기 알림 생성"""
    message = f'축하합니다! "{word.english}" 단어를 완벽하게 암기했습니다! 🌟'
    return create_notification(user, 'mastery', message)

def create_level_notification(user, level):
    """레벨 달성 알림 생성"""
    message = f'축하합니다! 레벨 {level}을 달성했습니다! 🏆'
    return create_notification(user, 'level', message) 