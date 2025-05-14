from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core.views import monitoring_page, metrics_api

urlpatterns = [
    path('adminka-193n/performance/', monitoring_page, name='admin_monitoring'),
    path('adminka-193n/monitor/api/', metrics_api, name='metrics_api'),
    path('adminka-193n/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
