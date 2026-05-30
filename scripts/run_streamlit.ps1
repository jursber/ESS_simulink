# 储能 UI — Windows 启动（避免控制台中文乱码）
# 用法：在项目根目录执行  .\scripts\run_streamlit.ps1
# 或：powershell -ExecutionPolicy Bypass -File .\scripts\run_streamlit.ps1
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

python -m streamlit run app.py
