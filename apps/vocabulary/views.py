from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Case, When, Value, IntegerField
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Word, WordBookmark, PersonalWordList

def is_admin(user):
    """관리자 권한 체크"""
    return user.is_superuser or user.is_staff

# Create your views here.

@login_required
def word_list(request):
    """단어 목록 뷰"""
    # 검색 및 필터링
    search_query = request.GET.get('search', '')
    difficulty = request.GET.get('difficulty', '')
    
    # 사용자의 현재 레벨 가져오기
    user_level = request.user.userlevel.current_level if hasattr(request.user, 'userlevel') else 1
    
    # 기본 쿼리셋
    words = Word.objects.all()
    
    # 검색어가 있는 경우
    if search_query:
        words = words.filter(
            Q(english__icontains=search_query) |
            Q(korean__icontains=search_query)
        )
    
    # 난이도 필터링
    if difficulty:
        words = words.filter(difficulty=difficulty)
    # 난이도 전체 선택 시에는 필터링하지 않음 (모든 단어 표시)
    
    # 난이도 순서로 정렬 (easy -> medium -> hard)
    words = words.annotate(
        difficulty_order=Case(
            When(difficulty='easy', then=Value(1)),
            When(difficulty='medium', then=Value(2)),
            When(difficulty='hard', then=Value(3)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('difficulty_order', 'english')
    
    # 페이지네이션
    paginator = Paginator(words, 20)  # 페이지당 20개
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_number)
    except:
        page_obj = paginator.get_page(1)
    
    # 북마크 상태와 나만의 단어장 상태 추가
    for word in page_obj:
        word.is_bookmarked = word.bookmarks.filter(user=request.user).exists()
        word.is_in_personal_list = word.personal_lists.filter(user=request.user).exists()
    
    # 난이도 선택 옵션
    difficulties = [
        ('', '난이도 전체'),
        ('easy', '초급'),
        ('medium', '중급'),
        ('hard', '고급')
    ]
    
    context = {
        'words': page_obj,
        'search_query': search_query,
        'difficulty': difficulty,
        'difficulties': difficulties,
        'is_admin': is_admin(request.user),
        'user_level': user_level,
        'show_all': request.GET.get('show_all') == 'true',
        'total_words': words.count()  # 전체 단어 수 추가
    }
    
    return render(request, 'vocabulary/word_list.html', context)

@login_required
def word_detail(request, word_id):
    """단어 상세 뷰"""
    word = get_object_or_404(Word, id=word_id)
    context = {
        'word': word,
    }
    return render(request, 'vocabulary/word_detail.html', context)

@login_required
def bookmarked_words(request):
    """즐겨찾기한 단어 목록 뷰"""
    # 검색 및 필터링
    search_query = request.GET.get('search', '')
    difficulty = request.GET.get('difficulty', '')
    
    # 북마크된 단어 가져오기
    bookmarked_words = Word.objects.filter(
        bookmarks__user=request.user
    ).distinct()
    
    # 검색어가 있는 경우
    if search_query:
        bookmarked_words = bookmarked_words.filter(
            Q(english__icontains=search_query) |
            Q(korean__icontains=search_query)
        )
    
    # 난이도 필터링
    if difficulty:
        bookmarked_words = bookmarked_words.filter(difficulty=difficulty)
    
    # 난이도 순서로 정렬
    bookmarked_words = bookmarked_words.annotate(
        difficulty_order=Case(
            When(difficulty='easy', then=Value(1)),
            When(difficulty='medium', then=Value(2)),
            When(difficulty='hard', then=Value(3)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('difficulty_order', 'english')
    
    # 페이지네이션
    paginator = Paginator(bookmarked_words, 20)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_number)
    except:
        page_obj = paginator.get_page(1)
    
    # 북마크 상태 추가
    for word in page_obj:
        word.is_bookmarked = True
    
    # 난이도 선택 옵션
    difficulties = [
        ('', '난이도 전체'),
        ('easy', '초급'),
        ('medium', '중급'),
        ('hard', '고급')
    ]
    
    context = {
        'words': page_obj,
        'search_query': search_query,
        'difficulty': difficulty,
        'difficulties': difficulties,
        'is_admin': is_admin(request.user),
        'show_bookmarked_only': True,
        'total_words': bookmarked_words.count()
    }
    
    return render(request, 'vocabulary/word_list.html', context)

@login_required
@require_POST
def toggle_bookmark(request, word_id):
    """단어 즐겨찾기 토글"""
    word = get_object_or_404(Word, id=word_id)
    bookmark, created = WordBookmark.objects.get_or_create(
        user=request.user,
        word=word
    )
    
    if not created:
        bookmark.delete()
        is_bookmarked = False
    else:
        is_bookmarked = True
    
    return JsonResponse({
        'success': True,
        'is_bookmarked': is_bookmarked
    })

@login_required
@user_passes_test(is_admin)
def word_add(request):
    """단어 추가 (관리자 전용)"""
    if request.method == 'POST':
        word = Word.objects.create(
            english=request.POST['english'],
            korean=request.POST['korean'],
            part_of_speech=request.POST['part_of_speech'],
            difficulty=request.POST['difficulty'],
            example_sentence=request.POST['example_sentence'],
            example_translation=request.POST['example_translation']
        )
        messages.success(request, f'단어 "{word.english}"가 추가되었습니다.')
        return redirect('vocabulary:word_list')
    
    return render(request, 'vocabulary/word_add.html')

@login_required
@user_passes_test(is_admin)
def word_edit(request, word_id):
    """단어 수정 (관리자 전용)"""
    word = get_object_or_404(Word, id=word_id)
    
    if request.method == 'POST':
        print("\n=== 단어 수정 시작 ===")
        print(f"[DEBUG] POST 데이터: {request.POST}")
        print(f"[DEBUG] 수정 전 단어 정보: {word.english}, {word.korean}, {word.part_of_speech}, {word.difficulty}")
        
        word.english = request.POST['english']
        word.korean = request.POST['korean']
        word.part_of_speech = request.POST['part_of_speech']
        word.difficulty = request.POST['difficulty']
        word.example_sentence = request.POST['example_sentence']
        word.example_translation = request.POST['example_translation']
        word.save()
        
        print(f"[DEBUG] 수정 후 단어 정보: {word.english}, {word.korean}, {word.part_of_speech}, {word.difficulty}")
        print("=== 단어 수정 완료 ===\n")
        
        messages.success(request, f'단어 "{word.english}"가 수정되었습니다.')
        return redirect('vocabulary:word_list')
    
    return render(request, 'vocabulary/word_edit.html', {'word': word})

@login_required
@user_passes_test(is_admin)
def word_delete(request, word_id):
    """단어 삭제 (관리자 전용)"""
    word = get_object_or_404(Word, id=word_id)
    
    if request.method == 'POST':
        english = word.english
        word.delete()
        messages.success(request, f'단어 "{english}"가 삭제되었습니다.')
        return redirect('vocabulary:word_list')
    
    return render(request, 'vocabulary/word_delete.html', {'word': word})

@login_required
@require_POST
def toggle_personal_word(request, word_id):
    """개인 단어장 토글"""
    word = get_object_or_404(Word, id=word_id)
    personal_word, created = PersonalWordList.objects.get_or_create(
        user=request.user,
        word=word
    )
    
    if not created:
        personal_word.delete()
        is_added = False
    else:
        is_added = True
    
    return JsonResponse({
        'success': True,
        'is_added': is_added
    })

@login_required
def personal_word_list(request):
    """개인 단어장 목록 뷰"""
    # 검색 및 필터링
    search_query = request.GET.get('search', '')
    difficulty = request.GET.get('difficulty', '')
    
    # 개인 단어장 단어 가져오기
    personal_words = Word.objects.filter(
        personal_lists__user=request.user
    ).distinct()
    
    # 검색어가 있는 경우
    if search_query:
        personal_words = personal_words.filter(
            Q(english__icontains=search_query) |
            Q(korean__icontains=search_query)
        )
    
    # 난이도 필터링
    if difficulty:
        personal_words = personal_words.filter(difficulty=difficulty)
    
    # 난이도 순서로 정렬
    personal_words = personal_words.annotate(
        difficulty_order=Case(
            When(difficulty='easy', then=Value(1)),
            When(difficulty='medium', then=Value(2)),
            When(difficulty='hard', then=Value(3)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('difficulty_order', 'english')
    
    # 페이지네이션
    paginator = Paginator(personal_words, 20)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_number)
    except:
        page_obj = paginator.get_page(1)
    
    # 개인 단어장 상태 추가
    for word in page_obj:
        word.is_in_personal_list = True
    
    # 난이도 선택 옵션
    difficulties = [
        ('', '난이도 전체'),
        ('easy', '초급'),
        ('medium', '중급'),
        ('hard', '고급')
    ]
    
    context = {
        'words': page_obj,
        'search_query': search_query,
        'difficulty': difficulty,
        'difficulties': difficulties,
        'is_admin': is_admin(request.user),
        'show_personal_only': True,
        'total_words': personal_words.count()
    }
    
    return render(request, 'vocabulary/word_list.html', context)
