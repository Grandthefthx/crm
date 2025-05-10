from django.shortcuts import render
from django.http import HttpResponse, HttpResponseNotFound
from django.contrib.admin.views.decorators import staff_member_required
import httpx

@staff_member_required
def glances_proxy(request, path=''):
    print(f"🔍 glances_proxy вызывается! path={path}")  # <-- отладка
    try:
        url = f"http://127.0.0.1:61208/{path}"
        print(f"➡ Проксируем на {url}")  # <-- отладка
        resp = httpx.get(url, timeout=5)
        return HttpResponse(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get("content-type")
        )
    except Exception as e:
        print(f"❌ Ошибка при проксировании: {e}")  # <-- отладка
        return HttpResponseNotFound(f"Glances недоступен: {str(e)}")

@staff_member_required
def monitoring_page(request):
    print("📊 monitoring_page загружается!")  # <-- отладка
    return render(request, 'admin/monitoring.html')
