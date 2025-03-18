# core/admin.py
from django.contrib import admin
from .models import Task, Favorite

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """작업 관리 관리자 설정"""
    list_display = ('title', 'created_at', 'completed')
    list_filter = ('completed', 'created_at')
    search_fields = ('title', 'user_input')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('title', 'user_input', 'created_at', 'completed')
        }),
        ('처리 과정', {
            'fields': ('process', 'result')
        }),
        ('대화 기록', {
            'fields': ('conversation',),
            'classes': ('collapse',)
        })
    )

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    """즐겨찾기 관리 관리자 설정"""
    list_display = ('task', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('task__title',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)