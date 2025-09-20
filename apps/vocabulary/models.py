from django.db import models
from django.conf import settings

class Category(models.Model):
    """단어 카테고리 모델"""
    name = models.CharField('카테고리명', max_length=50)
    description = models.TextField('설명', blank=True)
    order = models.IntegerField('정렬 순서', default=0)
    created_at = models.DateTimeField('생성일', auto_now_add=True)

    class Meta:
        verbose_name = '카테고리'
        verbose_name_plural = '카테고리 목록'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

class Word(models.Model):
    """단어 모델"""
    DIFFICULTY_CHOICES = [
        ('easy', '쉬움'),
        ('medium', '보통'),
        ('hard', '어려움')
    ]
    
    PART_OF_SPEECH_CHOICES = [
        ('noun', '명사'),
        ('verb', '동사'),
        ('adjective', '형용사'),
        ('adverb', '부사'),
        ('preposition', '전치사'),
        ('conjunction', '접속사'),
        ('pronoun', '대명사'),
        ('interjection', '감탄사'),
        ('article', '관사'),
        ('other', '기타')
    ]
    
    english = models.CharField('영어', max_length=100)
    korean = models.CharField('한글 뜻', max_length=200)
    difficulty = models.CharField(
        '난이도',
        max_length=10,
        choices=DIFFICULTY_CHOICES,
        default='medium'
    )
    part_of_speech = models.CharField(
        '품사',
        max_length=20,
        choices=PART_OF_SPEECH_CHOICES,
        default='noun'
    )
    example_sentence = models.TextField('예문', blank=True, null=True)
    example_translation = models.TextField('예문 번역', blank=True, null=True)
    is_bookmarked = models.BooleanField('즐겨찾기', default=False)
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)
    daily_word_date = models.DateField(null=True, blank=True)  # 오늘의 단어로 선택된 날짜

    class Meta:
        verbose_name = '단어'
        verbose_name_plural = '단어 목록'
        ordering = ['english']

    def __str__(self):
        return f"{self.english} ({self.korean})"

    def save(self, *args, **kwargs):
        # 저장 시 영어는 소문자로 변환
        self.english = self.english.lower()
        super().save(*args, **kwargs)

class Example(models.Model):
    """예문 모델"""
    word = models.ForeignKey(Word, on_delete=models.CASCADE, related_name='examples')
    english = models.TextField('영어 예문')
    korean = models.TextField('한글 해석')
    created_at = models.DateTimeField('생성일', auto_now_add=True)

    class Meta:
        verbose_name = '예문'
        verbose_name_plural = '예문 목록'

    def __str__(self):
        return f"{self.word.english}의 예문"

class WordBookmark(models.Model):
    """단어 북마크 모델"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookmarks')
    word = models.ForeignKey(Word, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField('북마크 일시', auto_now_add=True)
    note = models.TextField('메모', blank=True)

    class Meta:
        verbose_name = '단어 북마크'
        verbose_name_plural = '단어 북마크 목록'
        unique_together = ['user', 'word']  # 사용자당 단어 중복 북마크 방지
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}의 단어 북마크: {self.word.english}"

class PersonalWordList(models.Model):
    """사용자의 개인 단어장 모델"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='personal_word_lists')
    word = models.ForeignKey(Word, on_delete=models.CASCADE, related_name='personal_lists')
    created_at = models.DateTimeField('추가 일시', auto_now_add=True)
    note = models.TextField('메모', blank=True)

    class Meta:
        verbose_name = '개인 단어장'
        verbose_name_plural = '개인 단어장 목록'
        unique_together = ['user', 'word']  # 사용자당 단어 중복 추가 방지
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}의 단어장: {self.word.english}"
