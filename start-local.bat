@echo off
title AI RCA Copilot Launcher
echo =====================================================
echo  Starting AI Root Cause Analysis Copilot (Local Run)
echo =====================================================

powershell -ExecutionPolicy Bypass -File "%~dp0start-local.ps1"
pause
