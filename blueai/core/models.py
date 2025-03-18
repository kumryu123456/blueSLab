# core/models.py (기존 코드 업데이트)
from django.db import models
import json
from django.utils import timezone
from django.conf import settings

class Task(models.Model):
    """작업 정보를 저장하는 모델"""
    title = models.CharField(max_length=200, verbose_name="제목")
    user_input = models.TextField(verbose_name="사용자 입력")
    process = models.TextField(verbose_name="처리 단계")  # 쉼표로 구분된 단계
    conversation = models.TextField(verbose_name="대화 기록")  # JSON 문자열
    created_at = models.DateTimeField(default=timezone.now, verbose_name="생성 시간")
    completed = models.BooleanField(default=False, verbose_name="완료 여부")
    result = models.TextField(blank=True, null=True, verbose_name="결과")
    
    # 사용자 관리 시스템 통합을 위한 필드 추가
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='owned_tasks',
        verbose_name="소유자",
        null=True,  # 기존 데이터 호환성 유지
    )
    is_public = models.BooleanField(default=False, verbose_name="공개 여부")
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='shared_tasks',
        verbose_name="공유 대상",
        blank=True
    )
    
    class Meta:
        verbose_name = "작업"
        verbose_name_plural = "작업 목록"
        ordering = ['-created_at']  # 최신 작업이 먼저 나오도록
    
    def __str__(self):
        return self.title
    
    def get_process_list(self):
        """처리 단계 문자열을 리스트로 변환"""
        return self.process.split(", ")
    
    def set_process_list(self, process_list):
        """처리 단계 리스트를 문자열로 변환"""
        self.process = ", ".join(process_list)
    
    def get_conversation(self):
        """JSON 대화 기록을 Python 객체로 변환"""
        try:
            return json.loads(self.conversation) if self.conversation else []
        except json.JSONDecodeError:
            return []
    
    def set_conversation(self, conversation_list):
        """Python 객체를 JSON 대화 기록으로 변환"""
        self.conversation = json.dumps(conversation_list)
    
    def add_message(self, message_type, content):
        """대화 기록에 새 메시지 추가"""
        conversation = self.get_conversation()
        timestamp = timezone.now().strftime("%H:%M")
        
        message = {
            "type": message_type,
            "content": content,
            "timestamp": timestamp
        }
        
        conversation.append(message)
        self.set_conversation(conversation)
        return conversation
    
    def can_user_view(self, user):
        """사용자가 작업을 볼 수 있는지 확인"""
        if not user.is_authenticated:
            return self.is_public
        
        # 소유자이거나 공유 대상이면 볼 수 있음
        return (
            self.is_public or 
            self.owner == user or 
            self.shared_with.filter(id=user.id).exists() or
            # 프로젝트를 통한 접근 권한 확인
            self.projects.filter(models.Q(project__owner=user) | models.Q(project__members__user=user)).exists()
        )
    
    def can_user_edit(self, user):
        """사용자가 작업을 수정할 수 있는지 확인"""
        if not user.is_authenticated:
            return False
        
        # 소유자이거나 프로젝트 편집 권한이 있으면 수정 가능
        is_project_editor = self.projects.filter(
            models.Q(project__owner=user) | 
            models.Q(project__members__user=user, project__members__role__in=['host', 'admin', 'editor'])
        ).exists()
        
        return self.owner == user or is_project_editor

class Favorite(models.Model):
    """즐겨찾기를 관리하는 모델"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='favorites', verbose_name="작업")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # 사용자 모델 추가
        on_delete=models.CASCADE,
        related_name='favorite_tasks',
        verbose_name="사용자"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성 시간")
    
    class Meta:
        verbose_name = "즐겨찾기"
        verbose_name_plural = "즐겨찾기 목록"
        ordering = ['-created_at']
        unique_together = ['task', 'user']  # 동일한 작업을 중복 즐겨찾기 방지
    
    def __str__(self):
        return f"즐겨찾기: {self.task.title} (by {self.user.username})"