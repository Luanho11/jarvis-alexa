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
rem Cambia de nombre cuando requirements.txt suma librerias, para que una instalacion vieja las reciba.
if not exist .venv\instalado-2 (
    .venv\Scripts\python -m pip install -r requirements.txt || goto error
    echo ok> .venv\instalado-2
)

where ngrok >nul 2>&1 || (
    echo No encuentro ngrok. Instalalo con: winget install ngrok.ngrok
    goto error
)

rem Sin ventanas negras: Jarvis y ngrok quedan en segundo plano con un icono junto al reloj.
rem Para ver los mensajes, clic derecho en el icono, "Ver registro". Para depurar: .venv\Scripts\python servidor.py
start "" .venv\Scripts\pythonw.exe lanzador.py
exit /b

:falta_python
echo No encuentro Python. Instala Python 3.12 o superior marcando "Add python.exe to PATH".
:error
pause
