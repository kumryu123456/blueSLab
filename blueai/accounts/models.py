# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid

class User(AbstractUser):
    """확장된 사용자 모델"""
    # 기본 사용자 식별자 필드
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # 프로필 정보
    display_name = models.CharField(_('표시 이름'), max_length=50, blank=True)
    profile_image = models.ImageField(_('프로필 이미지'), upload_to='profile_images/', blank=True, null=True)
    bio = models.TextField(_('자기소개'), blank=True)
    
    # 서비스 이용 정보
    PLAN_CHOICES = [
        ('free', _('무료 요금제')),
        ('pro', _('프로 요금제')),
        ('team', _('팀 요금제')),
        ('enterprise', _('기업 요금제')),
    ]
    plan = models.CharField(_('요금제'), max_length=20, choices=PLAN_CHOICES, default='free')
    plan_start_date = models.DateTimeField(_('요금제 시작일'), null=True, blank=True)
    plan_end_date = models.DateTimeField(_('요금제 종료일'), null=True, blank=True)
    
    # 추가 설정
    is_email_verified = models.BooleanField(_('이메일 인증 여부'), default=False)
    last_activity = models.DateTimeField(_('마지막 활동'), default=timezone.now)
    
    # 알림 설정
    email_notifications = models.BooleanField(_('이메일 알림'), default=True)
    
    class Meta:
        verbose_name = _('사용자')
        verbose_name_plural = _('사용자 목록')
    
    def __str__(self):
        return self.get_full_name() or self.username
    
    def get_display_name(self):
        """사용자 표시 이름 반환"""
        if self.display_name:
            return self.display_name
        elif self.get_full_name():
            return self.get_full_name()
        return self.username
    
    def get_initial(self):
        """사용자 이니셜 반환 (KKM 등)"""
        if self.get_full_name():
            names = self.get_full_name().split()
            return ''.join([name[0] for name in names if name])
        return self.username[:2].upper()
    
    def get_plan_display_name(self):
        """요금제 표시 이름 반환"""
        return dict(self.PLAN_CHOICES).get(self.plan, '무료 요금제')
    
    def is_plan_active(self):
        """요금제 활성화 여부 확인"""
        if self.plan == 'free':
            return True
        if not self.plan_end_date:
            return False
        return timezone.now() < self.plan_end_date
    
    @property
    def is_pro(self):
        """프로 요금제 이상 여부 확인"""
        return self.plan in ['pro', 'team', 'enterprise'] and self.is_plan_active()

class UserProfile(models.Model):
    """사용자 프로필 추가 정보"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # 추가 개인 정보
    phone = models.CharField(_('전화번호'), max_length=20, blank=True)
    organization = models.CharField(_('조직'), max_length=100, blank=True)
    position = models.CharField(_('직책'), max_length=100, blank=True)
    
    # UI/UX 설정
    theme_preference = models.CharField(_('테마 설정'), max_length=20, default='system',
                                     choices=[('light', '라이트'), ('dark', '다크'), ('system', '시스템 설정')])
    language_preference = models.CharField(_('언어 설정'), max_length=10, default='ko',
                                        choices=[('ko', '한국어'), ('en', '영어'), ('ja', '일본어'),
                                               ('zh', '중국어'), ('fr', '프랑스어'), ('pt', '포르투갈어')])
    
    # API 관련 정보
    api_key = models.CharField(_('API 키'), max_length=64, blank=True, null=True)
    api_usage_count = models.IntegerField(_('API 사용 횟수'), default=0)
    api_last_used = models.DateTimeField(_('API 마지막 사용일'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('사용자 프로필')
        verbose_name_plural = _('사용자 프로필 목록')
    
    def __str__(self):
        return f"{self.user.username}의 프로필"
    
    def generate_api_key(self):
        """새 API 키 생성"""
        import secrets
        self.api_key = secrets.token_hex(32)
        self.save()
        return self.api_key