from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.study.utils import check_and_create_reminder_notification

class Command(BaseCommand):
    help = '학습하지 않은 사용자들에게 독려 알림을 보냅니다'

    def handle(self, *args, **options):
        User = get_user_model()
        users = User.objects.all()
        
        for user in users:
            check_and_create_reminder_notification(user)
        
        self.stdout.write(self.style.SUCCESS('학습 독려 알림 체크가 완료되었습니다.')) 