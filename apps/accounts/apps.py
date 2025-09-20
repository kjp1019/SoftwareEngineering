from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = '계정 관리'

    def ready(self):
        import apps.accounts.signals  # 전체 경로로 수정
