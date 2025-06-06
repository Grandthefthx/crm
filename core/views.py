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

    # Дисковая статистика
    disk = psutil.disk_usage('/')
    disk_total = round(disk.total / 1024 / 1024 / 1024, 1)  # ГБ
    disk_used = round(disk.used / 1024 / 1024 / 1024, 1)
    disk_free = round(disk.free / 1024 / 1024 / 1024, 1)
    disk_percent = disk.percent

    # IO статистика (байты с запуска)
    io = psutil.disk_io_counters()
    io_read_mb = round(io.read_bytes / 1024 / 1024, 1)
    io_write_mb = round(io.write_bytes / 1024 / 1024, 1)

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
            mem_bytes = proc.memory_info().rss
            mem_mb = round(mem_bytes / 1024 / 1024, 1)
            top_mem.append({
                "pid": proc.info['pid'],
                "name": proc.info['name'],
                "mem_mb": mem_mb,
                "mem_percent": round(proc.info['memory_percent'], 1)
            })
        except Exception:
            continue
    top_mem = sorted(top_mem, key=lambda p: p["mem_mb"], reverse=True)[:5]

    return JsonResponse({
        "cpu": cpu,
        "ram": ram,
        "uptime": str(uptime).split('.')[0],
        "top_cpu": top_cpu,
        "top_mem": top_mem,
        "disk_total": disk_total,
        "disk_used": disk_used,
        "disk_free": disk_free,
        "disk_percent": disk_percent,
        "io_read_mb": io_read_mb,
        "io_write_mb": io_write_mb,
    })
