Param(
    [string]$EnvFile = ".env.staging.local",
    [int]$Requests = 300,
    [int]$WarmupIterations = 10,
    [string]$BaseUrl = $null,
    [string]$AdminToken = $null,
    [switch]$SkipWarmup,
    [switch]$DryRun
)

<#
.SYNOPSIS
    Esegue test P95 con warmup cache classification (Story 2.9).

.DESCRIPTION
    1. Warmup cache: popola Redis con documenti campione
    2. Test k6: misura P95 con cache pre-warmed
    3. Report: statistiche cache + confronto latenze

.EXAMPLE
    .\run_p95_with_warmup.ps1 -EnvFile .env.staging.local -Requests 300 -WarmupIterations 10

.NOTES
    Story 2.9: Classification Performance Optimization
    Target: P95 < 2s con hit rate > 90%
#>

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptRoot "..\..")
$reportsDir = Join-Path $repoRoot "reports"

if (-not (Test-Path $reportsDir)) {
    New-Item -ItemType Directory -Path $reportsDir | Out-Null
}

$envPath = Resolve-Path -Path (Join-Path $scriptRoot $EnvFile) -ErrorAction Stop

# Load env vars
Get-Content $envPath | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $idx = $line.IndexOf("=")
    if ($idx -lt 0) { return }
    $name = $line.Substring(0, $idx).Trim()
    $value = $line.Substring($idx + 1).Trim().Trim('"').Trim("'")
    Set-Item -Path "Env:$name" -Value $value
}

if (-not $BaseUrl) {
    $BaseUrl = if ($env:BASE_URL) { $env:BASE_URL } else { "http://localhost" }
}

if (-not $AdminToken) {
    $AdminToken = if ($env:ADMIN_BEARER) { 
        $env:ADMIN_BEARER -replace '^Bearer\s+', '' 
    } elseif ($env:AUTH_BEARER) {
        $env:AUTH_BEARER -replace '^Bearer\s+', ''
    } else {
        throw "ADMIN_BEARER non definito in $EnvFile"
    }
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Classification Cache P95 Test + Warmup" -ForegroundColor Cyan
Write-Host "  Story 2.9 - AC2.3 Validation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configurazione:" -ForegroundColor Yellow
Write-Host "  Base URL:          $BaseUrl"
Write-Host "  Total Requests:    $Requests"
Write-Host "  Warmup Iterations: $WarmupIterations"
Write-Host "  Env File:          $EnvFile"
Write-Host ""

if ($DryRun) {
    Write-Host "[INFO] Dry-run mode. Nessun comando eseguito." -ForegroundColor Yellow
    exit 0
}

# ========================================
# STEP 1: Cache Warmup
# ========================================
if (-not $SkipWarmup) {
    Write-Host "[1/4] Warmup Classification Cache..." -ForegroundColor Green
    Write-Host ""

    Push-Location (Join-Path $repoRoot "apps\api")
    try {
        $warmupScript = "..\..\scripts\perf\warmup_classification_cache.py"
        $warmupArgs = @(
            "--base-url", $BaseUrl,
            "--admin-token", $AdminToken,
            "--iterations", $WarmupIterations
        )
        
        & poetry run python $warmupScript @warmupArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Warmup cache fallito (exit code $LASTEXITCODE)"
        }
    } finally {
        Pop-Location
    }

    Write-Host ""
    Write-Host "✓ Warmup completato" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "[1/4] Warmup saltato (--SkipWarmup)" -ForegroundColor Yellow
    Write-Host ""
}

# ========================================
# STEP 2: Test k6 P95
# ========================================
Write-Host "[2/4] Esecuzione test k6 P95..." -ForegroundColor Green
Write-Host ""

$jsonFileName = "p95_k6_$timestamp.json"
$jsonPath = Join-Path $reportsDir $jsonFileName

