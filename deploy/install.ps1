# PowerShell script for Windows deployment
# Mantri Trade Book - Windows PowerShell Installation Script

param(
    [Parameter(Mandatory=$false)]
    [string]$InstallPath = "$env:USERPROFILE\TradeBook",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipDesktopShortcut = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$Verbose = $false
)

# Enable verbose output if requested
if ($Verbose) {
    $VerbosePreference = "Continue"
}

# Colors for output
$ColorInfo = "Cyan"
$ColorSuccess = "Green"
$ColorWarning = "Yellow"
$ColorError = "Red"

function Write-StatusMessage {
    param([string]$Message, [string]$Color = $ColorInfo)
    Write-Host "[INFO] $Message" -ForegroundColor $Color
}

function Write-SuccessMessage {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $ColorSuccess
}

function Write-WarningMessage {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $ColorWarning
}

function Write-ErrorMessage {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $ColorError
}

function Test-CommandExists {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

function Test-PythonVersion {
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            return ($major -eq 3 -and $minor -ge 8) -or ($major -gt 3)
        }
        return $false
    }
    catch {
        return $false
    }
}

function New-VirtualEnvironment {
    param([string]$Path, [string]$VenvName = "venv")
    
    $venvPath = Join-Path $Path $VenvName
    Write-StatusMessage "Creating virtual environment at $venvPath"
    
    & python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create virtual environment"
    }
    
    return $venvPath
}

function Install-PythonPackages {
    param([string]$VenvPath, [string]$RequirementsFile)
    
    $activateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
    Write-StatusMessage "Installing Python packages from $RequirementsFile"
    
    # Activate virtual environment
    & $activateScript
    
    # Upgrade pip
    & python -m pip install --upgrade pip
    
    # Install requirements
    & pip install -r $RequirementsFile
    
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install Python packages"
    }
}

function New-StartupScript {
    param([string]$InstallPath, [string]$VenvName = "venv")
    
    $startScript = Join-Path $InstallPath "start.ps1"
    $batScript = Join-Path $InstallPath "start.bat"
    
    # PowerShell startup script
    $psContent = @"
# Mantri Trade Book Startup Script
Set-Location -Path `$PSScriptRoot
& ".\$VenvName\Scripts\Activate.ps1"
`$env:FLASK_ENV = "production"
& python app.py
"@
    
    # Batch startup script for compatibility
    $batContent = @"
@echo off
cd /d "%~dp0"
call $VenvName\Scripts\activate.bat
set FLASK_ENV=production
python app.py
pause
"@
    
    $psContent | Out-File -FilePath $startScript -Encoding UTF8
    $batContent | Out-File -FilePath $batScript -Encoding ASCII
    
    Write-SuccessMessage "Startup scripts created"
}

function New-DesktopShortcut {
    param([string]$InstallPath)
    
    if ($SkipDesktopShortcut) {
        Write-StatusMessage "Skipping desktop shortcut creation"
        return
    }
    
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktopPath "Mantri Trade Book.lnk"
    $startScript = Join-Path $InstallPath "start.bat"
    
    $wshShell = New-Object -ComObject WScript.Shell
    $shortcut = $wshShell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $startScript
    $shortcut.WorkingDirectory = $InstallPath
    $shortcut.Description = "Mantri Trade Book - Trading Portfolio Management"
    $shortcut.Save()
    
    Write-SuccessMessage "Desktop shortcut created"
}

function Initialize-Database {
    param([string]$InstallPath, [string]$VenvName = "venv")
    
    Write-StatusMessage "Initializing database..."
    
    Set-Location $InstallPath
    $activateScript = Join-Path $InstallPath "$VenvName\Scripts\Activate.ps1"
    & $activateScript
    
    $initScript = @"
from app import app
with app.app_context():
    from models.database import db
    db.create_all()
    print('Database initialized successfully')
"@
    
    $initScript | python -
    
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to initialize database"
    }
    
    Write-SuccessMessage "Database initialized"
}

function New-EnvironmentFile {
    param([string]$InstallPath)
    
    $envFile = Join-Path $InstallPath ".env"
    
    if (Test-Path $envFile) {
        Write-StatusMessage "Environment file already exists"
        return
    }
    
    Write-StatusMessage "Creating environment configuration file..."
    
    # Generate random keys
    $secretKey = -join ((1..64) | ForEach { '{0:X}' -f (Get-Random -Max 16) })
    $encryptionKey = -join ((1..32) | ForEach { '{0:X}' -f (Get-Random -Max 16) })
    
    $envContent = @"
SECRET_KEY=$secretKey
ENCRYPTION_KEY=$encryptionKey
FLASK_ENV=production
DATABASE_URL=sqlite:///instance/mantri_trade_book.db
"@
    
    $envContent | Out-File -FilePath $envFile -Encoding UTF8
    Write-SuccessMessage "Environment file created"
}

