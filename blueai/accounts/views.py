# accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.conf import settings
import json

from .models import User, UserProfile
from .forms import (
    CustomUserCreationForm, 
    CustomUserChangeForm, 
    CustomAuthenticationForm,
    ProfileUpdateForm,
    PasswordResetForm,
    PasswordChangeForm
)
from core.project_models import Project, ProjectMember

def register_view(request):
    """회원가입 뷰"""
    if request.user.is_authenticated:
        return redirect('core:index')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True  # 이메일 인증을 사용할 경우 False로 설정
            user.save()
            
            # 사용자 프로필 생성
            UserProfile.objects.create(user=user)
            
            # 첫 프로젝트 자동 생성
            project = Project.objects.create(
                name=f"{user.get_display_name()}님의 BlueAI",
                owner=user
            )
            
            # 방법 1: 사용자 인증을 통해 백엔드 설정
            authenticated_user = authenticate(request, 
                                             username=form.cleaned_data['username'], 
                                             password=form.cleaned_data['password1'])
            login(request, authenticated_user)
            
            # 또는 방법 2: 백엔드를 명시적으로 지정
            # user.backend = 'django.contrib.auth.backends.ModelBackend'
            # login(request, user)
            
            messages.success(request, '회원가입이 완료되었습니다. 환영합니다!')
            return redirect('core:index')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    """로그인 뷰"""
    import logging
    logger = logging.getLogger(__name__)
    logger.debug("Login view accessed")
    
    if request.user.is_authenticated:
        logger.debug(f"User already authenticated: {request.user.username}")
        return redirect('core:index')
    
    if request.method == 'POST':
        logger.debug(f"POST request received with data: {request.POST}")
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            logger.debug("Form is valid")
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                logger.debug(f"User authenticated: {username}")
                login(request, user)
                
                # 마지막 활동 시간 업데이트
                user.last_activity = timezone.now()
                user.save(update_fields=['last_activity'])
                
                # 요청 경로가 있으면 해당 페이지로 리디렉션
                next_url = request.GET.get('next', 'core:index')
                logger.debug(f"Redirecting to: {next_url}")
                return redirect(next_url)
            else:
                logger.debug(f"Authentication failed for username: {username}")
                messages.error(request, '로그인에 실패했습니다. 사용자 이름과 비밀번호를 확인해주세요.')
        else:
            logger.debug(f"Form errors: {form.errors}")
            messages.error(request, '로그인에 실패했습니다. 입력한 정보를 확인해주세요.')
    else:
        logger.debug("GET request received")
        form = CustomAuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def logout_view(request):
    """로그아웃 뷰"""
    import logging
    logger = logging.getLogger(__name__)
    
    # 로그아웃 전 사용자 정보 저장
    username = request.user.username
    
    # 세션에서 현재 프로젝트 ID 제거
    if 'current_project_id' in request.session:
        del request.session['current_project_id']
    
    # 로그아웃 처리
    logout(request)
    
    # 로깅
    logger.info(f"User {username} logged out")
    
    # 성공 메시지
    messages.success(request, '로그아웃되었습니다.')
    
    return redirect('accounts:login')

@login_required
def profile_view(request):
    """사용자 프로필 뷰"""
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    owned_projects = Project.objects.filter(owner=user)
    member_projects = Project.objects.filter(members__user=user)
    
    context = {
        'user': user,
        'profile': profile,
        'owned_projects': owned_projects,
        'member_projects': member_projects,
    }
    
    return render(request, 'accounts/profile.html', context)

@login_required
def profile_update_view(request):
    """프로필 업데이트 뷰"""
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            
            # 프로필 필드 업데이트
            profile.phone = request.POST.get('phone', '')
            profile.organization = request.POST.get('organization', '')
            profile.position = request.POST.get('position', '')
            profile.theme_preference = request.POST.get('theme_preference', 'system')
            profile.language_preference = request.POST.get('language_preference', 'ko')
            profile.save()
            
            messages.success(request, '프로필이 업데이트되었습니다.')
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=user)
    
    return render(request, 'accounts/profile_update.html', {'form': form, 'profile': profile})

