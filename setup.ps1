param([switch]$Recreate)

$ErrorActionPreference = "Stop"
$venv = ".venv"

if ($Recreate -and (Test-Path $venv)) {
    Write-Host "Removendo $venv existente..."
    Remove-Item -Recurse -Force $venv
}

if (-not (Test-Path $venv)) {
    Write-Host "Criando venv em $venv..."
    py -m venv $venv
}

$python = Join-Path $venv "Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt

Write-Host ""
Write-Host "Pronto. Ative com:  .\$venv\Scripts\Activate.ps1"
Write-Host "Ou rode direto:     .\$venv\Scripts\python.exe main.py"
