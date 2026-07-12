$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$PythonExe = Join-Path $BackendDir ".venv\Scripts\python.exe"
$BackendPort = 8000
$FrontendPort = 5173

function Stop-PortProcess {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    $processIds = $connections |
        Where-Object { $_.OwningProcess -and $_.OwningProcess -ne 0 } |
        Select-Object -ExpandProperty OwningProcess -Unique

    foreach ($processId in $processIds) {
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "Stopping port $Port process: $($process.ProcessName) ($processId)"
            Stop-Process -Id $processId -Force
        }
    }
}

if (-not (Test-Path $PythonExe)) {
    throw "Backend Python not found: $PythonExe"
}

if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    throw "Frontend node_modules not found. Run npm install in frontend first."
}

Write-Host "Restarting RAG Medical Assistant dev servers..."
Stop-PortProcess -Port $BackendPort
Stop-PortProcess -Port $FrontendPort

$backendCommand = "cd /d `"$BackendDir`" && `"$PythonExe`" -m uvicorn main:app --reload --host 127.0.0.1 --port $BackendPort > dev-server.log 2> dev-server.err.log"
$frontendCommand = "cd /d `"$FrontendDir`" && npm.cmd run dev -- --host 127.0.0.1 --port $FrontendPort > dev-server.log 2> dev-server.err.log"

Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $backendCommand -WorkingDirectory $BackendDir
Start-Sleep -Seconds 2
Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $frontendCommand -WorkingDirectory $FrontendDir

Write-Host ""
Write-Host "Backend:  http://127.0.0.1:$BackendPort"
Write-Host "API docs: http://127.0.0.1:$BackendPort/docs"
Write-Host "Frontend: http://localhost:$FrontendPort"
Write-Host ""
Write-Host "Two terminal windows have been opened. Close them when you want to stop the servers."