$k6Args = @(
    "run",
    "--env", "BASE_URL=$BaseUrl",
    "--env", "REQUESTS=$Requests",
    "--env", "ADMIN_BEARER=Bearer $AdminToken",
    "--out", "json=$jsonPath",
    (Join-Path $scriptRoot "p95_local_test.js")
)

Push-Location $repoRoot
try {
    & k6 @k6Args
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "k6 terminato con exit code $LASTEXITCODE (possibili timeout)"
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "✓ Test k6 completato: $jsonPath" -ForegroundColor Green
Write-Host ""

# ========================================
# STEP 3: Generazione Summary
# ========================================
Write-Host "[3/4] Generazione summary report..." -ForegroundColor Green
Write-Host ""

$summaryFileName = "metrics-p95-$timestamp.md"
$summaryPath = Join-Path $reportsDir $summaryFileName

Push-Location (Join-Path $repoRoot "apps\api")
try {
    $relativeJson = "..\..\reports\$jsonFileName"
    $relativeSummary = "..\..\reports\$summaryFileName"
    & poetry run python ..\..\scripts\perf\summarize_p95.py $relativeJson | Out-File $relativeSummary -Encoding utf8
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Impossibile generare summary"
    }
} finally {
    Pop-Location
}

Write-Host "✓ Summary salvato: $summaryPath" -ForegroundColor Green
Write-Host ""

# ========================================
# STEP 4: Cache Stats Finali
# ========================================
Write-Host "[4/4] Statistiche finali cache..." -ForegroundColor Green
Write-Host ""

$cacheStatsUrl = "$BaseUrl/api/v1/admin/knowledge-base/classification-cache/metrics"
$headers = @{
    "Authorization" = "Bearer $AdminToken"
}

try {
    $response = Invoke-RestMethod -Uri $cacheStatsUrl -Headers $headers -Method Get -TimeoutSec 10
    $stats = $response.cache

    Write-Host "Cache Metrics:" -ForegroundColor Cyan
    Write-Host "  Enabled:    $($stats.enabled)"
    Write-Host "  Total Hits: $($stats.hits)"
    Write-Host "  Misses:     $($stats.misses)"
    
    $hitRatePercent = if ($stats.hit_rate) { [math]::Round($stats.hit_rate * 100, 2) } else { 0 }
    Write-Host "  Hit Rate:   $hitRatePercent%" -ForegroundColor $(if ($hitRatePercent -ge 90) { "Green" } else { "Yellow" })

    $latencyHit = $stats.latency_ms.hit
    $latencyMiss = $stats.latency_ms.miss

    Write-Host ""
    Write-Host "Latency (Cache HIT):" -ForegroundColor Cyan
    Write-Host "  P50: $($latencyHit.p50)ms"
    Write-Host "  P95: $($latencyHit.p95)ms"

    Write-Host ""
    Write-Host "Latency (Cache MISS):" -ForegroundColor Cyan
    Write-Host "  P50: $($latencyMiss.p50)ms"
    Write-Host "  P95: $($latencyMiss.p95)ms"

    # Salva stats JSON
    $statsJsonPath = Join-Path $reportsDir "cache-stats-$timestamp.json"
    $response | ConvertTo-Json -Depth 10 | Out-File $statsJsonPath -Encoding utf8
    Write-Host ""
    Write-Host "✓ Stats salvate: $statsJsonPath" -ForegroundColor Green

} catch {
    Write-Warning "Impossibile recuperare cache stats: $_"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Test Completato" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Output generati:" -ForegroundColor Yellow
Write-Host "  - k6 JSON:      $jsonPath"
Write-Host "  - Summary MD:   $summaryPath"
Write-Host "  - Cache Stats:  cache-stats-$timestamp.json"
Write-Host ""
Write-Host "Verifica:" -ForegroundColor Yellow
Write-Host "  1. Hit rate cache >= 90%"
Write-Host "  2. P95 sync-jobs < 2s (vs baseline >60s)"
Write-Host "  3. Speedup effettivo visibile in summary"
Write-Host ""

