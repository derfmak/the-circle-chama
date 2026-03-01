from django.urls import path

from apps.members import admin_views
from . import views

urlpatterns = [
    path('dashboard/', views.member_dashboard_view, name='member_dashboard'),
    path('contributions/', views.contributions_view, name='contributions'),
    path('contributions/make-payment/', views.make_payment_view, name='make_payment'),
    path('request-again/<int:contribution_id>/', views.request_again_view, name='request_again'),  # ADD THIS LINE
    path('contributions/quarterly/', views.quarterly_contributions_view, name='quarterly_contributions'),
    path('contributions/quarterly/pay/<int:quarter>/', views.pay_quarterly_view, name='pay_quarterly'),
    path('payment/pending/<int:transaction_id>/', views.payment_pending_view, name='payment_pending'),
    path('payment/check-status/<int:transaction_id>/', views.check_payment_status_view, name='check_payment_status'),
    path('payment/success/<int:transaction_id>/', views.payment_success_view, name='payment_success'),
    path('payment/failed/<int:transaction_id>/', views.payment_failed_view, name='payment_failed'),
    path('payment-review/<int:payment_id>/', admin_views.admin_review_cash_request_view, name='admin_review_cash_request'),
]