from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class LevelTestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # 로그인하지 않은 사용자는 체크하지 않음
        if not request.user.is_authenticated:
            return None

        # 관리자는 체크하지 않음
        if request.user.is_staff or request.user.is_superuser:
            return None

        # 이미 레벨 테스트를 완료한 사용자는 체크하지 않음
        if request.user.level_test_completed:
            return None

        # 레벨 테스트 관련 URL은 허용
        if request.path.startswith('/study/level-test/'):
            return None

        # 로그아웃은 허용
        if request.path == reverse('accounts:logout'):
            return None

        # 레벨 테스트가 필요한 경우 리다이렉트
        messages.info(request, '학습을 시작하기 전에 레벨 테스트를 완료해주세요.')
        return redirect('study:level_test_start') 