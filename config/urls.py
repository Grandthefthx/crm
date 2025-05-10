from django.contrib import admin
from django.urls import path, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from core.views import glances_proxy, monitoring_page

def monitor_root_redirect(request):
    return redirect('/adminka-193n/monitor/api/')

urlpatterns = [
    path('adminka-193n/performance/', monitoring_page, name='admin_monitoring'),  # ⬅️ Обязательно первым!
    path('adminka-193n/', admin.site.urls),
    path('adminka-193n/monitor/', monitor_root_redirect),
    path('adminka-193n/monitor/api/', glances_proxy),
    re_path(r'^adminka-193n/monitor/(?P<path>.*)$', glances_proxy),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
