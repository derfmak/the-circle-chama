from django.urls import path
from . import admin_views

urlpatterns = [
    path('', admin_views.admin_announcements_view, name='admin_announcements'),
    path('create/', admin_views.admin_create_announcement_view, name='admin_create_announcement'),
    path('<int:announcement_id>/edit/', admin_views.admin_edit_announcement_view, name='admin_edit_announcement'),
    path('<int:announcement_id>/delete/', admin_views.admin_delete_announcement_view, name='admin_delete_announcement'),
]