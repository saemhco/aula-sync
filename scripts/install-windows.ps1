# Instala Aula Sync API en Windows Server (Python nativo, sin Docker).
# Requiere Python 3.12+: https://www.python.org/downloads/
# Ejecutar en PowerShell: .\scripts\install-windows.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Require-Python {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) {
        Write-Error "Python no encontrado. Instala 3.12+ y marca 'Add to PATH'."
    }
    $version = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    $parts = $version.Split(".")
    if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 12)) {
        Write-Error "Se requiere Python 3.12 o superior (detectado: $version)."
    }
    Write-Host "Python $version OK"
}

Require-Python

if (-not (Test-Path ".venv")) {
    Write-Host "Creando entorno virtual..."
    python -m venv .venv
}

Write-Host "Instalando dependencias..."
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\pip.exe install -r requirements.txt

$dataDir = Join-Path $Root "data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
    Write-Host "Carpeta data/ creada."
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.windows.example" ".env"
    Write-Host "Copiado .env.windows.example -> .env — edítalo antes de producción."
} else {
    Write-Host ".env ya existe; no se sobrescribe."
}

Write-Host ""
Write-Host "Listo. Siguiente paso:"
Write-Host "  1. Editar .env (SQL Server, Moodle, contraseñas)"
Write-Host "  2. .\scripts\run-api.ps1"
Write-Host "  Panel: http://localhost:8092/"
