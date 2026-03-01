from django.urls import path
from . import admin_views

urlpatterns = [
    path('', admin_views.admin_meetings_view, name='admin_meetings'),
    path('create/', admin_views.admin_create_meeting_view, name='admin_create_meeting'),
    path('<int:meeting_id>/', admin_views.admin_meeting_detail_view, name='admin_meeting_detail'),
    path('<int:meeting_id>/edit/', admin_views.admin_edit_meeting_view, name='admin_edit_meeting'),
    path('<int:meeting_id>/summary/', admin_views.admin_add_summary_view, name='admin_add_summary'),
    path('reports/', admin_views.admin_attendance_report_view, name='admin_attendance_report'),
    path('member/<int:member_id>/', admin_views.admin_member_attendance_view, name='admin_member_attendance'),
]