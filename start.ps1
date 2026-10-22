param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8001
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Assert-Success([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "Echec : $Step" }
}

if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    python -m venv .venv
    Assert-Success 'creation de l environnement Python'
}
$projectPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
& $projectPython -m pip install -r requirements-web.txt
Assert-Success 'installation des dependances'
& $projectPython scripts/setup_local.py
Assert-Success 'configuration locale'
docker compose up -d --wait
Assert-Success 'demarrage de PostgreSQL (Docker Desktop doit etre ouvert)'
& $projectPython manage.py migrate --noinput
Assert-Success 'creation des tables'
Write-Host "Memo est disponible sur http://127.0.0.1:$Port - Ctrl+C pour arreter."
& $projectPython manage.py runserver "127.0.0.1:$Port"
