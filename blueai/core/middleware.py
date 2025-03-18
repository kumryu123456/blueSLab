# core/middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import get_object_or_404
from core.project_models import Project
import logging


# logger 초기화
logger = logging.getLogger(__name__)

class ProjectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 로그인한 사용자인 경우 현재 프로젝트 설정
        if request.user.is_authenticated:
            try:
                # 세션에서 현재 프로젝트 ID 가져오기
                project_id = request.session.get('current_project_id')
                
                if project_id:
                    from core.project_models import Project, ProjectMember
                    
                    # 프로젝트 접근 권한 확인
                    project = Project.objects.get(id=project_id)
                    
                    # 소유자이거나 멤버인 경우에만 설정
                    if project.owner == request.user or ProjectMember.objects.filter(
                            project=project, user=request.user).exists():
                        request.current_project = project
                        logger.debug(f"Current project set to {project.name} for user {request.user.username}")
                    else:
                        # 권한이 없는 경우 세션에서 제거
                        logger.warning(f"User {request.user.username} has no access to project {project_id}")
                        del request.session['current_project_id']
                        request.current_project = None
                else:
                    # 프로젝트 ID가 없으면 사용자의 첫 번째 프로젝트로 설정 (있는 경우)
                    from core.project_models import Project
                    
                    default_project = Project.objects.filter(owner=request.user).first()
                    if default_project:
                        request.session['current_project_id'] = str(default_project.id)
                        request.current_project = default_project
                        logger.debug(f"Default project set to {default_project.name} for user {request.user.username}")
                    else:
                        logger.debug(f"No default project found for user {request.user.username}")
                        request.current_project = None
            except Exception as e:
                # 오류 발생 시 현재 프로젝트 초기화
                logger.error(f"Error setting current project: {str(e)}")
                request.current_project = None
                if 'current_project_id' in request.session:
                    del request.session['current_project_id']
        else:
            request.current_project = None

        response = self.get_response(request)
        return response