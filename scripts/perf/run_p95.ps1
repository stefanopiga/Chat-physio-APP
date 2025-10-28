Param(
    [string]$EnvFile = ".env.staging.local",
    [int]$Requests = 300,
    [string]$BaseUrl = $null,
    [int]$WarmupIterations = 5,
    [double]$MinHitRate = 0.9,
    [switch]$SkipWarmup,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptRoot "..\..")
$reportsDir = Join-Path $repoRoot "reports"

if (-not (Test-Path $reportsDir)) {
    New-Item -ItemType Directory -Path $reportsDir | Out-Null
}

$envPath = Resolve-Path -Path (Join-Path $scriptRoot $EnvFile) -ErrorAction Stop

Get-Content $envPath | ForEach-Object {
    $line = $_.Trim()
    if (-not $line) { return }
    if ($line.StartsWith("#")) { return }
    $idx = $line.IndexOf("=")
    if ($idx -lt 0) { return }
    $name = $line.Substring(0, $idx).Trim()
    $value = $line.Substring($idx + 1).Trim()
    if ($value.StartsWith('"') -and $value.EndsWith('"')) {
        $value = $value.Trim('"')
    }
    if ($value.StartsWith("'") -and $value.EndsWith("'")) {
        $value = $value.Trim("'")
    }
    Set-Item -Path "Env:$name" -Value $value
}

if (-not $BaseUrl) {
    if ($env:BASE_URL) {
        $BaseUrl = $env:BASE_URL
    } else {
        throw "BASE_URL non definita né nel file $EnvFile né nel parametro --BaseUrl."
    }
}

$adminToken = $env:ADMIN_BEARER
if (-not $adminToken) {
    throw "ADMIN_BEARER non impostato. Specificare il token admin nel file $EnvFile o nell'ambiente."
}

# Remove "Bearer " prefix if present (warmup script adds it automatically)
if ($adminToken.StartsWith("Bearer ")) {
    $adminToken = $adminToken.Substring(7)
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$jsonFileName = "p95_k6_$timestamp.json"
$summaryFileName = "metrics-p95-$timestamp.md"
$jsonPath = Join-Path $reportsDir $jsonFileName
$summaryPath = Join-Path $reportsDir $summaryFileName

$k6Args = @(
    "run",
    "--env", "BASE_URL=$BaseUrl",
    "--env", "REQUESTS=$Requests",
    "--out", "json=$jsonPath",
    (Join-Path $scriptRoot "p95_local_test.js")
)

Write-Host "[INFO] k6 command: k6 $($k6Args -join ' ')"

if ($DryRun) {
    Write-Host "[INFO] Dry-run completato. Nessun comando eseguito."
    exit 0
}

$apiBaseUrl = $BaseUrl.TrimEnd("/")

if (-not $SkipWarmup) {
    Write-Host "[INFO] Avvio warmup cache classificazione..."
    $apiDir = Join-Path $repoRoot "apps\api"
    Push-Location $apiDir
    try {
        $warmupArgs = @(
            "run",
            "python",
            "..\..\scripts/perf/warmup_classification_cache.py",
            "--base-url", $BaseUrl,
            "--admin-token", $adminToken,
            "--iterations", $WarmupIterations
        )
        Write-Host "[INFO] poetry $($warmupArgs -join ' ')"
        & poetry @warmupArgs
        $warmupExitCode = $LASTEXITCODE
        if ($warmupExitCode -ne 0) {
            Write-Host "[WARNING] Warmup terminato con exit code $warmupExitCode (rate limiting atteso)"
        }

        $metricsUrl = "$apiBaseUrl/api/v1/admin/knowledge-base/classification-cache/metrics"
        Write-Host "[INFO] Verifica hit-rate cache tramite $metricsUrl"
        $metrics = Invoke-RestMethod -Uri $metricsUrl -Headers @{ Authorization = "Bearer $adminToken" } -Method Get -TimeoutSec 15
        $cacheStats = $metrics.cache
        if (-not $cacheStats) {
            throw "Risposta metrics priva di sezione 'cache'."
        }

        $hitRate = $cacheStats.hit_rate
        if ($null -eq $hitRate) {
            throw "Hit-rate non disponibile nelle metriche (cache.hit_rate = null)."
        }

        Write-Host ("[INFO] Hit-rate corrente: {0:P2}" -f [double]$hitRate)
        if ([double]$hitRate -lt $MinHitRate) {
            $percent = [math]::Round([double]$hitRate * 100, 2)
            throw "Hit-rate ${percent}% inferiore alla soglia minima $([math]::Round($MinHitRate * 100, 2))%. Verificare warmup."
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[INFO] Warmup cache saltato (--SkipWarmup)."
}

Push-Location $repoRoot
try {
    & k6 @k6Args
    if ($LASTEXITCODE -ne 0) {
        throw "k6 terminato con exit code $LASTEXITCODE"
    }
    Write-Host "[INFO] Output k6 salvato in $jsonPath"

    Push-Location (Join-Path $repoRoot "apps\api")
    try {
        $relativeJson = "..\..\reports\$jsonFileName"
        $relativeSummary = "..\..\reports\$summaryFileName"
        & poetry run python ..\..\scripts\perf\summarize_p95.py $relativeJson | Out-File $relativeSummary -Encoding utf8
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "[WARN] Impossibile generare il summary per $jsonFileName"
        } else {
            Write-Host "[INFO] Summary salvato in $summaryPath"
        }
    } finally {
        Pop-Location
    }
} finally {
    Pop-Location
}

Write-Host "[INFO] Esecuzione completata. Verificare i log e confrontare i valori con la dashboard Supabase."
