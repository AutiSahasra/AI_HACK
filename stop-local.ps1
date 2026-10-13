# Stop local services
Write-Host "Stopping local AI RCA Copilot processes..." -ForegroundColor Yellow

# 1. Kill listeners on ports 5173, 8000, 8001
Get-NetTCPConnection -LocalPort 5173, 8000, 8001 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}

# 2. Kill python/node processes matching AI_HACK workspace
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    ($_.Name -match "python.exe" -or $_.Name -match "node.exe") -and
    ($_.CommandLine -like "*AI-HACK*" -or $_.CommandLine -like "*AI_HACK*" -or $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*tailer.py*")
} | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

Write-Host "Services stopped." -ForegroundColor Green
