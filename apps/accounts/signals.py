from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import Attendance
import logging

logger = logging.getLogger(__name__)

@receiver(user_logged_in)
def check_attendance(sender, request, user, **kwargs):
    logger.debug("====== 출석 체크 시작 ======")
    logger.debug(f"사용자: {user.username}")
    
    today = timezone.now().date()
    logger.debug(f"오늘 날짜: {today}")
    
    # 오늘 첫 로그인인 경우에만 출석 체크
    attendance, created = Attendance.objects.get_or_create(
        user=user,
        check_date=today
    )
    
    logger.debug(f"출석 기록 생성 여부: {created}")
    
    if created:
        logger.debug("새로운 출석 기록 생성됨")
        # 어제 날짜의 출석 기록 확인
        yesterday = today - timezone.timedelta(days=1)
        try:
            yesterday_attendance = Attendance.objects.get(
                user=user,
                check_date=yesterday
            )
            attendance.streak_days = yesterday_attendance.streak_days + 1
            logger.debug(f"어제 출석 기록 있음. 연속 출석 {yesterday_attendance.streak_days} -> {attendance.streak_days}")
        except Attendance.DoesNotExist:
            attendance.streak_days = 1
            logger.debug("어제 출석 기록 없음. 연속 출석 1일로 시작")
        
        attendance.save()
        logger.debug(f"최종 연속 출석일: {attendance.streak_days}")
        
        # 출석 메시지 설정
        if attendance.streak_days >= 3:
            message = f'🔥 {attendance.streak_days}일 연속 출석 성공! 대단해요!'
        else:
            message = '오늘의 출석이 완료되었습니다! ✨'
            
        logger.debug(f"출석 메시지: {message}")
        messages.success(request, message)
    else:
        logger.debug("이미 오늘 출석한 기록이 있음")
    
    logger.debug(f"현재 연속 출석일: {attendance.streak_days}")
    logger.debug("====== 출석 체크 종료 ======") 