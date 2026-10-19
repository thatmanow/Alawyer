@echo off
chcp 65001 >nul
title alawyer 启动器

netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [alawyer] 后端未运行，正在启动...
    start "alawyer-backend" cmd /k "cd /d E:\alawyer\backend && D:\anaconda3\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
    echo [alawyer] 等待服务就绪...
    timeout /t 8 /nobreak >nul
) else (
    echo [alawyer] 后端已在运行
)

start http://127.0.0.1:8000
exit