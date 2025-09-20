from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Max
from .models import Quiz, QuizQuestion, QuizAttempt, WrongAnswerNote
from apps.vocabulary.models import Word
import random
from django.urls import reverse
from apps.study.models import StudyProgress, WordStudyHistory
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
import json
from django.core.paginator import Paginator

# Create your views here.

@login_required
def quiz_home(request):
    """퀴즈 홈 뷰"""
    # 사용자의 학습 진행 상황 가져오기
    total_words = Word.objects.count()
    learned_words = StudyProgress.objects.filter(user=request.user).count()
    
    # 학습한 단어들의 수 계산
    studied_words_count = Word.objects.filter(
        study_progress__user=request.user,
        study_progress__review_count__gt=0
    ).distinct().count()
    
    # 사용자가 생성한 퀴즈 또는 공개된 퀴즈 중 최근 5개
    recent_quizzes = Quiz.objects.filter(
        Q(created_by=request.user) | Q(is_public=True)
    ).order_by('-created_at')[:5]

    # 최근 퀴즈 기록 추가 - 중복 제거
    recent_attempts_list = QuizAttempt.objects.filter(
        user=request.user,
        completed_at__isnull=False
    ).values('quiz', 'user', 'completed_at').annotate(
        id=Max('id')  # 각 그룹에서 가장 최근의 ID 선택
    ).values_list('id', flat=True)
    
    # 선택된 ID로 전체 레코드 조회
    recent_attempts_list = QuizAttempt.objects.filter(
        id__in=recent_attempts_list
    ).order_by('-completed_at')
    
    page_number = request.GET.get('page', 1)
    paginator = Paginator(recent_attempts_list, 5)
    recent_attempts = paginator.get_page(page_number)
    
    context = {
        'total_words': total_words,
        'learned_words': learned_words,
        'studied_words_count': studied_words_count,
        'recent_quizzes': recent_quizzes,
        'recent_attempts': recent_attempts,
        'paginator': paginator,
    }
    
    return render(request, 'quiz/quiz_home.html', context)

@login_required
def word_test(request):
    """일반 단어 테스트"""
    if request.method == 'POST':
        # 답안 제출 처리
        data = request.POST
        score = 0
        results = []
        
        # 퀴즈 생성
        quiz = Quiz.objects.create(
            title=f"{request.user.username}의 단어 테스트",
            quiz_type='en_to_ko',
            difficulty='medium',
            created_by=request.user,
            is_public=False
        )
        
        for i in range(10):  # 10문제
            question_key = f'question_{i}'
            answer_key = f'answer_{i}'
            correct_key = f'correct_{i}'
            
            if question_key in data and answer_key in data and correct_key in data:
                user_answer = data[answer_key].strip()
                correct_answer = data[correct_key].strip()
                word_id = data[question_key]
                word = get_object_or_404(Word, id=word_id)
                
                # 정답 체크
                is_correct = user_answer.lower() == correct_answer.lower()
                
                # 퀴즈 문제 생성
                question = QuizQuestion.objects.create(
                    quiz=quiz,
                    word=word,
                    order=i+1,
                    user_answer=user_answer,
                    is_correct=is_correct
                )
                
                # 학습 기록 저장
                WordStudyHistory.objects.create(
                    user=request.user,
                    word=word,
                    is_correct=is_correct,
                )
                
                if is_correct:
                    score += 1
                
                results.append({
                    'question': word.english if correct_answer == word.korean else word.korean,
                    'correct_answer': correct_answer,
                    'user_answer': user_answer,
                    'is_correct': is_correct
                })
        
        # 퀴즈 시도 기록 저장
        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            score=score * 10,  # 100점 만점
            total_questions=10,
            correct_answers=score,
            completed_at=timezone.now()
        )
        
        context = {
            'score': score * 10,  # 100점 만점으로 변환
            'correct_count': score,
            'wrong_count': 10 - score,
            'answers': results,
            'quiz': quiz,
            'attempt': attempt
        }
        
        return render(request, 'quiz/test_result.html', context)
    
    # GET 요청: 새로운 테스트 시작
    # 북마크된 단어만 테스트할지 여부 확인
    bookmarked_only = request.GET.get('bookmarked', 'false').lower() == 'true'
    
    # 기본 쿼리셋
    if bookmarked_only:
        # 북마크된 단어만 선택
        studied_words = Word.objects.filter(
            study_progress__user=request.user,
            study_progress__is_bookmarked=True
        ).distinct()
    else:
        # 학습한 단어들 중에서 선택
        studied_words = Word.objects.filter(
            study_progress__user=request.user,
            study_progress__review_count__gt=0
        ).distinct()
    
    if studied_words.count() < 10:
        messages.warning(request, '테스트를 위해서는 최소 10개의 단어를 학습해야 합니다.')
        return redirect('study:daily_words')
    
    test_words = list(studied_words.order_by('?')[:10])
    questions = []
    
    for i, word in enumerate(test_words):
        # 랜덤하게 문제 유형 선택 (영한 또는 한영)
        is_en_to_ko = random.choice([True, False])
        
        if is_en_to_ko:
            question = word.english
            answer = word.korean
            question_type = 'en_to_ko'
        else:
            question = word.korean
            answer = word.english
            question_type = 'ko_to_en'
        
        questions.append({
            'id': i + 1,
            'word_id': word.id,
            'question': question,
            'answer': answer,
            'type': question_type
        })
    
    return render(request, 'quiz/word_test.html', {
        'questions': questions,
        'bookmarked_only': bookmarked_only
    })

