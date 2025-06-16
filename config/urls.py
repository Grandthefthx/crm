from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core.views import monitoring_page, metrics_api, check_access_view

urlpatterns = [
    path('adminka-193n/performance/', monitoring_page, name='admin_monitoring'),
    path('adminka-193n/monitor/api/', metrics_api, name='metrics_api'),
    path('api/check-access/', check_access_view, name='check_access'),
    path('adminka-193n/', admin.site.urls),
]

# Для загрузки медиафайлов (например, фото к рассылке) в DEBUG-режиме
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
