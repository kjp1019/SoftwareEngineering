from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class CustomUser(AbstractUser):
    """사용자 모델"""
    email = models.EmailField('이메일 주소', unique=True)
    nickname = models.CharField(max_length=50, blank=True)
    is_student = models.BooleanField(default=False)
    is_teacher = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    last_login_attempt = models.DateTimeField(null=True, blank=True)
    lockout_until = models.DateTimeField(null=True, blank=True)
    login_attempts = models.IntegerField(default=0)
    level_test_completed = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']
    
    def __str__(self):
        return self.email

    class Meta:
        verbose_name = '사용자'
        verbose_name_plural = '사용자'

class UserProfile(models.Model):
    """사용자 프로필 모델"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    nickname = models.CharField(max_length=50, blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True, null=True)
    points = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    daily_goal = models.IntegerField(default=15)
    dark_mode = models.BooleanField(default=False)
    experience = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    points_to_next_level = models.IntegerField(default=100)

    def add_points(self, amount, reason):
        """포인트 추가 및 레벨 업 체크"""
        self.points += amount
        self.experience = min(100, self.experience + amount)
        self.check_level_up()
        self.save()
        
        # 포인트 내역 기록
        PointHistory.objects.create(
            user=self.user,
            amount=amount,
            reason=reason
        )

    def check_level_up(self):
        """포인트에 따른 레벨 업 체크"""
        required_points = self.get_required_points()
        while self.points >= required_points:
            self.level += 1
            required_points = self.get_required_points()

    def get_required_points(self):
        """다음 레벨까지 필요한 포인트 계산"""
        return self.level * 1000  # 레벨당 1000포인트 필요

    @property
    def points_to_next_level(self):
        """다음 레벨까지 필요한 포인트"""
        return self.get_required_points()

    def __str__(self):
        return f"{self.user.username}'s profile"

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """새로운 사용자가 생성되면 프로필도 자동으로 생성"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    """사용자가 수정되면 프로필도 저장"""
    instance.profile.save()

class Attendance(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='attendances')
    check_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    streak_days = models.IntegerField(default=1)

    class Meta:
        unique_together = ['user', 'check_date']
        ordering = ['-check_date']

    def __str__(self):
        return f"{self.user.username} - {self.check_date}"

    def save(self, *args, **kwargs):
        logger.debug("====== 출석 기록 저장 시작 ======")
        logger.debug(f"사용자: {self.user.username}, 날짜: {self.check_date}")
        
        if not self.pk:  # 새로운 출석 기록인 경우
            logger.debug("새로운 출석 기록 생성")
            # 어제 날짜의 출석 기록 확인
            yesterday = self.check_date - timezone.timedelta(days=1)
            try:
                yesterday_attendance = Attendance.objects.get(
                    user=self.user,
                    check_date=yesterday
                )
                self.streak_days = yesterday_attendance.streak_days + 1
                logger.debug(f"어제 출석 있음. 연속 출석 {yesterday_attendance.streak_days} -> {self.streak_days}")
            except Attendance.DoesNotExist:
                self.streak_days = 1
                logger.debug("어제 출석 없음. 연속 출석 1일로 시작")
        else:
            logger.debug(f"기존 출석 기록 업데이트. 현재 연속 출석: {self.streak_days}")
        
        logger.debug("====== 출석 기록 저장 종료 ======")
        super().save(*args, **kwargs)

class PointHistory(models.Model):
    """포인트 획득/차감 기록"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='point_histories')
    amount = models.IntegerField('포인트')
    reason = models.CharField('사유', max_length=100)
    created_at = models.DateTimeField('획득일시', auto_now_add=True)

    class Meta:
        verbose_name = '포인트 기록'
        verbose_name_plural = '포인트 기록 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}의 포인트 기록 - {self.amount}점 ({self.reason})"
