from django.urls import path
from . import admin_views

urlpatterns = [
    path('', admin_views.admin_contributions_view, name='admin_contributions'),
    path('types/create/', admin_views.admin_create_contribution_type_view, name='admin_create_contribution_type'),
    path('<int:contribution_id>/edit/', admin_views.admin_edit_contribution_view, name='admin_edit_contribution'),
    path('approvals/', admin_views.admin_payment_approval_view, name='admin_payment_approval'),
    path('reports/', admin_views.admin_contribution_report_view, name='admin_contribution_report'),
]