@login_required
def quiz_list(request):
    """퀴즈 목록 뷰"""
    # 공개된 퀴즈 또는 자신이 만든 퀴즈만 표시
    quizzes = Quiz.objects.filter(
        Q(is_public=True) | Q(created_by=request.user)
    ).select_related('created_by')
    
    # 각 퀴즈의 문제 수를 미리 계산
    quiz_questions = QuizQuestion.objects.filter(quiz__in=quizzes).values('quiz').annotate(question_count=Count('id'))
    quiz_question_counts = {q['quiz']: q['question_count'] for q in quiz_questions}
    
    # 각 퀴즈 객체에 문제 수 추가
    for quiz in quizzes:
        quiz.question_count = quiz_question_counts.get(quiz.id, 0)
    
    context = {
        'quizzes': quizzes,
        'quiz_types': Quiz.QUIZ_TYPES,
        'difficulties': Word.DIFFICULTY_CHOICES,
    }
    return render(request, 'quiz/quiz_list.html', context)

@login_required
def quiz_delete(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
    if request.method == 'POST':
        quiz.delete()
        messages.success(request, '퀴즈가 삭제되었습니다.')
        return redirect('quiz:quiz_list')
    return redirect('quiz:quiz_list')

@login_required
def quiz_create(request):
    """퀴즈 생성 뷰"""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        quiz_type = request.POST.get('quiz_type')
        difficulty = request.POST.get('difficulty')
        is_public = request.POST.get('is_public') == 'on'
        time_limit = request.POST.get('time_limit', 0)
        word_count = int(request.POST.get('word_count', 10))
        
        print(f"[DEBUG] Creating quiz: {title}, type: {quiz_type}, word_count: {word_count}")
        
        # 퀴즈 생성
        quiz = Quiz.objects.create(
            title=title,
            description=description,
            quiz_type=quiz_type,
            difficulty=difficulty,
            created_by=request.user,
            is_public=is_public,
            time_limit=time_limit
        )
        
        print(f"[DEBUG] Quiz created with ID: {quiz.id}")
        
        # 문제 생성 - 사용자가 학습한 단어들 중에서 선택
        studied_words = Word.objects.filter(
            study_progress__user=request.user,
            study_progress__review_count__gt=0
        ).distinct()
        
        studied_words_count = studied_words.count()
        print(f"[DEBUG] Found {studied_words_count} studied words")
        
        if studied_words_count < word_count:
            print(f"[DEBUG] Not enough studied words. Required: {word_count}, Available: {studied_words_count}")
            quiz.delete()
            messages.error(request, f'퀴즈 생성을 위해서는 최소 {word_count}개의 단어를 학습해야 합니다.')
            return redirect('quiz:quiz_list')
        
        words = list(studied_words.order_by('?')[:word_count])
        print(f"[DEBUG] Selected {len(words)} words for quiz")
        
        for i, word in enumerate(words, 1):
            print(f"[DEBUG] Creating question {i} with word: {word.english} - {word.korean}")
            question = QuizQuestion(quiz=quiz, word=word, order=i)
            
            if quiz_type == 'multiple':
                # 객관식 보기 생성
                wrong_words = Word.objects.exclude(id=word.id).order_by('?')[:3]
                options = [word.korean] + [w.korean for w in wrong_words]
                random.shuffle(options)
                
                question.option1 = options[0]
                question.option2 = options[1]
                question.option3 = options[2]
                question.option4 = options[3]
                question.correct_option = options.index(word.korean) + 1
            
            question.save()
            print(f"[DEBUG] Question {i} saved with ID: {question.id}")
        
        questions_count = QuizQuestion.objects.filter(quiz=quiz).count()
        print(f"[DEBUG] Total questions created for quiz: {questions_count}")
        
        messages.success(request, '퀴즈가 생성되었습니다.')
        return redirect('quiz:quiz_detail', quiz_id=quiz.id)
    
    context = {
        'quiz_types': Quiz.QUIZ_TYPES,
        'difficulties': Word.DIFFICULTY_CHOICES,
    }
    return render(request, 'quiz/quiz_create.html', context)

@login_required
def quiz_detail(request, quiz_id):
    """퀴즈 상세 뷰"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    # 비공개 퀴즈인 경우 작성자만 접근 가능
    if not quiz.is_public and quiz.created_by != request.user:
        messages.error(request, '접근 권한이 없습니다.')
        return redirect('quiz:quiz_list')
    
    # 문제 수 계산
    question_count = QuizQuestion.objects.filter(quiz=quiz).count()
    quiz.question_count = question_count
    
    # 이전 응시 기록
    user_attempts = QuizAttempt.objects.filter(
        user=request.user,
        quiz=quiz
    ).order_by('-started_at')
    
    context = {
        'quiz': quiz,
        'user_attempts': user_attempts,
        'quiz_types': Quiz.QUIZ_TYPES,
        'difficulties': Word.DIFFICULTY_CHOICES,
    }
    return render(request, 'quiz/quiz_detail.html', context)

@login_required
def quiz_start(request, quiz_id):
    """퀴즈 시작 뷰"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = QuizQuestion.objects.filter(quiz=quiz).order_by('id')
    
    if not questions.exists():
        messages.error(request, '이 퀴즈에는 문제가 없습니다.')
        return redirect('quiz:quiz_detail', quiz_id=quiz_id)
    
    # 첫 번째 문제로 시작
    first_question = questions.first()
    
    context = {
        'quiz': quiz,
        'question': first_question,
        'question_number': 1,
        'total_questions': questions.count(),
        'end_time': timezone.now() + timezone.timedelta(minutes=30)  # 30분 제한시간
    }
    
    return render(request, 'quiz/quiz_submit.html', context)

def calculate_quiz_points(score, quiz_type, mode):
    """퀴즈 점수에 따른 포인트 계산"""
    base_points = {
        'multiple': 10,  # 객관식 문제당 10포인트
        'typing': 15,    # 주관식 문제당 15포인트
    }
    
    # 기본 포인트 계산
    points = score * base_points.get(mode, 10)
    
    # 퀴즈 타입별 보너스
    if quiz_type == 'ko_to_en':
        points = int(points * 1.2)  # 한→영 퀴즈는 20% 보너스
    
    return points

@login_required
def quiz_submit(request, quiz_id):
    """퀴즈 답안 제출 뷰"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = QuizQuestion.objects.filter(quiz=quiz).order_by('id')
    
    if request.method == 'POST':
        # 답안 처리
        answer = request.POST.get('answer', '').strip()
        question_id = request.POST.get('question_id')
        
        try:
            current_question = questions.get(id=question_id)
        except QuizQuestion.DoesNotExist:
            messages.error(request, '잘못된 문제 ID입니다.')
            return redirect('quiz:quiz_detail', quiz_id=quiz_id)
        
        # 답안 정확도 확인
        is_correct = False
        if quiz.quiz_type == 'en_to_ko':
            is_correct = answer.lower() == current_question.word.korean.lower()
        else:
            is_correct = answer.lower() == current_question.word.english.lower()
        
        # 답안 저장
        current_question.user_answer = answer
        current_question.is_correct = is_correct
        current_question.save()
        
        print(f"[DEBUG] Saving answer - Question: {current_question.word.english}, User Answer: {answer}, Correct: {is_correct}")
        
        # 학습 기록 저장
        study_history = WordStudyHistory.objects.create(
            user=request.user,
            word=current_question.word,
            is_correct=is_correct,
        )
        print(f"[DEBUG] Created WordStudyHistory - ID: {study_history.id}, Word: {study_history.word.english}, Is Correct: {study_history.is_correct}")
        
        # 다음 문제 또는 결과 페이지로
        next_question = questions.filter(id__gt=current_question.id).first()
        if next_question:
            context = {
                'quiz': quiz,
                'question': next_question,
                'question_number': list(questions).index(next_question) + 1,
                'total_questions': questions.count(),
                'end_time': request.POST.get('end_time')
            }
            return render(request, 'quiz/quiz_submit.html', context)
        else:
            # 모든 문제를 다 풀었을 때
            correct_count = questions.filter(is_correct=True).count()
            score = (correct_count / questions.count()) * 100
            
            # 퀴즈 완료 시 포인트 지급
            points = calculate_quiz_points(correct_count, quiz.quiz_type, quiz.mode)
            request.user.profile.add_points(points, f"{quiz.get_quiz_type_display()} 퀴즈 완료")
            
            # 퀴즈 시도 기록 저장
            attempt = QuizAttempt.objects.create(
                user=request.user,
                quiz=quiz,
                score=score,
                total_questions=questions.count(),
                correct_answers=correct_count,
                completed_at=timezone.now()
            )
            
            # 결과 컨텍스트 준비
            answers = []
            for q in questions:
                answers.append({
                    'question': q.word.english if quiz.quiz_type == 'en_to_ko' else q.word.korean,
                    'correct_answer': q.word.korean if quiz.quiz_type == 'en_to_ko' else q.word.english,
                    'user_answer': q.user_answer,
                    'is_correct': q.is_correct
                })
            
            context = {
                'quiz': quiz,
                'score': score,
                'correct_count': correct_count,
                'total_questions': questions.count(),
                'answers': answers,
                'attempt': attempt
            }
            return render(request, 'quiz/test_result.html', context)
    
    # GET 요청 시 첫 문제로 시작
    first_question = questions.first()
    if not first_question:
        messages.error(request, '이 퀴즈에는 문제가 없습니다.')
        return redirect('quiz:quiz_detail', quiz_id=quiz_id)
        
    context = {
        'quiz': quiz,
        'question': first_question,
        'question_number': 1,
        'total_questions': questions.count(),
        'end_time': timezone.now() + timezone.timedelta(minutes=30)
    }
    return render(request, 'quiz/quiz_submit.html', context)

@login_required
def quiz_history_detail(request, attempt_id):
    """퀴즈 응시 기록 상세 뷰"""
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
    questions = QuizQuestion.objects.filter(quiz=attempt.quiz).select_related('word')
    
    # 이전 퀴즈 기록 가져오기
    previous_attempts = QuizAttempt.objects.filter(
        user=request.user,
        completed_at__lt=attempt.completed_at
    ).order_by('-completed_at')[:5]
    
    answer_history = []
    for question in questions:
        # 이전 퀴즈에서의 정답 여부 확인
        previous_correct = False
        if previous_attempts.exists():
            prev_questions = QuizQuestion.objects.filter(
                quiz__in=[a.quiz for a in previous_attempts if a.quiz],
                word=question.word,
                is_correct=True
            ).exists()
            previous_correct = prev_questions
        
        answer_history.append({
            'question': question,
            'user_answer': question.user_answer,
            'is_correct': question.is_correct,
            'previous_correct': previous_correct
        })
    
    context = {
        'attempt': attempt,
        'answer_history': answer_history,
        'show_add_note': False,  # 결과 복습에서는 오답노트 버튼 숨김
        'previous_attempts': previous_attempts
    }
    
    return render(request, 'quiz/quiz_history_detail.html', context)

@login_required
def quiz_timer(request):
    """타이머 퀴즈 뷰"""
    if request.method == 'POST':
        # 답안 처리
        answers = request.POST.getlist('answers[]')
        word_ids = request.POST.getlist('word_ids[]')
        score = 0
        results = []
        
        for word_id, answer in zip(word_ids, answers):
            word = Word.objects.get(id=word_id)
            is_correct = answer.lower().strip() == word.korean.lower().strip()
            if is_correct:
                score += 1
            results.append({
                'word': word.english,
                'correct_answer': word.korean,
                'user_answer': answer,
                'is_correct': is_correct
            })
            
            # 학습 기록 저장
            WordStudyHistory.objects.create(
                user=request.user,
                word=word,
                is_correct=is_correct,
            )
        
        # 퀴즈 시도 기록 저장
        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=None,  # 타이머 퀴즈는 퀴즈 객체가 없음
            score=score * 10,  # 100점 만점
            total_questions=len(word_ids),
            correct_answers=score,
            completed_at=timezone.now()
        )
        
        context = {
            'score': score * 10,  # 100점 만점으로 변환
            'correct_count': score,
            'total_questions': len(word_ids),
            'answers': results,
            'attempt': attempt
        }
        
        return render(request, 'quiz/test_result.html', context)
    
    # GET 요청: 새로운 테스트 시작
    # 학습한 단어들 중에서 20개를 랜덤으로 선택
    studied_words = Word.objects.filter(
        study_progress__user=request.user,
        study_progress__review_count__gt=0
    ).distinct()
    
    if studied_words.count() < 20:
        messages.warning(request, '타이머 퀴즈를 위해서는 최소 20개의 단어를 학습해야 합니다.')
        return redirect('study:daily_words')
    
    test_words = list(studied_words.order_by('?')[:20])
    questions = []
    
    for word in test_words:
        questions.append({
            'word_id': word.id,
            'english': word.english,
            'korean': word.korean
        })
    
    context = {
        'questions': questions,
        'time_limit': 300,  # 5분(300초) 제한시간
    }
    
    return render(request, 'quiz/timer_quiz.html', context)

@login_required
@csrf_exempt
def en_to_ko_multiple(request):
    user = request.user
    studied_words = Word.objects.filter(
        study_progress__user=user,
        study_progress__review_count__gt=0
    ).distinct()
    if studied_words.count() < 15:
        messages.warning(request, '테스트를 위해서는 최소 15개의 단어를 학습해야 합니다.')
        return redirect('quiz:quiz_home')

    if request.method == 'POST':
        # 세션에서 문제 데이터 가져오기
        questions = request.session.get('en_to_ko_multiple_questions', [])
        if not questions or 'word_id' not in questions[0]:
            messages.error(request, '퀴즈 세션이 만료되었습니다. 다시 시작해주세요.')
            return redirect('quiz:quiz_home')
            
        user_answers = [request.POST.get(f'answer_{i+1}') for i in range(len(questions))]
        correct_count = 0
        results = []
        
        # 퀴즈 생성
        quiz = Quiz.objects.create(
            title="영어 → 한국어 객관식",
            quiz_type='en_to_ko',
            difficulty='medium',
            created_by=request.user,
            is_public=False
        )
        
        for i, q in enumerate(questions):
            correct = user_answers[i] == q['answer']
            correct_count += int(correct)
            
            # 단어 찾기
            word = Word.objects.get(id=q['word_id'])
            
            # 퀴즈 문제 생성
            question = QuizQuestion.objects.create(
                quiz=quiz,
                word=word,
                order=i+1,
                user_answer=user_answers[i],
                is_correct=correct
            )
            
            # 학습 기록 저장
            WordStudyHistory.objects.create(
                user=request.user,
                word=word,
                is_correct=correct,
            )
            
            results.append({
                'question': q['question'],
                'answer': q['answer'],
                'options': q['options'],
                'user_answer': user_answers[i],
                'is_correct': correct
            })
            
        score = int(correct_count / len(questions) * 100)
        
        # 퀴즈 시도 기록 저장
        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            quiz_type='en_to_ko',
            mode='multiple',
            score=score,
            total_questions=len(questions),
            correct_answers=correct_count,
            completed_at=timezone.now()
        )
        
        # 포인트 지급
        points = calculate_quiz_points(correct_count, 'en_to_ko', 'multiple')
        request.user.profile.add_points(points, "영→한 객관식 퀴즈 완료")
        
        # 세션 데이터 삭제
        if 'en_to_ko_multiple_questions' in request.session:
            del request.session['en_to_ko_multiple_questions']
        
        return render(request, 'quiz/en_to_ko_multiple_result.html', {
            'results': results,
            'score': score,
            'correct_count': correct_count,
            'total': len(questions),
            'attempt': attempt
        })
    else:
        # GET 요청 시 세션 초기화
        if 'en_to_ko_multiple_questions' in request.session:
            del request.session['en_to_ko_multiple_questions']
            
        import random
        words = list(studied_words.order_by('?')[:15])
        questions = []
        for word in words:
            wrongs = list(Word.objects.exclude(id=word.id).order_by('?')[:3])
            options = [word.korean] + [w.korean for w in wrongs]
            random.shuffle(options)
            questions.append({
                'word_id': word.id,
                'question': word.english,
                'answer': word.korean,
                'options': options
            })
        request.session['en_to_ko_multiple_questions'] = questions
        return render(request, 'quiz/en_to_ko_multiple.html', {
            'questions': questions
        })

@login_required
@csrf_exempt
def en_to_ko_typing(request):
    user = request.user
    studied_words = Word.objects.filter(
        study_progress__user=user,
        study_progress__review_count__gt=0
    ).distinct()
    if studied_words.count() < 15:
        messages.warning(request, '테스트를 위해서는 최소 15개의 단어를 학습해야 합니다.')
        return redirect('quiz:quiz_home')

    if request.method == 'POST':
        # 세션에서 문제 데이터 가져오기
        questions = request.session.get('en_to_ko_typing_questions', [])
        if not questions or 'word_id' not in questions[0]:
            messages.error(request, '퀴즈 세션이 만료되었습니다. 다시 시작해주세요.')
            return redirect('quiz:quiz_home')
            
        user_answers = [request.POST.get(f'answer_{i+1}', '').strip() for i in range(len(questions))]
        correct_count = 0
        results = []
        
        # 퀴즈 생성
        quiz = Quiz.objects.create(
            title="영어 → 한국어 주관식",
            quiz_type='en_to_ko',
            difficulty='medium',
            created_by=request.user,
            is_public=False
        )
        
        for i, q in enumerate(questions):
            correct = user_answers[i] == q['answer']
            correct_count += int(correct)
            
            # 단어 찾기
            word = Word.objects.get(id=q['word_id'])
            
            # 퀴즈 문제 생성
            question = QuizQuestion.objects.create(
                quiz=quiz,
                word=word,
                order=i+1,
                user_answer=user_answers[i],
                is_correct=correct
            )
            
            # 학습 기록 저장
            WordStudyHistory.objects.create(
                user=request.user,
                word=word,
                is_correct=correct,
            )
            
            results.append({
                'question': q['question'],
                'answer': q['answer'],
                'user_answer': user_answers[i],
                'is_correct': correct
            })
            
        score = int(correct_count / len(questions) * 100)
        
        # 퀴즈 시도 기록 저장
        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            quiz_type='en_to_ko',
            mode='typing',
            score=score,
            total_questions=len(questions),
            correct_answers=correct_count,
            completed_at=timezone.now()
        )
        
        # 포인트 지급
        points = calculate_quiz_points(correct_count, 'en_to_ko', 'typing')
        request.user.profile.add_points(points, "영→한 주관식 퀴즈 완료")
        
        return render(request, 'quiz/en_to_ko_typing_result.html', {
            'results': results,
            'score': score,
            'correct_count': correct_count,
            'total': len(questions),
            'attempt': attempt
        })
    else:
        # GET 요청 시 세션 초기화
        if 'en_to_ko_typing_questions' in request.session:
            del request.session['en_to_ko_typing_questions']
            
        import random
        words = list(studied_words.order_by('?')[:15])
        questions = []
        for word in words:
            questions.append({
                'word_id': word.id,
                'question': word.english,
                'answer': word.korean
            })
        request.session['en_to_ko_typing_questions'] = questions
        return render(request, 'quiz/en_to_ko_typing.html', {
            'questions': questions
        })

@login_required
@csrf_exempt
def ko_to_en_multiple(request):
    user = request.user
    studied_words = Word.objects.filter(
        study_progress__user=user,
        study_progress__review_count__gt=0
    ).distinct()
    if studied_words.count() < 15:
        messages.warning(request, '테스트를 위해서는 최소 15개의 단어를 학습해야 합니다.')
        return redirect('quiz:quiz_home')

    if request.method == 'POST':
        # 세션에서 문제 데이터 가져오기
        questions = request.session.get('ko_to_en_multiple_questions', [])
        if not questions or not all('word_id' in q for q in questions):
            messages.error(request, '퀴즈 세션이 만료되었습니다. 다시 시작해주세요.')
            return redirect('quiz:quiz_home')
            
        user_answers = [request.POST.get(f'answer_{i+1}', '') for i in range(len(questions))]
        correct_count = 0
        results = []
        
        # 퀴즈 생성
        quiz = Quiz.objects.create(
            title="한국어 → 영어 객관식",
            quiz_type='ko_to_en',
            difficulty='medium',
            created_by=request.user,
            is_public=False
        )
        
        for i, q in enumerate(questions):
            correct = user_answers[i] == q['answer']
            correct_count += int(correct)
            
            # 단어 찾기
            word = Word.objects.get(id=q['word_id'])
            
            # 퀴즈 문제 생성
            question = QuizQuestion.objects.create(
                quiz=quiz,
                word=word,
                order=i+1,
                user_answer=user_answers[i],
                is_correct=correct
            )
            
            # 학습 기록 저장
            WordStudyHistory.objects.create(
                user=request.user,
                word=word,
                is_correct=correct,
            )
            
            results.append({
                'question': q['question'],
                'answer': q['answer'],
                'options': q['options'],
                'user_answer': user_answers[i],
                'is_correct': correct
            })
            
        score = int(correct_count / len(questions) * 100)
        
        # 퀴즈 시도 기록 저장
        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            quiz_type='ko_to_en',
            mode='multiple',
            score=score,
            total_questions=len(questions),
            correct_answers=correct_count,
            completed_at=timezone.now()
        )
        
        # 포인트 지급
        points = calculate_quiz_points(correct_count, 'ko_to_en', 'multiple')
        request.user.profile.add_points(points, "한→영 객관식 퀴즈 완료")
        
        # 세션 데이터 삭제
        if 'ko_to_en_multiple_questions' in request.session:
            del request.session['ko_to_en_multiple_questions']
        
        return render(request, 'quiz/ko_to_en_multiple_result.html', {
            'results': results,
            'score': score,
            'correct_count': correct_count,
            'total': len(questions),
            'attempt': attempt
        })
    else:
        # GET 요청 시 세션 초기화
        if 'ko_to_en_multiple_questions' in request.session:
            del request.session['ko_to_en_multiple_questions']
            
        import random
        words = list(studied_words.order_by('?')[:15])
        questions = []
        for word in words:
            options = list(studied_words.exclude(id=word.id).order_by('?')[:3])
            options.append(word)
            random.shuffle(options)
            questions.append({
                'word_id': word.id,
                'question': word.korean,
                'answer': word.english,
                'options': [w.english for w in options]
            })
        request.session['ko_to_en_multiple_questions'] = questions
        return render(request, 'quiz/ko_to_en_multiple.html', {
            'questions': questions
        })

@login_required
@csrf_exempt
def ko_to_en_typing(request):
    user = request.user
    studied_words = Word.objects.filter(
        study_progress__user=user,
        study_progress__review_count__gt=0
    ).distinct()
    if studied_words.count() < 15:
        messages.warning(request, '테스트를 위해서는 최소 15개의 단어를 학습해야 합니다.')
        return redirect('quiz:quiz_home')

    if request.method == 'POST':
        # 세션에서 문제 데이터 가져오기
        questions = request.session.get('ko_to_en_typing_questions', [])
        if not questions or 'word_id' not in questions[0]:
            messages.error(request, '퀴즈 세션이 만료되었습니다. 다시 시작해주세요.')
            return redirect('quiz:quiz_home')
            
        user_answers = [request.POST.get(f'answer_{i+1}', '').strip() for i in range(len(questions))]
        correct_count = 0
        results = []
        
        # 퀴즈 생성
        quiz = Quiz.objects.create(
            title="한국어 → 영어 주관식",
            quiz_type='ko_to_en',
            difficulty='medium',
            created_by=request.user,
            is_public=False
        )
        
        for i, q in enumerate(questions):
            correct = user_answers[i] == q['answer']
            correct_count += int(correct)
            
            # 단어 찾기
            word = Word.objects.get(id=q['word_id'])
            
            # 퀴즈 문제 생성
            question = QuizQuestion.objects.create(
                quiz=quiz,
                word=word,
                order=i+1,
                user_answer=user_answers[i],
                is_correct=correct
            )
            
            # 학습 기록 저장
            WordStudyHistory.objects.create(
                user=request.user,
                word=word,
                is_correct=correct,
            )
            
            results.append({
                'question': q['question'],
                'answer': q['answer'],
                'user_answer': user_answers[i],
                'is_correct': correct
            })
            
        score = int(correct_count / len(questions) * 100)
        
        # 퀴즈 시도 기록 저장
        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            quiz_type='ko_to_en',
            mode='typing',
            score=score,
            total_questions=len(questions),
            correct_answers=correct_count,
            completed_at=timezone.now()
        )
        
        # 포인트 지급
        points = calculate_quiz_points(correct_count, 'ko_to_en', 'typing')
        request.user.profile.add_points(points, "한→영 주관식 퀴즈 완료")
        
        return render(request, 'quiz/ko_to_en_typing_result.html', {
            'results': results,
            'score': score,
            'correct_count': correct_count,
            'total': len(questions),
            'attempt': attempt
        })
    else:
        # GET 요청 시 세션 초기화
        if 'ko_to_en_typing_questions' in request.session:
            del request.session['ko_to_en_typing_questions']
            
        import random
        words = list(studied_words.order_by('?')[:15])
        questions = []
        for word in words:
            questions.append({
                'word_id': word.id,
                'question': word.korean,
                'answer': word.english
            })
        request.session['ko_to_en_typing_questions'] = questions
        return render(request, 'quiz/ko_to_en_typing.html', {
            'questions': questions
        })

@login_required
@csrf_exempt
def bookmark_multiple(request):
    """즐겨찾기 단어 객관식 퀴즈"""
    if request.method == 'POST':
        data = json.loads(request.body)
        score = 0
        results = []
        
        # 퀴즈 생성
        quiz = Quiz.objects.create(
            title="즐겨찾기 객관식",
            quiz_type='bookmark',
            difficulty='medium',
            created_by=request.user,
            is_public=False
        )
        
        for i, answer in enumerate(data['answers']):
            word = get_object_or_404(Word, id=answer['word_id'])
            is_correct = answer['selected_answer'] == answer['correct_answer']
            
            if is_correct:
                score += 1
            
            # 퀴즈 문제 생성
            question = QuizQuestion.objects.create(
                quiz=quiz,
                word=word,
                order=i+1,
                user_answer=answer['selected_answer'],
                is_correct=is_correct
            )
            
            # 학습 기록 저장
            WordStudyHistory.objects.create(
                user=request.user,
                word=word,
                is_correct=is_correct,
            )
            
            results.append({
                'word': word.english,
                'meaning': word.korean,
                'user_answer': answer['selected_answer'],
                'correct_answer': answer['correct_answer'],
                'is_correct': is_correct
            })
        
        # 퀴즈 시도 기록 저장
        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            score=score * 10,  # 100점 만점
            total_questions=len(data['answers']),
            correct_answers=score,
            completed_at=timezone.now()
        )
        
        # 포인트 지급
        points = calculate_quiz_points(score, 'bookmark', 'multiple')
        request.user.profile.add_points(points, "즐겨찾기 객관식 퀴즈 완료")
        
        return JsonResponse({
            'success': True,
            'attempt_id': attempt.id
        })
    
    # GET 요청: 새로운 퀴즈 시작
    # 즐겨찾기한 단어 가져오기
    bookmarked_words = Word.objects.filter(
        bookmarks__user=request.user
    ).distinct()
    
    if bookmarked_words.count() < 10:
        messages.warning(request, '즐겨찾기한 단어가 10개 이상 필요합니다.')
        return redirect('quiz:quiz_home')
    
    # 랜덤하게 10개의 단어 선택
    test_words = list(bookmarked_words.order_by('?')[:10])
    questions = []
    
    for word in test_words:
        # 랜덤하게 문제 유형 선택 (영한 또는 한영)
        is_en_to_ko = random.choice([True, False])
        
        if is_en_to_ko:
            question = word.english
            answer = word.korean
            question_type = 'en_to_ko'
        else:
            question = word.korean
            answer = word.english
            question_type = 'ko_to_en'
        
        # 오답 선택지 생성
        wrong_answers = Word.objects.exclude(id=word.id).order_by('?')[:3]
        options = [answer] + [w.korean if is_en_to_ko else w.english for w in wrong_answers]
        random.shuffle(options)
        
        questions.append({
            'word_id': word.id,
            'question': question,
            'answer': answer,
            'options': options,
            'type': question_type
        })
    
    return render(request, 'quiz/bookmark_multiple.html', {
        'questions': questions
    })

@login_required
@csrf_exempt
def bookmark_typing(request):
    """즐겨찾기 단어 주관식 퀴즈"""
    if request.method == 'POST':
        data = json.loads(request.body)
        score = 0
        results = []
        
        # 퀴즈 생성
        quiz = Quiz.objects.create(
            title="즐겨찾기 주관식",
            quiz_type='bookmark',
            difficulty='medium',
            created_by=request.user,
            is_public=False
        )
        
        for i, answer in enumerate(data['answers']):
            word = get_object_or_404(Word, id=answer['word_id'])
            is_correct = answer['user_answer'].strip().lower() == answer['correct_answer'].lower()
            
            if is_correct:
                score += 1
            
            # 퀴즈 문제 생성
            question = QuizQuestion.objects.create(
                quiz=quiz,
                word=word,
                order=i+1,
                user_answer=answer['user_answer'],
                is_correct=is_correct
            )
            
            # 학습 기록 저장
            WordStudyHistory.objects.create(
                user=request.user,
                word=word,
                is_correct=is_correct,
            )
            
            results.append({
                'word': word.english,
                'meaning': word.korean,
                'user_answer': answer['user_answer'],
                'correct_answer': answer['correct_answer'],
                'is_correct': is_correct
            })
        
        # 퀴즈 시도 기록 저장
        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            score=score * 10,  # 100점 만점
            total_questions=len(data['answers']),
            correct_answers=score,
            completed_at=timezone.now()
        )
        
        # 포인트 지급
        points = calculate_quiz_points(score, 'bookmark', 'typing')
        request.user.profile.add_points(points, "즐겨찾기 주관식 퀴즈 완료")
        
        return JsonResponse({
            'success': True,
            'attempt_id': attempt.id
        })
    
    # GET 요청: 새로운 퀴즈 시작
    # 즐겨찾기한 단어 가져오기
    bookmarked_words = Word.objects.filter(
        bookmarks__user=request.user
    ).distinct()
    
    if bookmarked_words.count() < 10:
        messages.warning(request, '즐겨찾기한 단어가 10개 이상 필요합니다.')
        return redirect('quiz:quiz_home')
    
    # 랜덤하게 10개의 단어 선택
    test_words = list(bookmarked_words.order_by('?')[:10])
    questions = []
    
    for word in test_words:
        # 랜덤하게 문제 유형 선택 (영한 또는 한영)
        is_en_to_ko = random.choice([True, False])
        
        if is_en_to_ko:
            question = word.english
            answer = word.korean
            question_type = 'en_to_ko'
        else:
            question = word.korean
            answer = word.english
            question_type = 'ko_to_en'
        
        questions.append({
            'word_id': word.id,
            'question': question,
            'answer': answer,
            'type': question_type
        })
    
    return render(request, 'quiz/bookmark_typing.html', {
        'questions': questions
    })

@require_http_methods(["POST"])
@login_required
def toggle_mastered(request, note_id):
    """마스터 버튼 클릭 시 오답노트의 마스터 상태 토글"""
    try:
        note = WrongAnswerNote.objects.get(id=note_id, user=request.user)
        note.is_mastered = not note.is_mastered  # 마스터 상태 토글
        note.save()
        return JsonResponse({
            'status': 'success',
            'message': '마스터 상태가 변경되었습니다.'
        })
    except WrongAnswerNote.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': '오답노트를 찾을 수 없습니다.'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def all_wrong_answer_notes(request):
    """전체 오답노트 보기"""
    # 사용자의 마스터되지 않은 오답노트만 가져옴
    notes = WrongAnswerNote.objects.filter(
        user=request.user,
        is_mastered=False  # 마스터되지 않은 단어만 필터링
    ).select_related('word').order_by('-created_at')
    
    # 페이지네이션
    page = request.GET.get('page', 1)
    paginator = Paginator(notes, 10)  # 한 페이지에 10개씩 표시
    notes_page = paginator.get_page(page)
    
    context = {
        'notes': notes_page,
        'paginator': paginator,
    }
    
    return render(request, 'quiz/all_wrong_answer_notes.html', context)

@login_required
@require_POST
def add_wrong_answer(request):
    """오답 노트에 추가 (한->영, 영->한 모두 지원)"""
    try:
        data = json.loads(request.body)
        question = data.get('question')
        answer = data.get('answer')
        user_answer = data.get('user_answer')

        # 단어 찾기 (정확한 매칭)
        word = None
        if question in [w.english for w in Word.objects.all()]:
            word = Word.objects.get(english=question)
        elif question in [w.korean for w in Word.objects.all()]:
            word = Word.objects.get(korean=question)
        
        if not word:
            return JsonResponse({'success': False, 'error': '단어를 찾을 수 없습니다.'})

        # 이미 오답 노트에 있는지 확인
        existing_note = WrongAnswerNote.objects.filter(
            user=request.user,
            word=word,
            question=question,
            correct_answer=answer
        ).first()

        if existing_note:
            return JsonResponse({'success': True, 'message': '이미 오답노트에 있는 단어입니다.'})

        # 새로운 오답노트 생성
        WrongAnswerNote.objects.create(
            user=request.user,
            word=word,
            question=question,
            correct_answer=answer,
            user_answer=user_answer
        )

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def wrong_answer_notes(request):
    quiz_attempt_id = request.GET.get('quiz_id')
    if not quiz_attempt_id:
        return render(request, 'quiz/wrong_answer_notes.html', {'notes': []})

    attempt = QuizAttempt.objects.filter(id=quiz_attempt_id, user=request.user).first()
    if not attempt:
        return render(request, 'quiz/wrong_answer_notes.html', {'notes': []})

    # 해당 시도의 틀린 문제만 쿼리
    wrong_questions = QuizQuestion.objects.filter(quiz=attempt.quiz, is_correct=False)
    # 객관식/주관식 등 quiz=None인 경우(임시 퀴즈) 처리
    if attempt.quiz is None:
        # quiz=None인 경우 QuizQuestion과 연결이 없으므로, WordStudyHistory 등에서 틀린 단어를 찾아야 할 수도 있음
        # 하지만 현재 구조상 QuizQuestion이 생성되지 않으면, 틀린 단어를 알 수 없음
        # (필요시 추가 구현)
        wrong_questions = []
    
    # 각 문제별로 오답노트 등록 여부 체크
    notes = []
    for q in wrong_questions:
        already_added = WrongAnswerNote.objects.filter(user=request.user, word=q.word).exists()
        notes.append({
            'word': q.word,
            'already_added': already_added,
            'question': q,
        })

    return render(request, 'quiz/wrong_answer_notes.html', {
        'notes': notes
    })