@login_required
def password_change_view(request):
    """비밀번호 변경 뷰"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, '비밀번호가 변경되었습니다.')
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/password_change.html', {'form': form})

def password_reset_request_view(request):
    """비밀번호 재설정 요청 뷰"""
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                
                # 비밀번호 재설정 토큰 생성
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                current_site = get_current_site(request)
                
                # 이메일 준비
                mail_subject = '[BlueAI] 비밀번호 재설정 요청'
                message = render_to_string('accounts/password_reset_email.html', {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': uid,
                    'token': token,
                    'protocol': 'https' if request.is_secure() else 'http',
                })
                
                # 이메일 발송
                email_message = EmailMultiAlternatives(mail_subject, message, settings.DEFAULT_FROM_EMAIL, [email])
                email_message.content_subtype = 'html'
                email_message.send()
                
                messages.success(request, '비밀번호 재설정 링크가 이메일로 발송되었습니다.')
                return redirect('accounts:login')
            except User.DoesNotExist:
                messages.error(request, '해당 이메일로 등록된 사용자가 없습니다.')
    else:
        form = PasswordResetForm()
    
    return render(request, 'accounts/password_reset_request.html', {'form': form})

def password_reset_confirm_view(request, uidb64, token):
    """비밀번호 재설정 확인 뷰"""
    try:
        # UID 디코딩
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    # 토큰 검증
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = PasswordResetForm(request.POST)
            if form.is_valid():
                new_password = form.cleaned_data['new_password1']
                user.set_password(new_password)
                user.save()
                messages.success(request, '비밀번호가 성공적으로 재설정되었습니다. 새 비밀번호로 로그인하세요.')
                return redirect('accounts:login')
        else:
            form = PasswordResetForm()
        return render(request, 'accounts/password_reset_confirm.html', {'form': form})
    else:
        messages.error(request, '비밀번호 재설정 링크가 유효하지 않습니다.')
        return redirect('accounts:password_reset_request')

@login_required
def project_list_view(request):
    """사용자 프로젝트 목록 뷰"""
    user = request.user
    owned_projects = Project.objects.filter(owner=user)
    member_projects = Project.objects.filter(members__user=user)
    
    context = {
        'owned_projects': owned_projects,
        'member_projects': member_projects,
    }
    
    return render(request, 'accounts/projects.html', context)

@login_required
def project_create_view(request):
    """새 프로젝트 생성 뷰"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not name:
            messages.error(request, '프로젝트 이름을 입력해주세요.')
            return redirect('accounts:project_create')
        
        project = Project.objects.create(
            name=name,
            description=description,
            owner=request.user
        )
        
        messages.success(request, f'"{name}" 프로젝트가 생성되었습니다.')
        return redirect('accounts:project_list')
    
    return render(request, 'accounts/project_create.html')

@login_required
def project_detail_view(request, project_id):
    """프로젝트 상세 뷰"""
    project = get_object_or_404(Project, id=project_id)
    
    # 권한 검증
    if project.owner != request.user and not ProjectMember.objects.filter(project=project, user=request.user).exists():
        messages.error(request, '해당 프로젝트에 접근할 권한이 없습니다.')
        return redirect('accounts:project_list')
    
    members = ProjectMember.objects.filter(project=project)
    
    context = {
        'project': project,
        'members': members,
        'is_owner': project.owner == request.user,
    }
    
    return render(request, 'accounts/project_detail.html', context)

