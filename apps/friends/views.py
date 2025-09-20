from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .models import Friendship
from apps.vocabulary.models import PersonalWordList

@login_required
def friend_vocabulary(request, friend_id):
    """친구의 단어장 페이지"""
    try:
        friend = User.objects.get(id=friend_id)
        
        # 친구 관계 확인
        if not Friendship.objects.filter(
            (Q(user=request.user, friend=friend) | Q(user=friend, friend=request.user)),
            status='accepted'
        ).exists():
            messages.error(request, '친구 관계가 아닙니다.')
            return redirect('friends:friend_list')
        
        # 친구의 단어장 가져오기
        word_list = PersonalWordList.objects.filter(user=friend).select_related('word')
        
        # 검색 기능
        search_query = request.GET.get('search', '')
        if search_query:
            word_list = word_list.filter(
                Q(word__english__icontains=search_query) |
                Q(word__korean__icontains=search_query)
            )
        
        # 정렬 기능
        sort_by = request.GET.get('sort', '-created_at')
        if sort_by == 'english':
            word_list = word_list.order_by('word__english')
        elif sort_by == '-english':
            word_list = word_list.order_by('-word__english')
        else:
            word_list = word_list.order_by(sort_by)
        
        # 페이지네이션
        paginator = Paginator(word_list, 20)
        page = request.GET.get('page')
        words = paginator.get_page(page)
        
        context = {
            'friend': friend,
            'words': words,
            'search_query': search_query,
            'sort_by': sort_by,
        }
        return render(request, 'friends/friend_vocabulary.html', context)
        
    except User.DoesNotExist:
        messages.error(request, '존재하지 않는 사용자입니다.')
        return redirect('friends:friend_list') 