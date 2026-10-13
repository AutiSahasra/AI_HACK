# Start all services for AI RCA Copilot without Docker
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host " Starting AI Root Cause Analysis Copilot (Local Run) " -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $rootDir) { $rootDir = (Get-Location).Path }

# Identify correct Python virtual environment executable
$pythonExe = if (Test-Path "$rootDir\.venv\Scripts\python.exe") {
    "$rootDir\.venv\Scripts\python.exe"
} else {
    "python"
}

Write-Host "Using Python: $pythonExe" -ForegroundColor Gray

# 0. Clean up previous listeners on ports 5173, 8000, 8001
Get-NetTCPConnection -LocalPort 5173, 8000, 8001 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}

# 1. Check MongoDB
$mongoService = Get-Service -Name *mongo* -ErrorAction SilentlyContinue
if ($mongoService -and $mongoService.Status -ne 'Running') {
    Write-Host "Starting MongoDB service..." -ForegroundColor Yellow
    Start-Service -Name $mongoService.Name
}
Write-Host "[1/4] MongoDB is ready on port 27017." -ForegroundColor Green

# 2. Start Backend FastAPI
Write-Host "[2/4] Starting Backend (http://localhost:8000)..." -ForegroundColor Yellow
$backendJob = Start-Process $pythonExe -ArgumentList "-m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000" -WorkingDirectory $rootDir -PassThru

# 3. Start Demo App
Write-Host "[3/4] Starting Demo App (http://localhost:8001)..." -ForegroundColor Yellow
$demoJob = Start-Process $pythonExe -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port 8001" -WorkingDirectory "$rootDir\demo-app" -PassThru

# 4. Start Collector
Write-Host "Starting Log Collector..." -ForegroundColor Yellow
$collectorJob = Start-Process $pythonExe -ArgumentList "tailer.py" -WorkingDirectory "$rootDir\collector" -PassThru

# 5. Start Frontend
Write-Host "[4/4] Starting Frontend Vite Server (http://localhost:5173)..." -ForegroundColor Yellow
$frontendJob = Start-Process cmd.exe -ArgumentList "/c npm run dev" -WorkingDirectory "$rootDir\frontend" -PassThru

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Green
Write-Host " All services started successfully!" -ForegroundColor Green
Write-Host " Access the Web App at: http://localhost:5173" -ForegroundColor Cyan
Write-Host " API Documentation at:  http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host " Demo Service at:       http://localhost:8001/health" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Green
Write-Host "Default Login Accounts:" -ForegroundColor White
Write-Host " - Admin:     admin / adminpassword123 (or admin123)" -ForegroundColor White
Write-Host " - Approver:  approver / approverpassword123 (or approver123)" -ForegroundColor White
Write-Host " - Support:   support / supportpassword123 (or support123)" -ForegroundColor White
Write-Host "=====================================================" -ForegroundColor Green
