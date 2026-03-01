from django.urls import path
from . import views

urlpatterns = [
    path('', views.events_list_view, name='events_list'),
    path('apply/<int:event_id>/', views.apply_event_view, name='apply_event'),
    path('status/<int:application_id>/', views.application_status_view, name='application_status'),
]