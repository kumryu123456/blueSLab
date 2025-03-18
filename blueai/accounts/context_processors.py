#accounts/context_processors.py
def user_info(request):
    """사용자 정보를 템플릿에 전달하는 컨텍스트 프로세서"""
    context = {
        'isAuthenticated': request.user.is_authenticated,
    }
    
    if request.user.is_authenticated:
        # 사용자 이름 처리
        display_name = request.user.get_display_name() if hasattr(request.user, 'get_display_name') else request.user.username
        
        # 이니셜 계산 (첫 글자)
        initial = display_name[0].upper() if display_name else '?'
        
        context.update({
            'userDisplayName': display_name,
            'userInitial': initial,
            'userPlan': request.user.plan if hasattr(request.user, 'plan') else 'free',
        })
        
        # 프로필 정보 추가 (있는 경우)
        try:
            from accounts.models import UserProfile
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            context['userProfile'] = profile
        except Exception:
            pass
    
    return context