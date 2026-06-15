param(
    [int]$Port = 8502,
    [string]$HostAddress = "127.0.0.1",
    [switch]$NoTunnel
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$LogsDir = Join-Path $ProjectRoot "logs"
$HealthUrl = "http://${HostAddress}:${Port}/_stcore/health"
$AppUrl = "http://${HostAddress}:${Port}"

New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null
Set-Location $ProjectRoot

function Test-AppHealth {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Wait-AppHealth {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-AppHealth -Url $Url) {
            return $true
        }
        Start-Sleep -Seconds 2
    }

    return $false
}

if (Test-AppHealth -Url $HealthUrl) {
    Write-Host "Streamlit is already running: $AppUrl"
}
else {
    Write-Host "Starting Streamlit on $AppUrl ..."

    $stdoutLog = Join-Path $LogsDir "streamlit_public_${Port}.out.log"
    $stderrLog = Join-Path $LogsDir "streamlit_public_${Port}.err.log"

    Start-Process `
        -FilePath "python" `
        -ArgumentList @(
            "-m", "streamlit", "run", "app/streamlit_app.py",
            "--server.port", "$Port",
            "--server.address", "$HostAddress",
            "--server.headless", "true"
        ) `
        -WorkingDirectory $ProjectRoot `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -WindowStyle Hidden | Out-Null

    if (-not (Wait-AppHealth -Url $HealthUrl -TimeoutSeconds 90)) {
        Write-Host "Streamlit failed to become healthy. Recent error log:"
        if (Test-Path $stderrLog) {
            Get-Content $stderrLog -Tail 80
        }
        throw "Streamlit health check failed: $HealthUrl"
    }

    Write-Host "Streamlit is healthy: $AppUrl"
}

if ($NoTunnel) {
    Write-Host "NoTunnel was set. Skipping Cloudflare Tunnel startup."
    exit 0
}

if (-not (Get-Command "cloudflared" -ErrorAction SilentlyContinue)) {
    throw "cloudflared was not found. Install it with: winget install --id Cloudflare.cloudflared --exact"
}

Write-Host ""
Write-Host "Starting Cloudflare Quick Tunnel..."
Write-Host "Keep this terminal open. Press Ctrl+C to stop the public URL."
Write-Host ""

& cloudflared tunnel --protocol http2 --url $AppUrl
