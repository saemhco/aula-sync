# Arranca Aula Sync API en puerto 8092 (Windows Server).
# Ejecutar en PowerShell: .\scripts\run-api.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not (Test-Path ".venv")) {
    Write-Error "No hay .venv. Ejecuta primero: .\scripts\install-windows.ps1"
}
if (-not (Test-Path ".env")) {
    Write-Error "Falta .env. Copia .env.windows.example o ejecuta install-windows.ps1"
}

$env:PYTHONPATH = $Root
Write-Host "Aula Sync API en http://0.0.0.0:8092/"
& .\.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8092
