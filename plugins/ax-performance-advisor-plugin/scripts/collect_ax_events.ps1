param(
  [Parameter(Mandatory=$true)][string]$OutputDirectory,
  [int]$Hours = 24,
  [string]$LogName = "Application"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$since = (Get-Date).AddHours(-1 * $Hours)

$events = Get-WinEvent -FilterHashtable @{ LogName = $LogName; StartTime = $since } |
  Where-Object {
    $_.ProviderName -match "Dynamics|Microsoft Dynamics|AOS" -or
    $_.Message -match "Dynamics AX|AOS|Batch|SysOperation"
  } |
  Select-Object TimeCreated, ProviderName, Id, LevelDisplayName, Message

$events | Export-Csv -NoTypeInformation -Encoding UTF8 -Path (Join-Path $OutputDirectory "ax_events.csv")
Write-Host "AX-related event log snapshot written to $OutputDirectory"
