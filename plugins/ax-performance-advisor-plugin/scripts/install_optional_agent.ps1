param(
  [Parameter(Mandatory=$true)][string]$ConfigPath,
  [string]$TaskName = "AXPA Optional Agent",
  [switch]$DryRun
)

$PluginRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$Python = "python"
$Script = Join-Path $PluginRoot "scripts\optional_agent.py"
$Action = New-ScheduledTaskAction -Execute $Python -Argument "`"$Script`" --config `"$ConfigPath`""
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Hours 1)

if ($DryRun) {
  [pscustomobject]@{
    TaskName = $TaskName
    Execute = $Python
    Argument = "`"$Script`" --config `"$ConfigPath`""
    Note = "Dry run only. No scheduled task registered."
  } | ConvertTo-Json -Depth 5
  exit 0
}

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Description "Optional AX Performance Advisor collector/report agent" | Out-Null
Write-Host "Registered optional AXPA scheduled task: $TaskName"
