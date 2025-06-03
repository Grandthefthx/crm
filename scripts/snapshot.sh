#!/bin/bash
set -e

DATE=$(date +%Y-%m-%d_%H-%M)
DEST="/root/crm/backups/crm_snapshot_$DATE.tar.gz"

# Архивируем всё содержимое /root/crm, кроме backups, logs и *.log файлов
tar \
    --exclude='./backups' \
    --exclude='./logs' \
    --exclude='*.log' \
    -czf "$DEST" -C /root crm

# Оставляем только 7 последних архивов
ls -tp /root/crm/backups/crm_snapshot_*.tar.gz | grep -v '/$' | tail -n +8 | xargs -r rm --

echo "✅ Полный бэкап создан: $DEST"
