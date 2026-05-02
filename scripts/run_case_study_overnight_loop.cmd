@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_case_study_overnight_loop.ps1" -SleepSeconds 5 -PublishEveryMinutes 30 -EndHour 6