@login_required
@require_http_methods(["POST"])
def project_invite_view(request, project_id):
    """프로젝트 초대 뷰 (AJAX)"""
    project = get_object_or_404(Project, id=project_id)
    
    # 권한 검증
    if project.owner != request.user and not ProjectMember.objects.filter(
            project=project, user=request.user, role__in=['host', 'admin']).exists():
        return JsonResponse({'status': 'error', 'message': '초대 권한이 없습니다.'}, status=403)
    
    data = json.loads(request.body)
    email = data.get('email', '').strip()
    role = data.get('role', 'guest')
    
    if not email:
        return JsonResponse({'status': 'error', 'message': '이메일을 입력해주세요.'}, status=400)
    
    try:
        invited_user = User.objects.get(email=email)
        
        # 이미 멤버인지 확인
        if project.owner == invited_user:
            return JsonResponse({'status': 'error', 'message': '프로젝트 소유자입니다.'}, status=400)
        
        if ProjectMember.objects.filter(project=project, user=invited_user).exists():
            return JsonResponse({'status': 'error', 'message': '이미 프로젝트 멤버입니다.'}, status=400)
        
        # 초대 생성
        member = ProjectMember.objects.create(
            project=project,
            user=invited_user,
            role=role,
            invited_by=request.user,
            joined_at=timezone.now()  # 자동 승인 (실제 구현에서는 이메일 초대 프로세스 추가)
        )
        
        return JsonResponse({
            'status': 'success',
            'message': f'{invited_user.get_display_name()}님을 프로젝트에 초대했습니다.',
            'member': {
                'id': member.id,
                'name': invited_user.get_display_name(),
                'role': member.get_role_display(),
                'joined_at': member.joined_at.strftime('%Y-%m-%d %H:%M')
            }
        })
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '해당 이메일의 사용자가 없습니다.'}, status=404)

@login_required
@require_http_methods(["POST"])
def project_change_role_view(request, project_id, member_id):
    """멤버 역할 변경 뷰 (AJAX)"""
    project = get_object_or_404(Project, id=project_id)
    member = get_object_or_404(ProjectMember, id=member_id, project=project)
    
    # 권한 검증
    if project.owner != request.user and not ProjectMember.objects.filter(
            project=project, user=request.user, role__in=['host', 'admin']).exists():
        return JsonResponse({'status': 'error', 'message': '권한 변경 권한이 없습니다.'}, status=403)
    
    data = json.loads(request.body)
    new_role = data.get('role', '').strip()
    
    if not new_role or new_role not in dict(ProjectMember.ROLE_CHOICES):
        return JsonResponse({'status': 'error', 'message': '유효하지 않은 역할입니다.'}, status=400)
    
    member.role = new_role
    member.save()
    
    return JsonResponse({
        'status': 'success',
        'message': f'{member.user.get_display_name()}님의 역할이 {member.get_role_display()}(으)로 변경되었습니다.'
    })

@login_required
@require_http_methods(["POST"])
def project_remove_member_view(request, project_id, member_id):
    """멤버 제거 뷰 (AJAX)"""
    project = get_object_or_404(Project, id=project_id)
    member = get_object_or_404(ProjectMember, id=member_id, project=project)
    
    # 권한 검증
    if project.owner != request.user and not ProjectMember.objects.filter(
            project=project, user=request.user, role__in=['host', 'admin']).exists():
        return JsonResponse({'status': 'error', 'message': '멤버 제거 권한이 없습니다.'}, status=403)
    
    member_name = member.user.get_display_name()
    member.delete()
    
    return JsonResponse({
        'status': 'success',
        'message': f'{member_name}님이 프로젝트에서 제거되었습니다.'
    })

@login_required
@require_http_methods(["POST"])
def switch_project_view(request):
    """프로젝트 전환 뷰 (AJAX)"""
    data = json.loads(request.body)
    project_id = data.get('project_id', '').strip()
    
    if not project_id:
        return JsonResponse({'status': 'error', 'message': '프로젝트 ID가 필요합니다.'}, status=400)
    
    project = get_object_or_404(Project, id=project_id)
    
    # 권한 검증
    if project.owner != request.user and not ProjectMember.objects.filter(project=project, user=request.user).exists():
        return JsonResponse({'status': 'error', 'message': '해당 프로젝트에 접근할 권한이 없습니다.'}, status=403)
    
    # 세션에 현재 프로젝트 ID 저장
    request.session['current_project_id'] = str(project.id)
    
    return JsonResponse({
        'status': 'success',
        'message': f'"{project.name}" 프로젝트로 전환되었습니다.',
        'project': {
            'id': str(project.id),
            'name': project.name,
            'owner_name': project.owner.get_display_name(),
            'role': 'host' if project.owner == request.user else ProjectMember.objects.get(project=project, user=request.user).role,
            'plan': project.owner.plan
        }
    })