function Copy-ApplicationFiles {
    param([string]$SourcePath, [string]$DestinationPath)
    
    Write-StatusMessage "Copying application files..."
    
    # Create destination directory
    if (Test-Path $DestinationPath) {
        $backupPath = "$DestinationPath.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Write-WarningMessage "Destination exists, backing up to $backupPath"
        Move-Item $DestinationPath $backupPath
    }
    
    New-Item -ItemType Directory -Path $DestinationPath -Force | Out-Null
    
    # Copy files excluding certain directories
    $excludePatterns = @("deploy", "__pycache__", "*.pyc", ".git", "instance", "logs", "venv", ".env")
    
    Get-ChildItem -Path $SourcePath -Recurse | Where-Object {
        $relativePath = $_.FullName.Substring($SourcePath.Length + 1)
        $shouldExclude = $false
        
        foreach ($pattern in $excludePatterns) {
            if ($relativePath -like "*$pattern*") {
                $shouldExclude = $true
                break
            }
        }
        
        return -not $shouldExclude
    } | Copy-Item -Destination {
        $destPath = $_.FullName.Replace($SourcePath, $DestinationPath)
        $destDir = Split-Path $destPath -Parent
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        return $destPath
    }
    
    # Create necessary directories
    @("instance", "logs") | ForEach {
        $dir = Join-Path $DestinationPath $_
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    
    Write-SuccessMessage "Application files copied"
}

function Show-InstallationSummary {
    param([string]$InstallPath)
    
    Write-Host ""
    Write-Host "==================== INSTALLATION COMPLETE ====================" -ForegroundColor $ColorSuccess
    Write-Host "Mantri Trade Book has been successfully installed!" -ForegroundColor $ColorSuccess
    Write-Host ""
    Write-Host "Installation directory: $InstallPath"
    Write-Host "Python version: $(python --version)"
    Write-Host ""
    Write-Host "==================== HOW TO START ====================" -ForegroundColor $ColorInfo
    Write-Host "1. PowerShell: & '$InstallPath\start.ps1'"
    Write-Host "2. Command Prompt: $InstallPath\start.bat"
    if (-not $SkipDesktopShortcut) {
        Write-Host "3. Use the desktop shortcut"
    }
    Write-Host ""
    Write-Host "The application will be available at: http://localhost:5001"
    Write-Host ""
    Write-Host "==================== CONFIGURATION ====================" -ForegroundColor $ColorInfo
    Write-Host "Configuration file: $InstallPath\.env"
    Write-Host "Database location: $InstallPath\instance\mantri_trade_book.db"
    Write-Host "Logs directory: $InstallPath\logs\"
    Write-Host ""
    Write-Host "==================== UNINSTALL ====================" -ForegroundColor $ColorInfo
    Write-Host "To uninstall, simply delete the directory: $InstallPath"
    Write-Host "============================================================"
}

# Main installation process
try {
    Write-Host "==================== MANTRI TRADE BOOK INSTALLER ====================" -ForegroundColor $ColorInfo
    Write-Host "This installer will set up Mantri Trade Book on your Windows system." -ForegroundColor $ColorInfo
    Write-Host "=====================================================================" -ForegroundColor $ColorInfo
    Write-Host ""
    
    # Check prerequisites
    Write-StatusMessage "Checking prerequisites..."
    
    if (-not (Test-CommandExists "python")) {
        Write-ErrorMessage "Python is not installed or not in PATH"
        Write-WarningMessage "Please install Python 3.8+ from https://www.python.org/downloads/"
        Write-WarningMessage "Make sure to check 'Add Python to PATH' during installation"
        exit 1
    }
    
    if (-not (Test-PythonVersion)) {
        Write-ErrorMessage "Python 3.8 or higher is required"
        Write-StatusMessage "Current Python version: $(python --version)"
        exit 1
    }
    
    Write-SuccessMessage "Python $(python --version) found"
    
    if (-not (Test-CommandExists "pip")) {
        Write-ErrorMessage "pip is not available"
        exit 1
    }
    
    Write-SuccessMessage "pip is available"
    
    # Get source directory (parent of deploy directory)
    $scriptPath = $PSScriptRoot
    $sourcePath = Split-Path $scriptPath -Parent
    
    # Copy application files
    Copy-ApplicationFiles -SourcePath $sourcePath -DestinationPath $InstallPath
    
    # Create virtual environment
    $venvPath = New-VirtualEnvironment -Path $InstallPath
    
    # Install dependencies
    $requirementsFile = Join-Path $InstallPath "requirements.txt"
    Install-PythonPackages -VenvPath $venvPath -RequirementsFile $requirementsFile
    
    # Setup environment
    New-EnvironmentFile -InstallPath $InstallPath
    
    # Initialize database
    Initialize-Database -InstallPath $InstallPath
    
    # Create startup scripts
    New-StartupScript -InstallPath $InstallPath
    
    # Create desktop shortcut
    New-DesktopShortcut -InstallPath $InstallPath
    
    # Show summary
    Show-InstallationSummary -InstallPath $InstallPath
    
    Write-Host ""
    Write-Host "Press any key to exit..." -ForegroundColor $ColorInfo
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    
} catch {
    Write-ErrorMessage "Installation failed: $($_.Exception.Message)"
    Write-Host "Press any key to exit..." -ForegroundColor $ColorError
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}