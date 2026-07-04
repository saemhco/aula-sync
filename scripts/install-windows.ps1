# Instala Aula Sync API en Windows Server (Python nativo, sin Docker).
# Requiere Python 3.10+: https://www.python.org/downloads/
# Ejecutar en PowerShell: .\scripts\install-windows.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Require-Python {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) {
        Write-Error "Python no encontrado. Instala 3.10+ y marca Add to PATH."
    }
    $version = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    $parts = $version.Split(".")
    if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 10)) {
        Write-Error "Se requiere Python 3.10 o superior (detectado: $version)."
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
# Windows: quitar atributo solo-lectura en data/ (evita sqlite3.OperationalError)
Get-ChildItem -Path $dataDir -Force -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.PSIsContainer) { return }
    $_.IsReadOnly = $false
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.windows.example" ".env"
    Write-Host "Copiado .env.windows.example -> .env (editarlo antes de produccion)."
} else {
    Write-Host ".env ya existe; no se sobrescribe."
}

Write-Host ""
Write-Host "Listo. Siguiente paso:"
Write-Host "  1. Editar .env (SQL Server, Moodle, credenciales)"
Write-Host "  2. .\scripts\run-api.ps1"
Write-Host "  Panel: http://localhost:8092/"
