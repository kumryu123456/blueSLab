# accounts/backends.py
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from accounts.models import User

User = get_user_model()

class EmailBackend(ModelBackend):
    """
    이메일로 인증하는 백엔드
    사용자가 이메일을 사용해 로그인할 수 있도록 함
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # 이메일 또는 사용자 이름으로 사용자 찾기
            user = User.objects.get(Q(username=username) | Q(email=username))
            
            # 비밀번호 검증
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None
        
        return None