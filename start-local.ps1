# Start all services for AI RCA Copilot without Docker
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host " Starting AI Root Cause Analysis Copilot (Local Run) " -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Check MongoDB
$mongoService = Get-Service -Name *mongo* -ErrorAction SilentlyContinue
if ($mongoService -and $mongoService.Status -ne 'Running') {
    Write-Host "Starting MongoDB service..." -ForegroundColor Yellow
    Start-Service -Name $mongoService.Name
}
Write-Host "[1/4] MongoDB is running on port 27017." -ForegroundColor Green

# 2. Start Backend FastAPI
Write-Host "[2/4] Starting Backend (http://localhost:8000)..." -ForegroundColor Yellow
$backendJob = Start-Process python -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8000" -WorkingDirectory "$rootDir\backend" -PassThru

# 3. Start Demo App
Write-Host "[3/4] Starting Demo App (http://localhost:8001)..." -ForegroundColor Yellow
$demoJob = Start-Process python -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port 8001" -WorkingDirectory "$rootDir\demo-app" -PassThru

# 4. Start Collector
Write-Host "Starting Log Collector..." -ForegroundColor Yellow
$collectorJob = Start-Process python -ArgumentList "tailer.py" -WorkingDirectory "$rootDir\collector" -PassThru

# 5. Start Frontend
Write-Host "[4/4] Starting Frontend Vite Server (http://localhost:5173)..." -ForegroundColor Yellow
$frontendJob = Start-Process cmd.exe -ArgumentList "/c npm run dev" -WorkingDirectory "$rootDir\frontend" -PassThru

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Green
Write-Host " All services started successfully!" -ForegroundColor Green
Write-Host " Access the Web App at: http://localhost:5173" -ForegroundColor Cyan
Write-Host " API Documentation at:  http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Green
Write-Host "Default Login Accounts:" -ForegroundColor White
Write-Host " - Admin:     admin / admin123" -ForegroundColor White
Write-Host " - Approver:  approver / approver123" -ForegroundColor White
Write-Host " - Support:   support / support123" -ForegroundColor White
Write-Host "=====================================================" -ForegroundColor Green
