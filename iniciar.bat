@echo off
cd /d "%~dp0"

if not exist .env (
    copy .env.ejemplo .env >nul
    echo Se creo el archivo .env. Escribe tus claves, guarda y vuelve a abrir iniciar.bat.
    notepad .env
    exit /b
)

rem Jarvis necesita Python 3.12 o superior; con uno viejo la instalacion parece ir bien y luego falla.
if not exist .venv\Scripts\python.exe (
    python -c "import sys; assert sys.hexversion >= 0x030C0000" || goto falta_python
    python -m venv .venv || goto falta_python
)

rem La marca evita reinstalar en cada arranque; si la instalacion falla se reintenta la proxima vez.
if not exist .venv\instalado (
    .venv\Scripts\python -m pip install -r requirements.txt || goto error
    echo ok> .venv\instalado
)

for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    if /i "%%a"=="NGROK_DOMINIO" set "NGROK_DOMINIO=%%b"
)

where ngrok >nul 2>&1 || (
    echo No encuentro ngrok. Instalalo con: winget install ngrok.ngrok
    goto error
)

rem 127.0.0.1 y no "localhost": Flask solo escucha en IPv4 y ngrok podria intentar IPv6.
if defined NGROK_DOMINIO (
    start "ngrok" ngrok http --url=%NGROK_DOMINIO% 127.0.0.1:5000
) else (
    start "ngrok" ngrok http 127.0.0.1:5000
)

.venv\Scripts\python servidor.py
pause
exit /b

:falta_python
echo No encuentro Python. Instala Python 3.12 o superior marcando "Add python.exe to PATH".
:error
pause
