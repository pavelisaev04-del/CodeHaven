@echo off
chcp 65001 >nul
echo =====================================================
echo   Учёт почтовых расходов — запуск сервера
echo =====================================================
echo.

REM Переходим в папку программы
cd /d "%~dp0"

REM Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не установлен или не добавлен в PATH.
    echo Скачайте Python с https://python.org
    pause
    exit /b 1
)

REM Запускаем программу
echo Запуск сервера...
echo Откройте браузер и перейдите по адресу: http://localhost:5000
echo Для остановки нажмите Ctrl+C
echo.
python app.py

pause
