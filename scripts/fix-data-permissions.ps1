# Repara permisos de data/settings.db en Windows (solo-lectura).
# Ejecutar en PowerShell como Administrador: .\scripts\fix-data-permissions.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$dataDir = Join-Path $Root "data"

if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
    Write-Host "Creada carpeta data/"
}

attrib -R "$dataDir\*" /S /D 2>$null
Get-ChildItem -Path $dataDir -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $_.IsReadOnly = $false
}

$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
icacls $dataDir /grant "${user}:(OI)(CI)F" /T | Out-Null

Write-Host "Permisos OK en $dataDir"
Write-Host "Reinicia la API: .\scripts\run-api.ps1"
