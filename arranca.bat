@echo off
cd /d "%~dp0"
echo Carpeta actual: %cd%
echo Archivos en esta carpeta:
dir
echo.
call "%USERPROFILE%\musicenv\Scripts\activate.bat"
python "%~dp0player_modular.py"
echo.
echo ====== FIN / ERROR ======
pause
