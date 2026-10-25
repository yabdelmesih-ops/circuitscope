@echo off
cd /d "%~dp0"
py -m streamlit run "%~dp0drawing_app.py"
pause
