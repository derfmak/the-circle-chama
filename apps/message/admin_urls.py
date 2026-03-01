from django.urls import path
from . import admin_views

urlpatterns = [
    path('', admin_views.admin_messages_view, name='admin_messages'),
    path('<int:message_id>/', admin_views.admin_message_detail_view, name='admin_message_detail'),
    path('<int:message_id>/reply/', admin_views.admin_reply_message_view, name='admin_reply_message'),
    path('<int:message_id>/status/', admin_views.admin_update_message_status_view, name='admin_update_message_status'),
    path('<int:message_id>/delete/', admin_views.admin_delete_message_view, name='admin_delete_message'),
]