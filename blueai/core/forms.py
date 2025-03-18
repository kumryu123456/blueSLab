# core/forms.py
from django import forms
from .models import Task

class TaskForm(forms.ModelForm):
    """작업 생성 및 수정 폼"""
    class Meta:
        model = Task
        fields = ['title', 'user_input', 'process']
        widgets = {
            'user_input': forms.Textarea(attrs={'rows': 4}),
        }
        
    def clean_process(self):
        """처리 단계 검증"""
        process = self.cleaned_data.get('process')
        if not process:
            return ''
            
        # 쉼표로 구분된 문자열인지 확인
        if ',' not in process:
            return process
            
        # 각 단계가 유효한지 확인
        steps = [step.strip() for step in process.split(',')]
        if any(not step for step in steps):
            raise forms.ValidationError('유효하지 않은 처리 단계가 있습니다.')
            
        return process

class TaskTitleForm(forms.Form):
    """작업 제목 업데이트 폼"""
    title = forms.CharField(max_length=200, required=True)
    
    def clean_title(self):
        """제목 검증"""
        title = self.cleaned_data.get('title')
        if not title.strip():
            raise forms.ValidationError('제목은 공백일 수 없습니다.')
        return title