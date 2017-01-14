@ECHO ON

call activate test-environment

echo "%PATH%"
echo "%QT_PLUGIN_PATH%"
python -V
call pyuic5 --version

pyrcc5 -version

lrelease -version

echo "%cd%"
set PYTHONPATH="%PYTHONPATH%;%CD%\src"
echo "%PYTHONPATH%"
py.test tests/

if %errorlevel% neq 0 exit /b 1