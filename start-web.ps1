# Kode AI Web Startup Script (Windows PowerShell)
# This script will start both backend and frontend services

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "  Kode AI Web Startup" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check Python installation
Write-Host "Checking Python..." -ForegroundColor Yellow
$pythonCheck = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCheck) {
    Write-Host "Error: Python not found. Please install Python 3.10+ first." -ForegroundColor Red
    exit 1
}
$pythonVersion = python --version
Write-Host "[OK] $pythonVersion" -ForegroundColor Green

# Check Node.js installation
Write-Host "Checking Node.js..." -ForegroundColor Yellow
$nodeCheck = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCheck) {
    Write-Host "Error: Node.js not found. Please install Node.js first." -ForegroundColor Red
    Write-Host "Download: https://nodejs.org/" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Node.js installed (version: $(node --version))" -ForegroundColor Green

# Check if in project root
if (-not (Test-Path "pyproject.toml")) {
    Write-Host "Error: Please run this script from project root directory." -ForegroundColor Red
    exit 1
}

# Check backend virtual environment
Write-Host ""
Write-Host "Checking backend virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    Write-Host "Error: Virtual environment (.venv) not found." -ForegroundColor Red
    Write-Host "Please create it first with one of these methods:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Method 1: Using venv (recommended)" -ForegroundColor Cyan
    Write-Host "  python -m venv .venv" -ForegroundColor Gray
    Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Gray
    Write-Host "  pip install -e ." -ForegroundColor Gray
    Write-Host ""
    Write-Host "Method 2: Using Poetry" -ForegroundColor Cyan
    Write-Host "  poetry install" -ForegroundColor Gray
    Write-Host ""
    exit 1
}
Write-Host "[OK] Virtual environment (.venv) found" -ForegroundColor Green

# Check if Python packages are installed
Write-Host "Checking backend packages..." -ForegroundColor Yellow
$pythonExe = ".venv\Scripts\python.exe"
$checkKode = & $pythonExe -c "import kode" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Backend packages may not be fully installed." -ForegroundColor Yellow
    Write-Host "Attempting to install..." -ForegroundColor Yellow
    & $pythonExe -m pip install -e . --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Failed to install backend packages." -ForegroundColor Red
        Write-Host "Please install manually:" -ForegroundColor Yellow
        Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Gray
        Write-Host "  pip install -e ." -ForegroundColor Gray
        exit 1
    }
}
Write-Host "[OK] Backend packages ready" -ForegroundColor Green

# Check frontend dependencies
Write-Host "Checking frontend dependencies..." -ForegroundColor Yellow
if (-not (Test-Path "web-frontend/node_modules")) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location web-frontend
    npm install
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        Write-Host "Error: Frontend dependencies installation failed." -ForegroundColor Red
        exit 1
    }
    Pop-Location
}
Write-Host "[OK] Frontend dependencies ready" -ForegroundColor Green

# Check API key configuration
Write-Host ""
Write-Host "Checking API key configuration..." -ForegroundColor Yellow
$apiKeyWarning = $false
if (-not $env:ANTHROPIC_API_KEY) {
    if (-not (Test-Path ".kode.json")) {
        Write-Host "Warning: ANTHROPIC_API_KEY not found in environment or .kode.json" -ForegroundColor Yellow
        Write-Host "Backend may not work properly. Please configure API key." -ForegroundColor Yellow
        $apiKeyWarning = $true
    }
}
if (-not $apiKeyWarning) {
    Write-Host "[OK] API key configuration check passed" -ForegroundColor Green
}

# Check port availability
Write-Host ""
Write-Host "Checking port availability..." -ForegroundColor Yellow

$port8000 = netstat -ano | Select-String ":8000.*LISTENING"
if ($port8000) {
    Write-Host "Warning: Port 8000 is already in use." -ForegroundColor Yellow
    Write-Host "Please close the program using this port if it's not Kode backend." -ForegroundColor Yellow
    $response = Read-Host "Continue? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        exit 0
    }
}

$port3000 = netstat -ano | Select-String ":3000.*LISTENING"
if ($port3000) {
    Write-Host "Warning: Port 3000 is already in use." -ForegroundColor Yellow
    Write-Host "Please close the program using this port if it's not Kode frontend." -ForegroundColor Yellow
    $response = Read-Host "Continue? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        exit 0
    }
}

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "  Starting Services" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Start backend service in new window
Write-Host "Starting backend service (port 8000)..." -ForegroundColor Yellow
Write-Host "Using .venv virtual environment..." -ForegroundColor Gray
$backendCmd = 'Write-Host "Kode AI Backend Service" -ForegroundColor Cyan; Write-Host ""; . .venv\Scripts\Activate.ps1; python -m kode.web.main'
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# Wait for backend to start
Write-Host "Waiting for backend to start..." -ForegroundColor Yellow
$maxWait = 30
$waited = 0
$backendReady = $false

while ($waited -lt $maxWait) {
    Start-Sleep -Seconds 1
    $waited++
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 1 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $backendReady = $true
            break
        }
    } catch {
        # Continue waiting
    }
    Write-Host "." -NoNewline
}

Write-Host ""

if (-not $backendReady) {
    Write-Host "Warning: Backend may not have started successfully (timeout ${maxWait}s)." -ForegroundColor Yellow
    Write-Host "Please check the backend window for error messages." -ForegroundColor Yellow
} else {
    Write-Host "[OK] Backend service started" -ForegroundColor Green
}

# Start frontend service in new window
Write-Host "Starting frontend service (port 3000)..." -ForegroundColor Yellow
$frontendCmd = 'Write-Host "Kode AI Frontend Service" -ForegroundColor Cyan; Write-Host ""; Set-Location web-frontend; npm run dev'
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host ""
Write-Host "==================================" -ForegroundColor Green
Write-Host "  Services Started!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: Frontend may take a few seconds to compile." -ForegroundColor Yellow
Write-Host "Wait for 'ready' message in frontend window before accessing." -ForegroundColor Yellow
Write-Host ""
Write-Host "To stop: Close the two new PowerShell windows or run .\stop-web.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to exit this script..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
