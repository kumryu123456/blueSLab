# core/project_models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import uuid

class Project(models.Model):
    """사용자 프로젝트 모델"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('프로젝트 이름'), max_length=200)
    description = models.TextField(_('설명'), blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                             related_name='owned_projects', verbose_name=_('소유자'))
    
    # 프로젝트 설정
    is_public = models.BooleanField(_('공개 여부'), default=False)
    created_at = models.DateTimeField(_('생성일'), auto_now_add=True)
    updated_at = models.DateTimeField(_('수정일'), auto_now=True)
    
    # 제한 설정
    max_tasks = models.IntegerField(_('최대 작업 수'), default=1000)
    storage_limit_mb = models.IntegerField(_('저장 공간 제한 (MB)'), default=1000)
    
    class Meta:
        verbose_name = _('프로젝트')
        verbose_name_plural = _('프로젝트 목록')
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.name} ({self.owner.get_display_name()}님의 BlueAI)"
    
    def get_members_count(self):
        """프로젝트 멤버 수 반환"""
        return self.members.count() + 1  # 소유자 포함
    
    def get_tasks_count(self):
        """프로젝트 작업 수 반환"""
        return self.tasks.count()
    
    def get_used_storage_mb(self):
        """사용 중인 저장 공간 크기 반환 (MB)"""
        # 실제 구현에서는 파일 크기 계산 로직 필요
        return 0

class ProjectMember(models.Model):
    """프로젝트 멤버 및 권한 모델"""
    ROLE_CHOICES = [
        ('host', _('소유자')),
        ('admin', _('관리자')),
        ('editor', _('편집자')),
        ('viewer', _('뷰어')),
        ('guest', _('게스트')),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, 
                               related_name='members', verbose_name=_('프로젝트'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                            related_name='project_memberships', verbose_name=_('사용자'))
    role = models.CharField(_('역할'), max_length=20, choices=ROLE_CHOICES, default='guest')
    
    # 초대 및 참여 정보
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                  null=True, blank=True, related_name='sent_invitations',
                                  verbose_name=_('초대자'))
    invited_at = models.DateTimeField(_('초대일'), auto_now_add=True)
    joined_at = models.DateTimeField(_('참여일'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('프로젝트 멤버')
        verbose_name_plural = _('프로젝트 멤버 목록')
        unique_together = [['project', 'user']]
    
    def __str__(self):
        return f"{self.user.get_display_name()} - {self.project.name} ({self.get_role_display()})"
    
    def has_permission(self, permission_type):
        """권한 확인"""
        permission_hierarchy = {
            'view': ['host', 'admin', 'editor', 'viewer', 'guest'],
            'edit': ['host', 'admin', 'editor'],
            'manage': ['host', 'admin'],
            'owner': ['host'],
        }
        return self.role in permission_hierarchy.get(permission_type, [])

# 기존 Task 모델과 연결
from .models import Task

class ProjectTask(models.Model):
    """프로젝트와 작업 연결 모델"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['project', 'task']]
        verbose_name = _('프로젝트 작업')
        verbose_name_plural = _('프로젝트 작업 목록')
    
    def __str__(self):
        return f"{self.project.name} - {self.task.title}"