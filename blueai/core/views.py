# core/views.py의 기존 함수를 확장하여 사용자 관리 시스템 지원

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json
from datetime import datetime
from django.utils import timezone

from .models import Task, Favorite
from .project_models import Project, ProjectTask

@ensure_csrf_cookie
def index(request):
    """메인 페이지 렌더링"""
    context = {}
    
    # 로그인한 사용자인 경우 프로젝트 정보 추가
    if request.user.is_authenticated:
        from core.project_models import Project
        
        # 현재 프로젝트 정보 (ProjectMiddleware에서 설정됨)
        if hasattr(request, 'current_project') and request.current_project:
            context['current_project'] = request.current_project
        
        # 사용자의 프로젝트 목록
        context['current_user_projects'] = Project.objects.filter(owner=request.user)
        context['shared_projects'] = Project.objects.filter(members__user=request.user)
    
    return render(request, 'core/index.html', context)

@require_http_methods(["POST"])
def process_input(request):
    """사용자 입력을 처리하고 작업 단계 생성"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        data = json.loads(request.body)
        user_input = data.get("user_input")
        
        if not user_input:
            logger.warning("Empty user input received")
            return JsonResponse({"error": "사용자 입력이 없습니다."}, status=400)
        
        # 로그인 여부에 따라 사용자 정보 설정
        current_user = request.user if request.user.is_authenticated else None
        user_display = request.user.username if request.user.is_authenticated else "Guest"
        
        logger.debug(f"Processing input: '{user_input}' for user: {user_display}")
        
        # 명령어 분석하여 프로세스 단계 생성
        if "나라장터" in user_input:
            process = ["나라장터 접속", "RPA 공고명 입력 및 검색", "상위 5개 공고 크롤링", "엑셀 파일 저장"]
            title = "나라장터 공고 검색"
        elif "뉴스" in user_input and "요약" in user_input:
            process = ["뉴스 사이트 접속", "최신 뉴스 스크래핑", "내용 요약", "관련 음악 추천"]
            title = "뉴스 요약 및 음악 추천"
        elif "웹사이트" in user_input and "생성" in user_input:
            process = ["디자인 템플릿 선택", "콘텐츠 구성", "반응형 레이아웃 적용", "결과물 생성"]
            title = "웹사이트 생성"
        elif "날씨" in user_input:
            process = ["날씨 정보 검색", "데이터 수집", "이미지 생성", "저장"]
            title = "날씨 정보 이미지화"
        else:
            process = ["웹사이트 접속", "데이터 수집", "결과 정리"]
            title = "자동화 작업"
        
        # 초기 대화 기록 추가
        conversation = []
        timestamp = timezone.now().strftime("%H:%M")
        
        conversation.append({
            "type": "user",
            "content": user_input,
            "timestamp": timestamp
        })
        
        conversation.append({
            "type": "assistant",
            "content": "작업을 실행할 준비가 되었습니다. 위의 단계를 확인하시고, 계속하시려면 '계속하기' 버튼을 클릭하세요.",
            "timestamp": timestamp
        })
        
        # 새 작업 생성 (로그인된 경우에만 소유자 정보 추가)
        try:
            task = Task(
                title=title,
                user_input=user_input,
                process=", ".join(process),
                owner=current_user,  # 비로그인 시 None으로 설정
                is_public=True,  # 비로그인 사용자 작업은 항상 공개로 설정
            )
            task.conversation = json.dumps(conversation)
            task.save()
            logger.debug(f"Task created successfully: {task.id}")
            
            # 현재 프로젝트가 있고 로그인한 경우 작업을 프로젝트에 연결
            if hasattr(request, 'current_project') and request.current_project and current_user:
                ProjectTask.objects.create(
                    project=request.current_project,
                    task=task
                )
                logger.debug(f"Task connected to project: {request.current_project.id}")
            else:
                logger.debug("No current project available for task connection")
            
            return JsonResponse({
                "process": process, 
                "title": title, 
                "id": task.id
            })
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}", exc_info=True)
            return JsonResponse({"error": f"작업 생성 중 오류가 발생했습니다: {str(e)}"}, status=500)
            
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return JsonResponse({"error": "잘못된 요청 형식입니다."}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in process_input: {str(e)}", exc_info=True)
        return JsonResponse({"error": f"예상치 못한 오류가 발생했습니다: {str(e)}"}, status=500)

@require_http_methods(["GET"])
def get_task(request, task_id):
    """특정 작업 상세 정보 불러오기 (권한 확인)"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.debug(f"Fetching task {task_id} for user {request.user}")
        task = get_object_or_404(Task, id=task_id)
        
        # 권한 확인
        if not task.can_user_view(request.user):
            logger.warning(f"User {request.user} attempted to access task {task_id} without permission")
            return JsonResponse({"error": "이 작업을 볼 수 있는 권한이 없습니다."}, status=403)
        
        # 즐겨찾기 상태 확인
        is_favorite = False
        if request.user.is_authenticated:
            is_favorite = Favorite.objects.filter(task=task, user=request.user).exists()
        
        # 응답 데이터 구성
        task_data = {
            "id": task.id,
            "title": task.title,
            "user_input": task.user_input,
            "process": task.get_process_list(),
            "conversation": task.get_conversation(),
            "created_at": task.created_at.isoformat(),
            "completed": task.completed,
            "result": task.result or "",
            # 추가 정보
            "owner": task.owner.get_display_name() if task.owner else "알 수 없음",
            "is_public": task.is_public,
            "can_edit": task.can_user_edit(request.user) if request.user.is_authenticated else False,
            "is_favorite": is_favorite,
            # 연결된 프로젝트 정보
            "projects": [
                {
                    "id": pt.project.id,
                    "name": pt.project.name,
                    "owner": pt.project.owner.get_display_name()
                } 
                for pt in task.projects.select_related('project__owner').all()
            ]
        }
        
        # 접근 로그 기록
        logger.info(f"Task {task_id} accessed by user {request.user}")
        
        return JsonResponse(task_data)
    
    except Task.DoesNotExist:
        logger.warning(f"Task {task_id} not found")
        return JsonResponse({"error": "해당 작업을 찾을 수 없습니다."}, status=404)
    except Exception as e:
        logger.error(f"Error loading task {task_id}: {str(e)}", exc_info=True)
        return JsonResponse({"error": f"작업을 불러오는데 실패했습니다: {str(e)}"}, status=500)

