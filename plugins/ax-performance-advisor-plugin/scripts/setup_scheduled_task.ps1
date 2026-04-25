param(
  [Parameter(Mandatory=$true)][string]$TaskName,
  [Parameter(Mandatory=$true)][string]$PythonExe,
  [Parameter(Mandatory=$true)][string]$ScriptPath,
  [Parameter(Mandatory=$true)][string]$Arguments,
  [string]$At = "02:00"
)

$ErrorActionPreference = "Stop"
$action = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$ScriptPath`" $Arguments"
$trigger = New-ScheduledTaskTrigger -Daily -At $At
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Description "AX Performance Advisor scheduled collection/analysis" -Force | Out-Null
Write-Host "Scheduled task $TaskName registered"
