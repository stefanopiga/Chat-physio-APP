# Script Helper per Query Verifica Supabase
# Uso: .\scripts\supabase-verify.ps1 -ConnectionString "postgresql://..." [-Command "inspect"|"init"]

param(
    [Parameter(Mandatory=$false)]
    [string]$ConnectionString = $env:DATABASE_URL,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("inspect", "init", "link", "help")]
    [string]$Command = "help"
)

$SupabaseCLI = "C:\Users\user\scoop\shims\supabase.exe"

# Verifica CLI installato
if (-not (Test-Path $SupabaseCLI)) {
    Write-Error "Supabase CLI non trovato. Installare con: scoop install supabase"
    exit 1
}

Write-Host "=== Supabase CLI Verification Helper ===" -ForegroundColor Cyan
Write-Host ""

switch ($Command) {
    "inspect" {
        if (-not $ConnectionString) {
            Write-Error "Connection string richiesta. Specificare -ConnectionString o impostare DATABASE_URL"
            exit 1
        }
        
        Write-Host "[1/5] Verifica Table Statistics..." -ForegroundColor Yellow
        & $SupabaseCLI inspect db table-stats --db-url $ConnectionString
        
        Write-Host ""
        Write-Host "[2/5] Verifica Index Statistics..." -ForegroundColor Yellow
        & $SupabaseCLI inspect db index-stats --db-url $ConnectionString
        
        Write-Host ""
        Write-Host "[3/5] Verifica Database Stats (Cache Hit, Sizes)..." -ForegroundColor Yellow
        & $SupabaseCLI inspect db db-stats --db-url $ConnectionString
        
        Write-Host ""
        Write-Host "[4/5] Verifica Role Stats..." -ForegroundColor Yellow
        & $SupabaseCLI inspect db role-stats --db-url $ConnectionString
        
        Write-Host ""
        Write-Host "[5/5] Verifica Replication Slots..." -ForegroundColor Yellow
        & $SupabaseCLI inspect db replication-slots --db-url $ConnectionString
        
        Write-Host ""
        Write-Host "=== Verifica completata ===" -ForegroundColor Green
    }
    
    "init" {
        Write-Host "Inizializzazione progetto Supabase locale..." -ForegroundColor Yellow
        & $SupabaseCLI init
        
        Write-Host ""
        Write-Host "Progetto inizializzato. Per avviare stack locale:" -ForegroundColor Green
        Write-Host "  supabase start" -ForegroundColor Cyan
    }
    
    "link" {
        Write-Host "Link progetto Supabase esistente..." -ForegroundColor Yellow
        Write-Host "1. Login prima con: supabase login" -ForegroundColor Cyan
        Write-Host "2. Poi esegui: supabase link --project-ref <your-ref>" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Project ref visibile in: Supabase Dashboard → Settings → General" -ForegroundColor Yellow
    }
    
    "help" {
        Write-Host "Comandi disponibili:" -ForegroundColor Green
        Write-Host ""
        Write-Host "  .\scripts\supabase-verify.ps1 -Command inspect -ConnectionString 'postgresql://...'" -ForegroundColor Cyan
        Write-Host "    → Esegue verifiche complete su database remoto" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  .\scripts\supabase-verify.ps1 -Command init" -ForegroundColor Cyan
        Write-Host "    → Inizializza progetto Supabase locale" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  .\scripts\supabase-verify.ps1 -Command link" -ForegroundColor Cyan
        Write-Host "    → Mostra istruzioni per linkare progetto esistente" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Environment Variables:" -ForegroundColor Green
        Write-Host "  DATABASE_URL: $ConnectionString" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Documentazione completa: SUPABASE_CLI_USAGE.md" -ForegroundColor Yellow
    }
}

