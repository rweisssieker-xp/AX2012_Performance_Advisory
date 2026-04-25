param(
  [Parameter(Mandatory=$true)][string]$OutputDirectory,
  [int]$SampleSeconds = 30,
  [string]$ComputerName = $env:COMPUTERNAME
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$counterSets = Get-Counter -ComputerName $ComputerName -ListSet * -ErrorAction SilentlyContinue |
  Where-Object { $_.CounterSetName -match "Dynamics|AX|AOS|Processor|Memory|PhysicalDisk" }

$paths = @()
foreach ($set in $counterSets) {
  if ($set.CounterSetName -match "Dynamics|AX|AOS") {
    $paths += $set.PathsWithInstances
  }
}

if ($paths.Count -eq 0) {
  $paths = @(
    "\Processor(_Total)\% Processor Time",
    "\Memory\Available MBytes",
    "\PhysicalDisk(_Total)\Avg. Disk sec/Read",
    "\PhysicalDisk(_Total)\Avg. Disk sec/Write"
  )
}

try {
  $sample = Get-Counter -ComputerName $ComputerName -Counter $paths -SampleInterval $SampleSeconds -MaxSamples 1 -ErrorAction Stop
  $rows = $sample.CounterSamples | Select-Object `
    @{Name="timestamp"; Expression={$sample.Timestamp.ToString("o")}},
    Path,
    InstanceName,
    CookedValue
  $rows | Export-Csv -NoTypeInformation -Encoding UTF8 -Path (Join-Path $OutputDirectory "aos_counters.csv")
}
catch {
  [pscustomobject]@{
    computer = $ComputerName
    error = $_.Exception.Message
    collected_at = [DateTimeOffset]::Now.ToString("o")
  } | Export-Csv -NoTypeInformation -Encoding UTF8 -Path (Join-Path $OutputDirectory "aos_counters.error.csv")
  Write-Warning "AOS/performance counter collection failed: $($_.Exception.Message)"
}
Write-Host "AOS/performance counter snapshot written to $OutputDirectory"
