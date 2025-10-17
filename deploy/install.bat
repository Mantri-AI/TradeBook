@echo off
REM Mantri Trade Book - Windows Installation Script

setlocal enabledelayedexpansion

REM Colors (Windows doesn't support colors in batch easily, so we'll use echo)
echo [92m==================== MANTRI TRADE BOOK INSTALLER ====================[0m
echo [92mThis installer will set up Mantri Trade Book on your Windows system.[0m
echo [92m=====================================================================[0m
echo.

REM Configuration
set APP_NAME=TradeBook
set INSTALL_DIR=%USERPROFILE%\%APP_NAME%
set VENV_NAME=venv
set PYTHON_MIN_VERSION=3.8

REM Check if Python is installed
echo [94m[INFO][0m Checking for Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [91m[ERROR][0m Python is not installed or not in PATH
    echo [93m[WARNING][0m Please install Python 3.8+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

REM Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [92m[SUCCESS][0m Python %PYTHON_VERSION% found

REM Check if pip is available
echo [94m[INFO][0m Checking for pip...
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [91m[ERROR][0m pip is not available
    pause
    exit /b 1
)
echo [92m[SUCCESS][0m pip is available

REM Check if git is available
echo [94m[INFO][0m Checking for git...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [93m[WARNING][0m git is not available. You may need to install it from https://git-scm.com/
)

REM Create installation directory
echo [94m[INFO][0m Creating installation directory: %INSTALL_DIR%
if exist "%INSTALL_DIR%" (
    echo [93m[WARNING][0m Directory already exists. Backing up...
    move "%INSTALL_DIR%" "%INSTALL_DIR%.backup.%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%" >nul 2>&1
)
mkdir "%INSTALL_DIR%" 2>nul

REM Copy application files (assuming script is in deploy folder)
echo [94m[INFO][0m Copying application files...
set SCRIPT_DIR=%~dp0
set APP_SOURCE_DIR=%SCRIPT_DIR%..

REM Copy files (excluding certain directories)
xcopy "%APP_SOURCE_DIR%\*" "%INSTALL_DIR%\" /E /I /H /Y /EXCLUDE:%SCRIPT_DIR%exclude.txt >nul 2>&1
if not exist "%SCRIPT_DIR%exclude.txt" (
    REM Create exclude file if it doesn't exist
    echo deploy\ > "%SCRIPT_DIR%exclude.txt"
    echo __pycache__\ >> "%SCRIPT_DIR%exclude.txt"
    echo *.pyc >> "%SCRIPT_DIR%exclude.txt"
    echo .git\ >> "%SCRIPT_DIR%exclude.txt"
    echo instance\ >> "%SCRIPT_DIR%exclude.txt"
    echo logs\ >> "%SCRIPT_DIR%exclude.txt"
    
    REM Copy again with exclusions
    xcopy "%APP_SOURCE_DIR%\*" "%INSTALL_DIR%\" /E /I /H /Y /EXCLUDE:%SCRIPT_DIR%exclude.txt >nul 2>&1
)

REM Create necessary directories
mkdir "%INSTALL_DIR%\instance" 2>nul
mkdir "%INSTALL_DIR%\logs" 2>nul

echo [92m[SUCCESS][0m Application files copied

REM Change to installation directory
cd /d "%INSTALL_DIR%"

REM Create virtual environment
echo [94m[INFO][0m Creating Python virtual environment...
python -m venv %VENV_NAME%
if %errorlevel% neq 0 (
    echo [91m[ERROR][0m Failed to create virtual environment
    pause
    exit /b 1
)
echo [92m[SUCCESS][0m Virtual environment created

REM Activate virtual environment and install dependencies
echo [94m[INFO][0m Installing Python dependencies...
call %VENV_NAME%\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [91m[ERROR][0m Failed to install dependencies
    pause
    exit /b 1
)
echo [92m[SUCCESS][0m Dependencies installed

REM Setup environment file
echo [94m[INFO][0m Setting up configuration...
if not exist ".env" (
    echo SECRET_KEY=your-secret-key-change-me > .env
    echo ENCRYPTION_KEY=your-encryption-key-change-me >> .env
    echo FLASK_ENV=production >> .env
    echo DATABASE_URL=sqlite:///instance/mantri_trade_book.db >> .env
    echo [92m[SUCCESS][0m Environment file created
)

REM Initialize database
echo [94m[INFO][0m Setting up database...
python -c "from app import app; app.app_context().push(); from models.database import db; db.create_all(); print('Database initialized successfully')"
if %errorlevel% neq 0 (
    echo [91m[ERROR][0m Failed to initialize database
    pause
    exit /b 1
)
echo [92m[SUCCESS][0m Database setup complete

REM Create startup batch file
echo [94m[INFO][0m Creating startup scripts...
echo @echo off > start.bat
echo cd /d "%%~dp0" >> start.bat
echo call %VENV_NAME%\Scripts\activate.bat >> start.bat
echo set FLASK_ENV=production >> start.bat
echo python app.py >> start.bat
echo pause >> start.bat

REM Create desktop shortcut
set /p CREATE_SHORTCUT="Create desktop shortcut? (y/N): "
if /i "%CREATE_SHORTCUT%"=="y" (
    echo [94m[INFO][0m Creating desktop shortcut...
    echo @echo off > "%USERPROFILE%\Desktop\Mantri Trade Book.bat"
    echo cd /d "%INSTALL_DIR%" >> "%USERPROFILE%\Desktop\Mantri Trade Book.bat"
    echo start.bat >> "%USERPROFILE%\Desktop\Mantri Trade Book.bat"
    echo [92m[SUCCESS][0m Desktop shortcut created
)

REM Create uninstall script
echo [94m[INFO][0m Creating uninstall script...
echo @echo off > uninstall.bat
echo echo Uninstalling Mantri Trade Book... >> uninstall.bat
echo cd /d "%%USERPROFILE%%" >> uninstall.bat
echo rmdir /s /q "%INSTALL_DIR%" >> uninstall.bat
echo del "%%USERPROFILE%%\Desktop\Mantri Trade Book.bat" 2^>nul >> uninstall.bat
echo echo Uninstallation complete! >> uninstall.bat
echo pause >> uninstall.bat

REM Deactivate virtual environment
call %VENV_NAME%\Scripts\deactivate.bat

REM Installation summary
echo.
echo [92m==================== INSTALLATION COMPLETE ====================[0m
echo [92mMantri Trade Book has been successfully installed![0m
echo.
echo Installation directory: %INSTALL_DIR%
echo Python version: %PYTHON_VERSION%
echo.
echo [94m==================== HOW TO START ====================[0m
echo 1. Double-click: %INSTALL_DIR%\start.bat
echo 2. Or run from command line: cd %INSTALL_DIR% ^&^& start.bat
if exist "%USERPROFILE%\Desktop\Mantri Trade Book.bat" (
    echo 3. Or use the desktop shortcut
)
echo.
echo The application will be available at: http://localhost:5001
echo.
echo [94m==================== CONFIGURATION ====================[0m
echo Configuration file: %INSTALL_DIR%\.env
echo Database location: %INSTALL_DIR%\instance\mantri_trade_book.db
echo Logs directory: %INSTALL_DIR%\logs\
echo.
echo [94m==================== UNINSTALL ====================[0m
echo To uninstall, run: %INSTALL_DIR%\uninstall.bat
echo [94m============================================================[0m
echo.
pause