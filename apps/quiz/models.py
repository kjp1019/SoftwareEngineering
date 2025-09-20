from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from apps.vocabulary.models import Word

class Quiz(models.Model):
    """퀴즈 모델"""
    QUIZ_TYPES = [
        ('en_to_ko', '영한 퀴즈'),
        ('ko_to_en', '한영 퀴즈'),
        ('multiple', '객관식'),
        ('typing', '단어 입력'),
    ]

    title = models.CharField('퀴즈 제목', max_length=200)
    description = models.TextField('설명', blank=True)
    quiz_type = models.CharField('퀴즈 유형', max_length=20, choices=QUIZ_TYPES)
    difficulty = models.CharField('난이도', max_length=10, choices=Word.DIFFICULTY_CHOICES)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_quizzes')
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    is_public = models.BooleanField('공개 여부', default=True)
    time_limit = models.IntegerField('제한 시간(분)', default=0)  # 0은 제한 없음

    class Meta:
        verbose_name = '퀴즈'
        verbose_name_plural = '퀴즈 목록'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class QuizQuestion(models.Model):
    """퀴즈 문제 모델"""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    word = models.ForeignKey(Word, on_delete=models.CASCADE, related_name='quiz_questions')
    order = models.IntegerField('문제 순서', default=0)
    
    # 객관식 문제용 필드
    option1 = models.CharField('보기 1', max_length=200, blank=True)
    option2 = models.CharField('보기 2', max_length=200, blank=True)
    option3 = models.CharField('보기 3', max_length=200, blank=True)
    option4 = models.CharField('보기 4', max_length=200, blank=True)
    correct_option = models.IntegerField('정답 번호', default=1)
    
    # 사용자 답안과 정답 여부
    user_answer = models.CharField('사용자 답안', max_length=200, blank=True, null=True)
    is_correct = models.BooleanField('정답 여부', default=False)

    class Meta:
        verbose_name = '퀴즈 문제'
        verbose_name_plural = '퀴즈 문제 목록'
        ordering = ['quiz', 'order']
        unique_together = ['quiz', 'order']  # 같은 퀴즈 내에서 문제 순서는 중복되지 않음

    def __str__(self):
        return f"{self.quiz.title}의 {self.order}번 문제"

class QuizAttempt(models.Model):
    """퀴즈 응시 기록 모델"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.OneToOneField(Quiz, on_delete=models.CASCADE, related_name='attempt', null=True, blank=True)
    quiz_type = models.CharField(max_length=20, blank=True, null=True)
    mode = models.CharField(max_length=20, blank=True, null=True)
    started_at = models.DateTimeField('시작 시간', auto_now_add=True)
    completed_at = models.DateTimeField('완료 시간', null=True, blank=True)
    score = models.IntegerField('점수', default=0)
    total_questions = models.IntegerField('전체 문제 수', default=0)
    correct_answers = models.IntegerField('정답 수', default=0)

    class Meta:
        verbose_name = '퀴즈 응시 기록'
        verbose_name_plural = '퀴즈 응시 기록 목록'
        ordering = ['-started_at']
        unique_together = ['user', 'quiz_type', 'mode', 'completed_at']  # 중복 기록 방지를 위한 제약조건 추가

    def __str__(self):
        return f"{self.user.username}의 {self.quiz.title if self.quiz else self.get_type_display()} 응시"

    def get_type_display(self):
        # 유형+모드 조합을 한글로 반환
        type_map = {
            'ko_to_en': '한→영',
            'en_to_ko': '영→한',
            'favorite': '즐겨찾기',
        }
        mode_map = {
            'multiple': '객관식',
            'typing': '주관식',
        }
        t = type_map.get(self.quiz_type, '기타')
        m = mode_map.get(self.mode, '')
        return f"{t} {m}".strip()

    @property
    def accuracy_rate(self):
        """정답률 계산"""
        if self.total_questions == 0:
            return 0
        return (self.correct_answers / self.total_questions) * 100

class QuizAnswerHistory(models.Model):
    """퀴즈 문제별 답안 기록 모델"""
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answer_history')
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name='answer_history')
    user_answer = models.CharField('사용자 답안', max_length=200)
    is_correct = models.BooleanField('정답 여부', default=False)
    answered_at = models.DateTimeField('답변 시간', auto_now_add=True)

    class Meta:
        verbose_name = '퀴즈 답안 기록'
        verbose_name_plural = '퀴즈 답안 기록 목록'
        ordering = ['attempt', 'question__order']

    def __str__(self):
        return f"{self.attempt.user.username}의 {self.question.quiz.title} {self.question.order}번 답안"

class WrongAnswerNote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wrong_answers')
    word = models.ForeignKey(Word, on_delete=models.CASCADE)
    question = models.CharField(max_length=200)  # 문제 (한글)
    correct_answer = models.CharField(max_length=200)  # 정답 (영어)
    user_answer = models.CharField(max_length=200)  # 사용자의 답
    created_at = models.DateTimeField(auto_now_add=True)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)  # 마지막 복습 시간
    is_mastered = models.BooleanField(default=False)  # 마스터 여부를 저장하는 필드 추가

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'word']  # 같은 단어는 한 번만 저장

    def __str__(self):
        return f"{self.user.username}의 오답: {self.word.english}"
