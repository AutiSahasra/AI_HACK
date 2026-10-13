# Stop local services
Write-Host "Stopping local AI RCA Copilot processes..." -ForegroundColor Yellow

Get-Process -Name node, python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*AI_HACK*" -or $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*vite*" -or $_.CommandLine -like "*tailer.py*"
} | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "Services stopped." -ForegroundColor Green
