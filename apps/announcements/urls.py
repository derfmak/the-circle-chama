from django.urls import path
from . import views

urlpatterns = [
    path('', views.announcements_list_view, name='announcements_list'),
    path('<int:announcement_id>/', views.announcement_detail_view, name='announcement_detail'),
]