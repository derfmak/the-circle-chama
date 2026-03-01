from django.urls import path
from . import views

urlpatterns = [
    path('', views.meetings_list_view, name='meetings_list'),
    path('<int:meeting_id>/', views.meeting_detail_view, name='meeting_detail'),
    path('<int:meeting_id>/respond/', views.respond_meeting_view, name='respond_meeting'),
    path('attendance/<int:attendance_id>/pay/', views.pay_facilitation_view, name='pay_facilitation'),
    path('payment/pending/<int:payment_id>/', views.facilitation_payment_pending_view, name='facilitation_payment_pending'),
    path('payment/check/<int:payment_id>/', views.check_facilitation_status_view, name='check_facilitation_status'),
    path('payment/success/<int:payment_id>/', views.facilitation_payment_success_view, name='facilitation_payment_success'),
    path('payment/failed/<int:payment_id>/', views.facilitation_payment_failed_view, name='facilitation_payment_failed'),
]