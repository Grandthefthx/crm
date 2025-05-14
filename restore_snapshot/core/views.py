from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
import psutil
import datetime
import time

@staff_member_required
def monitoring_page(request):
    return render(request, 'admin/monitoring.html')

@staff_member_required
def metrics_api(request):
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())

    # Инициализация, чтобы cpu_percent начал считать
    for proc in psutil.process_iter():
        try:
            proc.cpu_percent(interval=None)
        except Exception:
            continue
    time.sleep(0.1)

    # Топ по CPU
    top_cpu = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            top_cpu.append({
                "pid": proc.info['pid'],
                "name": proc.info['name'],
                "cpu": proc.cpu_percent()
            })
        except Exception:
            continue
    top_cpu = sorted(top_cpu, key=lambda p: p["cpu"], reverse=True)[:5]

    # Топ по RAM
    top_mem = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
        try:
            top_mem.append({
                "pid": proc.info['pid'],
                "name": proc.info['name'],
                "mem": round(proc.info['memory_percent'], 1)
            })
        except Exception:
            continue
    top_mem = sorted(top_mem, key=lambda p: p["mem"], reverse=True)[:5]

    return JsonResponse({
        "cpu": cpu,
        "ram": ram,
        "uptime": str(uptime).split('.')[0],
        "top_cpu": top_cpu,
        "top_mem": top_mem,
    })