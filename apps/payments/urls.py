from django.urls import path
from . import views

urlpatterns = [
    path('callback/', views.mpesa_callback_view, name='mpesa_callback'),
]