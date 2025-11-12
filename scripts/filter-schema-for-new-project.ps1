# Filter Schema for New Supabase Project
# Rimuove funzioni/trigger extensions.* che causano errori ownership
# Usage: .\scripts\filter-schema-for-new-project.ps1

param(
    [string]$InputFile = "supabase\sql_unico\00_consolidated_schema_v2_VERIFIED.sql",
    [string]$OutputFile = "supabase\sql_unico\00_consolidated_schema_v2_CLEAN.sql"
)

Write-Host "Filtering schema for new project deployment..." -ForegroundColor Cyan

$content = Get-Content $InputFile -Raw

# Pattern per rimuovere blocchi completi di funzioni extensions
$patternsToRemove = @(
    # Funzioni extensions.* complete con corpo
    '(?s)CREATE OR REPLACE FUNCTION "extensions"\.\S+\(\).*?(?=\n\n(?:CREATE|ALTER|SET|GRANT|REVOKE|$))',
    
    # ALTER FUNCTION per extensions.*
    'ALTER FUNCTION "extensions"\.\S+ OWNER TO \S+;',
    
    # COMMENT su funzioni extensions
    'COMMENT ON FUNCTION "extensions"\.\S+ IS .+?;',
    
    # GRANT/REVOKE su funzioni extensions.*
    '(?:GRANT|REVOKE) .+ ON FUNCTION "extensions"\.\S+ (?:TO|FROM) .+?;'
)

foreach ($pattern in $patternsToRemove) {
    $content = $content -replace $pattern, ''
}

# Rimuovi linee vuote multiple consecutive
$content = $content -replace '(?m)^\s*$\n\s*$', ''

# Aggiungi note nel header
$headerNote = @"
--
-- ⚠️ CLEANED VERSION for new project deployment
-- Removed: extensions.* functions (auto-managed by Supabase)
-- Safe for: Fresh Supabase projects
--
"@

$content = $content -replace '(-- ============================================\n)', "`$1$headerNote"

# Scrivi output
$content | Out-File -FilePath $OutputFile -Encoding utf8 -NoNewline

$originalSize = (Get-Item $InputFile).Length / 1KB
$cleanSize = (Get-Item $OutputFile).Length / 1KB
$removed = $originalSize - $cleanSize

Write-Host "`n✅ Schema filtered successfully" -ForegroundColor Green
Write-Host "Original: ${originalSize}KB" -ForegroundColor Gray
Write-Host "Cleaned:  ${cleanSize}KB" -ForegroundColor Gray
Write-Host "Removed:  ${removed}KB (extensions functions)" -ForegroundColor Yellow
Write-Host "`nOutput: $OutputFile" -ForegroundColor Cyan
Write-Host "`nReady for deployment on new Supabase project" -ForegroundColor Green

