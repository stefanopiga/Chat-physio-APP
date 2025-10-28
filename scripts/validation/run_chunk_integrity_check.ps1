# Script PowerShell per verifica integrità chunk
# Equivalente Windows di run_chunk_integrity_check.sh

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Verifica Integrità Chunk - Story 2.11 AC4" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Ottieni root directory del progetto
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootPath = Split-Path -Parent (Split-Path -Parent $scriptPath)

if ($env:DATABASE_URL) {
    Write-Host "[OK] DATABASE_URL configurata" -ForegroundColor Green
    Write-Host "--- Verifica con script Python standalone ---" -ForegroundColor Yellow
    Push-Location $rootPath
    python scripts/validation/verify_chunk_ids.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "[FAIL] Verifica Python fallita" -ForegroundColor Red
        Pop-Location
        exit $LASTEXITCODE
    }
    Write-Host ""
    Pop-Location
} else {
    Write-Host "[WARN] DATABASE_URL non configurata: skip verifica diretta sul database" -ForegroundColor Yellow
    Write-Host ""
}

# Opzione 2: Esegui test pytest di integrità
Write-Host "--- Verifica con pytest (test di integrità) ---" -ForegroundColor Yellow
Push-Location "$rootPath\apps\api"
poetry run pytest tests/test_chunk_integrity.py -v
$pytestResult = $LASTEXITCODE
Pop-Location

if ($pytestResult -ne 0) {
    Write-Host ""
    Write-Host "[FAIL] Test pytest falliti" -ForegroundColor Red
    exit $pytestResult
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "[SUCCESS] Verifica completata con successo!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
