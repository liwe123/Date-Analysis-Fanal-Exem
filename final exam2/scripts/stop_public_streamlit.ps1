param(
    [int]$Port = 8502,
    [switch]$KeepStreamlit
)

$ErrorActionPreference = "Continue"

function Stop-MatchingProcess {
    param(
        [string]$NamePattern,
        [string]$CommandLinePattern
    )

    $processes = Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -match $NamePattern -and
            $_.CommandLine -match $CommandLinePattern
        }

    foreach ($process in $processes) {
        Write-Host "Stopping PID $($process.ProcessId): $($process.Name)"
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

$escapedPort = [regex]::Escape("$Port")

Stop-MatchingProcess `
    -NamePattern "cloudflared" `
    -CommandLinePattern "127\.0\.0\.1:$escapedPort|localhost:$escapedPort"

if ($KeepStreamlit) {
    Write-Host "KeepStreamlit was set. Leaving Streamlit running."
    exit 0
}

$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
foreach ($listener in $listeners) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener.OwningProcess)"
    if ($process.CommandLine -match "streamlit" -and $process.CommandLine -match "app[/\\]streamlit_app\.py") {
        Write-Host "Stopping Streamlit PID $($process.ProcessId) on port $Port"
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
    }
}