@require_http_methods(["GET"])
def get_task(request, task_id):
    """특정 작업 상세 정보 불러오기 (권한 확인)"""
    task = get_object_or_404(Task, id=task_id)
    
    # 권한 확인
    if not task.can_user_view(request.user):
        return JsonResponse({"error": "이 작업을 볼 수 있는 권한이 없습니다."}, status=403)
    
    # 즐겨찾기 상태 확인
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(task=task, user=request.user).exists()
    
    task_data = {
        "id": task.id,
        "title": task.title,
        "user_input": task.user_input,
        "process": task.get_process_list(),
        "conversation": task.get_conversation(),
        "created_at": task.created_at.isoformat(),
        "completed": task.completed,
        "result": task.result or "",
        # 추가 정보
        "owner": task.owner.get_display_name() if task.owner else "알 수 없음",
        "is_public": task.is_public,
        "can_edit": task.can_user_edit(request.user) if request.user.is_authenticated else False,
        "is_favorite": is_favorite,
        # 연결된 프로젝트 정보
        "projects": [
            {
                "id": pt.project.id,
                "name": pt.project.name,
                "owner": pt.project.owner.get_display_name()
            } 
            for pt in task.projects.select_related('project__owner').all()
        ]
    }
    
    return JsonResponse(task_data)

