# accounts/urls.py
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # 인증 관련 URL
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # 비밀번호 관리
    path('password/change/', views.password_change_view, name='password_change'),
    path('password/reset/', views.password_reset_request_view, name='password_reset'),
    path('password/reset/<uidb64>/<token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
    
    # 프로필 관리
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update_view, name='profile_update'),
    
    # 프로젝트 관리
    path('projects/', views.project_list_view, name='project_list'),
    path('projects/create/', views.project_create_view, name='project_create'),
    path('projects/<uuid:project_id>/', views.project_detail_view, name='project_detail'),
    path('projects/<uuid:project_id>/invite/', views.project_invite_view, name='project_invite'),
    path('projects/<uuid:project_id>/members/<int:member_id>/role/', views.project_change_role_view, name='project_change_role'),
    path('projects/<uuid:project_id>/members/<int:member_id>/remove/', views.project_remove_member_view, name='project_remove_member'),
    path('projects/switch/', views.switch_project_view, name='switch_project'),
]