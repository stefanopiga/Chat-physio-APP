# Validate Schema Dump - Pre-Commit Guard
# Usage: .\scripts\validate-schema-dump.ps1 supabase/sql_unico/00_consolidated_schema_v2_VERIFIED.sql

param(
    [Parameter(Mandatory=$true)]
    [string]$SchemaFile
)

Write-Host "Validating schema dump: $SchemaFile" -ForegroundColor Cyan

$errors = @()

# Check 1: File exists
if (-not (Test-Path $SchemaFile)) {
    Write-Host "FAIL: File not found" -ForegroundColor Red
    exit 1
}

# Check 2: NO INSERT/COPY statements (data leak)
$dataStatements = Select-String -Path $SchemaFile -Pattern "(INSERT INTO|COPY )" -CaseSensitive
if ($dataStatements) {
    Write-Host "CRITICAL: Data statements found!" -ForegroundColor Red
    $dataStatements | ForEach-Object { Write-Host "  Line $($_.LineNumber): $($_.Line)" }
    $errors += "Data statements present"
}

# Check 3: NO secrets pattern (usando pattern separati)
$secretPattern1 = Select-String -Path $SchemaFile -Pattern "password.*=.*\w{20,}" -CaseSensitive
$secretPattern2 = Select-String -Path $SchemaFile -Pattern "secret.*=.*\w{20,}" -CaseSensitive
$secretPattern3 = Select-String -Path $SchemaFile -Pattern "api_key.*=.*\w{20,}" -CaseSensitive

if ($secretPattern1 -or $secretPattern2 -or $secretPattern3) {
    Write-Host "CRITICAL: Potential secrets found!" -ForegroundColor Red
    $errors += "Secrets detected"
}

# Check 4: Required objects present
$requiredPatterns = @(
    "extensions.*vector",
    "CREATE TABLE.*documents",
    "CREATE TABLE.*document_chunks",
    "CREATE INDEX.*hnsw",
    "ENABLE ROW LEVEL SECURITY",
    "GRANT.*service_role"
)

foreach ($pattern in $requiredPatterns) {
    $match = Select-String -Path $SchemaFile -Pattern $pattern
    if (-not $match) {
        Write-Host "WARNING: Pattern not found: $pattern" -ForegroundColor Yellow
        $errors += "Missing pattern: $pattern"
    }
}

# Check 5: File size reasonable (< 100KB for schema-only)
$fileSize = (Get-Item $SchemaFile).Length / 1KB
if ($fileSize -gt 100) {
    Write-Host "WARNING: File size ${fileSize}KB > 100KB - possible data inclusion" -ForegroundColor Yellow
    $errors += "File size suspicious: ${fileSize}KB"
}

# Final verdict
if ($errors.Count -gt 0) {
    Write-Host "`nVALIDATION FAILED" -ForegroundColor Red
    Write-Host "Errors found: $($errors.Count)" -ForegroundColor Red
    $errors | ForEach-Object { Write-Host "  - $_" }
    exit 1
} else {
    Write-Host "`nVALIDATION PASSED" -ForegroundColor Green
    Write-Host "Schema dump is clean and ready for commit" -ForegroundColor Green
    exit 0
}
