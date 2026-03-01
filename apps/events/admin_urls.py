from django.urls import path
from . import admin_views

urlpatterns = [
    path('', admin_views.admin_events_view, name='admin_events'),
    path('create/', admin_views.admin_create_event_view, name='admin_create_event'),
    path('<int:event_id>/applications/', admin_views.admin_event_applications_view, name='admin_event_applications'),
    path('winners/', admin_views.admin_event_winners_view, name='admin_event_winners'),
]