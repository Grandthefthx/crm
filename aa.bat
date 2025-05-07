@echo off
REM Скрипт создает дерево файлов и сохраняет его в файл project_structure.txt

set OUTPUT_FILE=project_structure.txt
echo Generating project tree...

REM Удаляем старый файл, если есть
if exist %OUTPUT_FILE% del %OUTPUT_FILE%

REM Генерация дерева (включая все поддиректории и файлы)
tree /F /A > %OUTPUT_FILE%

echo Done! Project structure saved to %OUTPUT_FILE%
pause
