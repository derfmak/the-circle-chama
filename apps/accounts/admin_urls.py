from django.urls import path
from . import admin_views

urlpatterns = [
    path('login/', admin_views.admin_login_view, name='admin_login'),
    path('logout/', admin_views.admin_logout_view, name='admin_logout'),
    path('dashboard/', admin_views.admin_dashboard_view, name='admin_dashboard'),
    path('forgot-password/', admin_views.admin_forgot_password_view, name='admin_forgot_password'),
    path('verify-code/', admin_views.admin_verify_code_view, name='admin_verify_code'),
    path('reset-password/', admin_views.admin_reset_password_view, name='admin_reset_password'),
    path('initial-password-change/', admin_views.admin_initial_password_change_view, name='admin_initial_password_change'),
    path('applications/', admin_views.admin_applications_list_view, name='admin_applications_list'),
    path('applications/<int:application_id>/', admin_views.admin_application_detail_view, name='admin_application_detail'),
    path('members/', admin_views.admin_members_list_view, name='admin_members_list'),
    path('members/create/', admin_views.admin_create_member_view, name='admin_create_member'),
    path('members/<int:member_id>/edit/', admin_views.admin_edit_member_view, name='admin_edit_member'),
    path('members/<int:member_id>/delete/', admin_views.admin_delete_member_view, name='admin_delete_member'),
]