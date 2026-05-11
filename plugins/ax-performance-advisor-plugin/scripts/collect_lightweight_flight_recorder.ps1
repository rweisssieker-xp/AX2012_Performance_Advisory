param(
  [Parameter(Mandatory=$true)][string]$ConnectionString,
  [Parameter(Mandatory=$true)][string]$OutputDirectory,
  [string]$AxDatabaseName = "",
  [string]$AosComputerName = $env:COMPUTERNAME,
  [int]$IntervalSeconds = 5,
  [int]$Samples = 12,
  [switch]$IncludeAosCounters,
  [switch]$IncludeEvents,
  [switch]$IncludeQueryStore
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$manifest = [ordered]@{
  mode = "server-side-lightweight-flight-recorder"
  startedAt = [DateTimeOffset]::Now.ToString("o")
  outputDirectory = (Resolve-Path $OutputDirectory).Path
  samplesRequested = $Samples
  intervalSeconds = $IntervalSeconds
  aosComputerName = $AosComputerName
  includeAosCounters = [bool]$IncludeAosCounters
  includeEvents = [bool]$IncludeEvents
  includeQueryStore = [bool]$IncludeQueryStore
  safety = "Read-only SQL DMVs, AX DB/session evidence, Windows counters and event logs. No client agent, no Trace Parser, no SQL Profiler."
  sampleDirectories = @()
}

for ($i = 1; $i -le $Samples; $i++) {
  $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $sampleDir = Join-Path $OutputDirectory ("sample-{0:D3}-{1}" -f $i, $stamp)
  New-Item -ItemType Directory -Force -Path $sampleDir | Out-Null
  Write-Host "Collecting lightweight flight recorder sample $i/$Samples into $sampleDir"

  try {
    $sqlArgs = @{
      ConnectionString = $ConnectionString
      OutputDirectory = $sampleDir
    }
    if ($IncludeQueryStore) {
      & "$PSScriptRoot\collect_sql_live_snapshot.ps1" @sqlArgs -IncludeQueryStore
    }
    else {
      & "$PSScriptRoot\collect_sql_live_snapshot.ps1" @sqlArgs
    }
  }
  catch {
    [pscustomobject]@{
      collector = "collect_sql_live_snapshot.ps1"
      error = $_.Exception.Message
      collected_at = [DateTimeOffset]::Now.ToString("o")
    } | Export-Csv -NoTypeInformation -Encoding UTF8 -Path (Join-Path $sampleDir "flight_recorder_sql.error.csv")
    Write-Warning "SQL snapshot failed: $($_.Exception.Message)"
  }

  if ($IncludeAosCounters) {
    try {
      & "$PSScriptRoot\collect_aos_counters.ps1" -OutputDirectory $sampleDir -SampleSeconds 1 -ComputerName $AosComputerName
    }
    catch {
      [pscustomobject]@{
        collector = "collect_aos_counters.ps1"
        error = $_.Exception.Message
        collected_at = [DateTimeOffset]::Now.ToString("o")
      } | Export-Csv -NoTypeInformation -Encoding UTF8 -Path (Join-Path $sampleDir "flight_recorder_aos.error.csv")
      Write-Warning "AOS counter snapshot failed: $($_.Exception.Message)"
    }
  }

  if ($IncludeEvents) {
    try {
      & "$PSScriptRoot\collect_ax_events.ps1" -OutputDirectory $sampleDir -Hours 1
    }
    catch {
      [pscustomobject]@{
        collector = "collect_ax_events.ps1"
        error = $_.Exception.Message
        collected_at = [DateTimeOffset]::Now.ToString("o")
      } | Export-Csv -NoTypeInformation -Encoding UTF8 -Path (Join-Path $sampleDir "flight_recorder_events.error.csv")
      Write-Warning "AX event snapshot failed: $($_.Exception.Message)"
    }
  }

  $manifest.sampleDirectories += $sampleDir
  if ($i -lt $Samples) {
    Start-Sleep -Seconds $IntervalSeconds
  }
}

$manifest.finishedAt = [DateTimeOffset]::Now.ToString("o")
$manifest.samplesCollected = $manifest.sampleDirectories.Count
$manifestPath = Join-Path $OutputDirectory "flight-recorder-manifest.json"
$manifest | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 -Path $manifestPath
Write-Host "Flight recorder manifest written to $manifestPath"