@require_http_methods(["GET"])
def get_tasks(request):
    """저장된 모든 작업 불러오기 (사용자별 필터링)"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.debug(f"Fetching tasks for user: {request.user}")
        
        if request.user.is_authenticated:
            # 현재 프로젝트가 있으면 해당 프로젝트의 작업만 표시
            if hasattr(request, 'current_project') and request.current_project:
                project_tasks = ProjectTask.objects.filter(project=request.current_project).select_related('task')
                tasks = [pt.task for pt in project_tasks]
                logger.debug(f"Fetched {len(tasks)} tasks for project: {request.current_project.id}")
            else:
                # 소유한 작업과 공유받은 작업 표시
                from django.db.models import Q
                tasks = Task.objects.filter(
                    Q(owner=request.user) | 
                    Q(shared_with=request.user) |
                    Q(is_public=True)
                ).distinct()
                logger.debug(f"Fetched {len(tasks)} tasks for user: {request.user.username}")
        else:
            # 비로그인 사용자는 공개 작업만 볼 수 있음
            tasks = Task.objects.filter(is_public=True)
            logger.debug(f"Fetched {len(tasks)} public tasks for anonymous user")
        
        # 최대 10개 작업만 표시
        tasks = tasks[:10]
        
        task_list = [
            {
                "id": task.id,
                "title": task.title,
                "user_input": task.user_input,
                "process": task.get_process_list(),
                "conversation": task.get_conversation(),
                "created_at": task.created_at.isoformat(),
                "completed": task.completed,
                # 추가 정보
                "owner": task.owner.get_display_name() if task.owner else "알 수 없음",
                "is_public": task.is_public,
                "can_edit": task.can_user_edit(request.user) if request.user.is_authenticated else False,
                "is_favorite": Favorite.objects.filter(task=task, user=request.user).exists() if request.user.is_authenticated else False,
            }
            for task in tasks
        ]
        
        return JsonResponse(task_list, safe=False)
    except Exception as e:
        logger.error(f"Error fetching tasks: {str(e)}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def update_conversation(request):
    """대화 기록 업데이트 (권한 확인)"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        data = json.loads(request.body)
        task_id = data.get("task_id")
        conversation = data.get("conversation")
        
        if not task_id or not conversation:
            logger.warning(f"Invalid request: missing task_id or conversation")
            return JsonResponse({"error": "유효하지 않은 요청입니다."}, status=400)
        
        logger.debug(f"Updating conversation for task {task_id}")
        task = get_object_or_404(Task, id=task_id)
        
        # 권한 확인
        if not task.can_user_edit(request.user):
            logger.warning(f"User {request.user} attempted to update task {task_id} without permission")
            return JsonResponse({"error": "이 작업을 수정할 권한이 없습니다."}, status=403)
        
        # 대화 기록 검증
        if not isinstance(conversation, list):
            logger.warning(f"Invalid conversation format: {type(conversation)}")
            return JsonResponse({"error": "대화 기록은 리스트 형식이어야 합니다."}, status=400)
        
        # 대화 기록 업데이트
        task.set_conversation(conversation)
        task.save(update_fields=['conversation'])
        
        logger.info(f"Conversation updated for task {task_id} by user {request.user}")
        
        return JsonResponse({
            "status": "success", 
            "message": "대화 기록이 업데이트되었습니다.",
            "conversation_count": len(conversation)
        })
    except Task.DoesNotExist:
        logger.warning(f"Task {data.get('task_id')} not found")
        return JsonResponse({"error": "해당 작업을 찾을 수 없습니다."}, status=404)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return JsonResponse({"error": "잘못된 요청 형식입니다."}, status=400)
    except Exception as e:
        logger.error(f"Error updating conversation: {str(e)}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def execute_task(request):
    """작업 실행 결과 저장 (권한 확인)"""
    try:
        data = json.loads(request.body)
        task_id = data.get("task_id")
        steps = data.get("steps")
        
        if not task_id or not steps:
            return JsonResponse({"error": "유효하지 않은 요청입니다."}, status=400)
        
        task = get_object_or_404(Task, id=task_id)
        
        # 권한 확인
        if not task.can_user_edit(request.user):
            return JsonResponse({"error": "이 작업을 실행할 권한이 없습니다."}, status=403)
        
        task.set_process_list(steps)
        task.completed = True
        task.save()
        
        return JsonResponse({"status": "success", "message": "작업이 성공적으로 실행되었습니다."})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@login_required
@require_http_methods(["DELETE"])
def delete_task(request, task_id):
    """작업 삭제 (권한 확인)"""
    try:
        task = get_object_or_404(Task, id=task_id)
        
        # 권한 확인 (소유자만 삭제 가능)
        if task.owner != request.user:
            return JsonResponse({"error": "이 작업을 삭제할 권한이 없습니다."}, status=403)
        
        task.delete()
        
        return JsonResponse({"status": "success", "message": "작업이 삭제되었습니다."})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def update_task_title(request):
    """작업 제목 업데이트 (권한 확인)"""
    try:
        data = json.loads(request.body)
        task_id = data.get("task_id")
        new_title = data.get("title")
        
        if not task_id or not new_title:
            return JsonResponse({"error": "유효하지 않은 요청입니다."}, status=400)
        
        task = get_object_or_404(Task, id=task_id)
        
        # 권한 확인
        if not task.can_user_edit(request.user):
            return JsonResponse({"error": "이 작업을 수정할 권한이 없습니다."}, status=403)
        
        task.title = new_title
        task.save()
        
        return JsonResponse({"status": "success", "message": "작업 제목이 업데이트되었습니다."})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def toggle_favorite(request, task_id):
    """즐겨찾기 토글 (사용자별 관리)"""
    try:
        task = get_object_or_404(Task, id=task_id)
        
        # 권한 확인
        if not task.can_user_view(request.user):
            return JsonResponse({"error": "이 작업을 즐겨찾기할 권한이 없습니다."}, status=403)
        
        favorite, created = Favorite.objects.get_or_create(
            task=task,
            user=request.user
        )
        
        if not created:
            # 이미 존재하면 삭제 (즐겨찾기 해제)
            favorite.delete()
            is_favorite = False
            message = "즐겨찾기가 해제되었습니다."
        else:
            is_favorite = True
            message = "즐겨찾기에 추가되었습니다."
        
        return JsonResponse({
            "status": "success",
            "is_favorite": is_favorite,
            "message": message
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@login_required
@require_http_methods(["GET"])
def get_favorites(request):
    """사용자의 즐겨찾기 목록 조회"""
    favorites = Favorite.objects.filter(user=request.user).select_related('task')
    
    favorite_list = [
        {
            "id": favorite.task.id,
            "title": favorite.task.title,
            "created_at": favorite.task.created_at.isoformat()
        }
        for favorite in favorites
    ]
    
    return JsonResponse(favorite_list, safe=False)

@login_required
@require_http_methods(["POST"])
def share_task(request, task_id):
    """작업 공유 설정"""
    try:
        task = get_object_or_404(Task, id=task_id)
        
        # 권한 확인 (소유자만 공유 설정 가능)
        if task.owner != request.user:
            return JsonResponse({"error": "이 작업을 공유할 권한이 없습니다."}, status=403)
        
        data = json.loads(request.body)
        is_public = data.get("is_public", False)
        share_with = data.get("share_with", [])
        
        # 공개 여부 설정
        task.is_public = is_public
        
        # 특정 사용자에게 공유
        if share_with:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            # 기존 공유 대상 초기화
            task.shared_with.clear()
            
            # 새 공유 대상 추가
            for username in share_with:
                try:
                    user = User.objects.get(username=username)
                    task.shared_with.add(user)
                except User.DoesNotExist:
                    pass
        
        task.save()
        
        return JsonResponse({
            "status": "success",
            "message": "작업 공유 설정이 업데이트되었습니다.",
            "is_public": task.is_public,
            "shared_with": list(task.shared_with.values_list('username', flat=True))
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def add_task_to_project(request, task_id):
    """작업을 프로젝트에 추가"""
    try:
        task = get_object_or_404(Task, id=task_id)
        
        # 권한 확인
        if not task.can_user_edit(request.user):
            return JsonResponse({"error": "이 작업을 프로젝트에 추가할 권한이 없습니다."}, status=403)
        
        data = json.loads(request.body)
        project_id = data.get("project_id")
        
        if not project_id:
            return JsonResponse({"error": "프로젝트 ID가 필요합니다."}, status=400)
        
        project = get_object_or_404(Project, id=project_id)
        
        # 프로젝트 권한 확인
        if project.owner != request.user and not project.members.filter(user=request.user, role__in=['host', 'admin', 'editor']).exists():
            return JsonResponse({"error": "이 프로젝트에 작업을 추가할 권한이 없습니다."}, status=403)
        
        # 이미 추가되어 있는지 확인
        if ProjectTask.objects.filter(project=project, task=task).exists():
            return JsonResponse({"error": "이미 프로젝트에 추가된 작업입니다."}, status=400)
        
        # 작업 추가
        ProjectTask.objects.create(project=project, task=task)
        
        return JsonResponse({
            "status": "success",
            "message": f"작업이 '{project.name}' 프로젝트에 추가되었습니다.",
            "project": {
                "id": str(project.id),
                "name": project.name
            }
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)