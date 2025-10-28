$ErrorActionPreference = "Stop"

$rootDir = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$timestamp = (Get-Date -AsUTC).ToString("yyyyMMddTHHmmssZ")
$outputDir = Join-Path $rootDir "ingestion\temp\watcher-debug\$timestamp"
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

function Capture-Command {
    param (
        [string]$FilePath,
        [string[]]$Command
    )

    $cmdLine = '$ ' + ($Command -join ' ')
    $exe = $Command[0]
    $args = @()
    if ($Command.Length -gt 1) {
        $args = $Command[1..($Command.Length - 1)]
    }

    try {
        $result = & $exe @args 2>&1
    }
    catch {
        $result = $_.Exception.Message
    }

    $cmdLine | Out-File -FilePath $FilePath -Encoding UTF8
    $result | Out-File -FilePath $FilePath -Encoding UTF8 -Append
}

$composeCommand = $null
if (Get-Command docker -ErrorAction SilentlyContinue) {
    try {
        docker compose version *> $null
        $composeCommand = @("docker", "compose")
    }
    catch {
        $composeCommand = $null
    }
}

if (-not $composeCommand -and (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    $composeCommand = @("docker-compose")
}

if ($composeCommand) {
    Capture-Command (Join-Path $outputDir "docker-ps.txt") ($composeCommand + "ps")
    Capture-Command (Join-Path $outputDir "docker-logs-api.txt") ($composeCommand + @("logs", "-n", "2000", "applicazione-api"))
    Capture-Command (Join-Path $outputDir "docker-logs-worker.txt") ($composeCommand + @("logs", "-n", "2000", "applicazione-celery-worker"))
    Capture-Command (Join-Path $outputDir "docker-logs-redis.txt") ($composeCommand + @("logs", "-n", "2000", "fisio-rag-redis"))
}
else {
    "docker compose not available" | Out-File -FilePath (Join-Path $outputDir "docker-info.txt") -Encoding UTF8
}

Capture-Command (Join-Path $outputDir "disk-usage.txt") @("PowerShell", "-NoProfile", "-Command", "Get-Volume | Select DriveLetter, FileSystemLabel, @{Name='Free(GB)';Expression={[math]::Round($_.SizeRemaining/1GB,2)}}, @{Name='Total(GB)';Expression={[math]::Round($_.Size/1GB,2)}}")

Capture-Command (Join-Path $outputDir "git-info.txt") @("git", "-C", $rootDir, "status", "--short")
Capture-Command (Join-Path $outputDir "git-commit.txt") @("git", "-C", $rootDir, "rev-parse", "HEAD")

if (Get-Command poetry -ErrorAction SilentlyContinue) {
    Capture-Command (Join-Path $outputDir "settings.json") @("poetry", "--directory", (Join-Path $rootDir "apps\api"), "run", "python", "-m", "api.debug.print_settings")
}
else {
    "poetry not available" | Out-File -FilePath (Join-Path $outputDir "settings.json") -Encoding UTF8
}

"Watcher diagnostics collected in $outputDir"

