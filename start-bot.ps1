# Starts the paper-trading bot and the dashboard website if they are not
# already running. Registered as a Windows scheduled task at logon so the
# bot survives reboots while it still lives on this PC.

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ft = Join-Path $root ".venv\Scripts\freqtrade.exe"
$py = Join-Path $root ".venv\Scripts\python.exe"

$botRunning = Get-Process freqtrade -ErrorAction SilentlyContinue
if (-not $botRunning) {
    Start-Process -FilePath $ft `
        -ArgumentList 'trade', '--config', 'config.json', '--userdir', 'user_data', '--strategy', 'TrendFollowStrategy', '--logfile', 'user_data\logs\freqtrade.log' `
        -WorkingDirectory $root -WindowStyle Hidden
}

$dashRunning = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'uvicorn' -and $_.CommandLine -match 'app:app' }
if (-not $dashRunning) {
    Start-Process -FilePath $py `
        -ArgumentList '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', '3000' `
        -WorkingDirectory (Join-Path $root 'dashboard') -WindowStyle Hidden
}
