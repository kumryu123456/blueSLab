# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from .models import User, UserProfile

class CustomUserCreationForm(UserCreationForm):
    """사용자 회원가입 폼"""
    email = forms.EmailField(
        label=_('이메일'),
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': '이메일 주소'})
    )
    first_name = forms.CharField(
        label=_('이름'),
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '이름'})
    )
    last_name = forms.CharField(
        label=_('성'),
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '성'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '사용자 아이디'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget = forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '비밀번호'
        })
        self.fields['password2'].widget = forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '비밀번호 확인'
        })
    
    def clean_email(self):
        """이메일 중복 검사"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError(_('이미 사용 중인 이메일입니다.'))
        return email

class CustomAuthenticationForm(AuthenticationForm):
    """로그인 폼"""
    username = forms.CharField(
        label=_('사용자 아이디 또는 이메일'),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '사용자 아이디 또는 이메일'})
    )
    password = forms.CharField(
        label=_('비밀번호'),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '비밀번호'})
    )
    
    def clean_username(self):
        """이메일로 로그인 지원"""
        username = self.cleaned_data.get('username')
        if '@' in username:
            try:
                user = User.objects.get(email=username)
                return user.username
            except User.DoesNotExist:
                pass
        return username

class CustomUserChangeForm(UserChangeForm):
    """사용자 정보 수정 폼"""
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'display_name', 'profile_image', 'bio')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'display_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 비밀번호 필드 제거 (별도 페이지에서 처리)
        if 'password' in self.fields:
            del self.fields['password']

class ProfileUpdateForm(forms.ModelForm):
    """프로필 정보 수정 폼"""
    class Meta:
        model = User
        fields = ('display_name', 'first_name', 'last_name', 'email', 'profile_image', 'bio')
        widgets = {
            'display_name': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    # 추가 필드 (UserProfile 모델용)
    phone = forms.CharField(
        label=_('전화번호'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    organization = forms.CharField(
        label=_('조직'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    position = forms.CharField(
        label=_('직책'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    theme_preference = forms.ChoiceField(
        label=_('테마 설정'),
        choices=[('light', '라이트'), ('dark', '다크'), ('system', '시스템 설정')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    language_preference = forms.ChoiceField(
        label=_('언어 설정'),
        choices=[('ko', '한국어'), ('en', '영어'), ('ja', '일본어'),
                ('zh', '중국어'), ('fr', '프랑스어'), ('pt', '포르투갈어')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class PasswordResetForm(forms.Form):
    """비밀번호 재설정 요청 폼"""
    email = forms.EmailField(
        label=_('이메일'),
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': '가입 시 사용한 이메일 주소'})
    )

class PasswordChangeForm(forms.Form):
    """비밀번호 변경 폼"""
    old_password = forms.CharField(
        label=_('현재 비밀번호'),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '현재 비밀번호'})
    )
    new_password1 = forms.CharField(
        label=_('새 비밀번호'),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '새 비밀번호'}),
        validators=[validate_password]
    )
    new_password2 = forms.CharField(
        label=_('새 비밀번호 확인'),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '새 비밀번호 확인'})
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_old_password(self):
        """현재 비밀번호 검증"""
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise ValidationError(_('현재 비밀번호가 올바르지 않습니다.'))
        return old_password
    
    def clean_new_password2(self):
        """새 비밀번호 일치 검증"""
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError(_('두 비밀번호가 일치하지 않습니다.'))
        return password2
    
    def save(self, commit=True):
        """비밀번호 저장"""
        self.user.set_password(self.cleaned_data['new_password1'])
        if commit:
            self.user.save()
        return self.user