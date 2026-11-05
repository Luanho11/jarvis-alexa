@echo off
rem Hace que Jarvis arranque solo al encender el PC (acceso directo en la carpeta Inicio de Windows).
set "DESTINO=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Jarvis.lnk"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:DESTINO); $s.TargetPath='%~dp0iniciar.bat'; $s.WorkingDirectory='%~dp0'; $s.WindowStyle=7; $s.Save()"
if exist "%DESTINO%" (echo Listo: Jarvis se iniciara solo al encender el PC.) else (echo No se pudo crear el acceso directo.)
pause
