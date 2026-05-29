@echo off
setlocal EnableExtensions

set "REPO_ROOT=%~dp0"
set "DEFAULT_ROOT=D:\crpto_experiments\regret_auditability\regret_auditability_20260513_v3_resource_tuned"

set "ARTIFACT_ROOT=%~1"
if "%ARTIFACT_ROOT%"=="" if not "%CRPTO_SANDBOX_ROOT%"=="" set "ARTIFACT_ROOT=%CRPTO_SANDBOX_ROOT%"
if "%ARTIFACT_ROOT%"=="" set "ARTIFACT_ROOT=%DEFAULT_ROOT%"

set "INTERVAL=%~2"
if "%INTERVAL%"=="" set "INTERVAL=60"

set "ONCE_ARG="
if /I "%~3"=="once" set "ONCE_ARG=--once"

set "PYTHON_EXE=%REPO_ROOT%.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

"%PYTHON_EXE%" "%REPO_ROOT%scripts\search\monitor_regret_auditability.py" --artifact-root "%ARTIFACT_ROOT%" --interval "%INTERVAL%" %ONCE_ARG%
