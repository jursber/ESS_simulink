@echo off
REM 储能 UI — 双击或 cmd 运行；UTF-8 控制台减少乱码
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0.."
python -m streamlit run app.py
if errorlevel 1 pause
