from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('apps.accounts.urls')),
    path('members/', include('apps.members.urls')),
    path('meetings/', include('apps.meetings.urls')),
    path('events/', include('apps.events.urls')),
    path('payments/', include('apps.payments.urls')),
    path('announcements/', include('apps.announcements.urls')),
    path('contact/', include('apps.message.urls')),
    path('admin-panel/', include('apps.accounts.admin_urls')),
    path('admin-panel/contributions/', include('apps.members.admin_urls')),
    path('admin-panel/meetings/', include('apps.meetings.admin_urls')),
    path('admin-panel/events/', include('apps.events.admin_urls')),
    path('admin-panel/announcements/', include('apps.announcements.admin_urls')),
    path('admin-panel/messages/', include('apps.message.admin_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)