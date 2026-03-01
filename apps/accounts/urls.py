from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('login/', views.member_login_view, name='login'),
    path('admin/login/', views.admin_login_view, name='admin_login'),
    path('logout/', views.logout_view, name='logout'),
    path('password-change/', views.initial_password_change_view, name='initial_password_change'),
    path('admin/password-change/', views.admin_initial_password_change_view, name='admin_initial_password_change'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('verify-code/', views.verify_reset_code_view, name='verify_reset_code'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    path('profile/', views.profile_view, name='profile'),
]