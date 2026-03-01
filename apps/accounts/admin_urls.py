from django.urls import path
from . import admin_views

urlpatterns = [
    path('login/', admin_views.admin_login_view, name='admin_login'),
    path('dashboard/', admin_views.admin_dashboard_view, name='admin_dashboard'),
    path('members/', admin_views.admin_members_list_view, name='admin_members_list'),
    path('members/create/', admin_views.admin_create_member_view, name='admin_create_member'),
    path('members/<int:member_id>/edit/', admin_views.admin_edit_member_view, name='admin_edit_member'),
    path('members/<int:member_id>/delete/', admin_views.admin_delete_member_view, name='admin_delete_member'),
]