param(
  [Parameter(Mandatory=$true)][string]$Environment,
  [Parameter(Mandatory=$true)][string]$Server,
  [Parameter(Mandatory=$true)][string]$Database,
  [Parameter(Mandatory=$true)][string]$Evidence,
  [Parameter(Mandatory=$true)][string]$Out,
  [string]$PythonExe = "python",
  [string]$TaskName = "",
  [string]$At = "02:00",
  [switch]$Collect
)

$ErrorActionPreference = "Stop"

$pluginRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$pipeline = Join-Path $pluginRoot "scripts\run_axpa_pipeline.py"
$task = if ($TaskName) { $TaskName } else { "AXPA-$Environment" }
$collectArg = if ($Collect) { " --collect" } else { "" }
$arguments = @(
  "`"$pipeline`"",
  "--environment `"$Environment`"",
  "--server `"$Server`"",
  "--database `"$Database`"",
  "--evidence `"$Evidence`"",
  "--out `"$Out`"",
  $collectArg
) -join " "

$action = New-ScheduledTaskAction -Execute $PythonExe -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 4)

Register-ScheduledTask `
  -TaskName $task `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "AX Performance Advisor pipeline for $Environment" `
  -Force | Out-Null

[pscustomobject]@{
  taskName = $task
  environment = $Environment
  server = $Server
  database = $Database
  evidence = $Evidence
  out = $Out
  schedule = $At
  collect = [bool]$Collect
  pipeline = $pipeline
} | ConvertTo-Json -Depth 4
