param(
  [Parameter(Mandatory=$true)][string]$ConnectionString,
  [Parameter(Mandatory=$true)][string]$OutputDirectory,
  [int]$Days = 14
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

function Invoke-AxpaSqlQuery {
  param([string]$Query, [string]$OutputFile)
  $connection = [System.Data.SqlClient.SqlConnection]::new($ConnectionString)
  $command = $connection.CreateCommand()
  $command.CommandText = $Query
  $command.CommandTimeout = 180
  $adapter = [System.Data.SqlClient.SqlDataAdapter]::new($command)
  $table = [System.Data.DataTable]::new()
  try {
    [void]$adapter.Fill($table)
    $table | Export-Csv -NoTypeInformation -Encoding UTF8 -Path (Join-Path $OutputDirectory $OutputFile)
  }
  catch {
    [pscustomobject]@{
      output_file = $OutputFile
      error = $_.Exception.Message
      collected_at = [DateTimeOffset]::Now.ToString("o")
    } | Export-Csv -NoTypeInformation -Encoding UTF8 -Path (Join-Path $OutputDirectory ($OutputFile + ".error.csv"))
    Write-Warning "Skipping $OutputFile because query failed: $($_.Exception.Message)"
  }
  finally {
    $connection.Dispose()
    $adapter.Dispose()
  }
}

function Test-AxpaColumn {
  param([string]$TableName, [string]$ColumnName)
  $connection = [System.Data.SqlClient.SqlConnection]::new($ConnectionString)
  $command = $connection.CreateCommand()
  $command.CommandText = "SELECT CASE WHEN COL_LENGTH(@table, @column) IS NULL THEN 0 ELSE 1 END"
  [void]$command.Parameters.AddWithValue("@table", $TableName)
  [void]$command.Parameters.AddWithValue("@column", $ColumnName)
  try {
    $connection.Open()
    return ([int]$command.ExecuteScalar()) -eq 1
  }
  finally {
    $connection.Dispose()
  }
}

function Get-AxpaColumnExpression {
  param([string]$TableName, [string[]]$Candidates, [string]$Alias, [string]$Default = "''")
  foreach ($candidate in $Candidates) {
    if (Test-AxpaColumn -TableName $TableName -ColumnName $candidate) {
      return "CAST($candidate AS nvarchar(200)) AS $Alias"
    }
  }
  return "CAST($Default AS nvarchar(200)) AS $Alias"
}

Invoke-AxpaSqlQuery -OutputFile "ax_schema_discovery.csv" -Query @"
SELECT
  TABLE_SCHEMA AS table_schema,
  TABLE_NAME AS table_name,
  CASE
    WHEN TABLE_NAME IN ('BATCHJOB','BATCH','SYSCLIENTSESSIONS','AIFMESSAGELOG','RETAILTRANSACTIONTABLE') THEN 'expected'
    WHEN TABLE_NAME LIKE '%BATCH%' THEN 'batch-candidate'
    WHEN TABLE_NAME LIKE '%SYSCLIENT%' OR TABLE_NAME LIKE '%SESSION%' THEN 'session-candidate'
    WHEN TABLE_NAME LIKE '%AIF%' THEN 'aif-candidate'
    WHEN TABLE_NAME LIKE '%RETAIL%' THEN 'retail-candidate'
    ELSE 'context'
  END AS discovery_type
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
  AND (
    TABLE_NAME IN ('BATCHJOB','BATCH','SYSCLIENTSESSIONS','AIFMESSAGELOG','RETAILTRANSACTIONTABLE','INVENTTRANS','GENERALJOURNALACCOUNTENTRY')
    OR TABLE_NAME LIKE '%BATCH%'
    OR TABLE_NAME LIKE '%SYSCLIENT%'
    OR TABLE_NAME LIKE '%SESSION%'
    OR TABLE_NAME LIKE '%AIF%'
    OR TABLE_NAME LIKE '%RETAIL%'
  )
ORDER BY discovery_type, TABLE_SCHEMA, TABLE_NAME;
"@

$sessionAosExpr = Get-AxpaColumnExpression -TableName "dbo.SYSCLIENTSESSIONS" -Candidates @("AOSID","SERVERID","AOSINSTANCE","SERVERNAME") -Alias "aos"
$sessionComputerExpr = Get-AxpaColumnExpression -TableName "dbo.SYSCLIENTSESSIONS" -Candidates @("CLIENTCOMPUTER","CLIENTMACHINE","COMPUTERNAME") -Alias "client_computer"
$sessionStatusExpr = Get-AxpaColumnExpression -TableName "dbo.SYSCLIENTSESSIONS" -Candidates @("STATUS","SESSIONSTATUS") -Alias "status"
$sessionLoginExpr = Get-AxpaColumnExpression -TableName "dbo.SYSCLIENTSESSIONS" -Candidates @("LOGINDATETIME","CREATEDDATETIME") -Alias "login_time"
$sessionUserExpr = Get-AxpaColumnExpression -TableName "dbo.SYSCLIENTSESSIONS" -Candidates @("USERID","USERID2") -Alias "user_id"
$sessionClientTypeExpr = Get-AxpaColumnExpression -TableName "dbo.SYSCLIENTSESSIONS" -Candidates @("CLIENTTYPE","SESSIONTYPE") -Alias "client_type"

$aifTypeExpr = Get-AxpaColumnExpression -TableName "dbo.AIFMESSAGELOG" -Candidates @("MESSAGETYPE","MESSAGENAME","SERVICEOPERATION","PORTNAME") -Alias "message_type"
$aifStatusExpr = Get-AxpaColumnExpression -TableName "dbo.AIFMESSAGELOG" -Candidates @("STATUS","MESSAGESTATUS","STATE") -Alias "status"
$aifDirectionExpr = Get-AxpaColumnExpression -TableName "dbo.AIFMESSAGELOG" -Candidates @("DIRECTION","MESSAGEDIRECTION") -Alias "direction"
$aifCreatedExpr = Get-AxpaColumnExpression -TableName "dbo.AIFMESSAGELOG" -Candidates @("CREATEDDATETIME","CREATEDDATE") -Alias "created_time"
$aifModifiedExpr = Get-AxpaColumnExpression -TableName "dbo.AIFMESSAGELOG" -Candidates @("MODIFIEDDATETIME","ENDDATETIME","CREATEDDATETIME") -Alias "modified_time"

Invoke-AxpaSqlQuery -OutputFile "batch_jobs.csv" -Query @"
IF OBJECT_ID('dbo.BATCHJOB') IS NOT NULL
BEGIN
  SELECT TOP (1000)
    CAST(bj.RECID AS nvarchar(40)) AS job_id,
    COALESCE(NULLIF(bj.CAPTION, ''), CAST(bj.RECID AS nvarchar(40))) AS job_name,
    CAST('' AS nvarchar(100)) AS class_name,
    CAST('' AS nvarchar(40)) AS batch_group,
    CAST('' AS nvarchar(80)) AS aos,
    CAST('' AS nvarchar(20)) AS company,
    CAST(bj.STATUS AS nvarchar(40)) AS status,
    bj.STARTDATETIME AS start_time,
    bj.ENDDATETIME AS end_time,
    DATEDIFF(second, bj.STARTDATETIME, bj.ENDDATETIME) AS duration_seconds,
    0 AS sla_target_seconds
  FROM dbo.BATCHJOB bj
  WHERE bj.STARTDATETIME >= DATEADD(day, -$Days, SYSUTCDATETIME())
  ORDER BY bj.STARTDATETIME DESC;
END
"@

Invoke-AxpaSqlQuery -OutputFile "batch_tasks.csv" -Query @"
IF OBJECT_ID('dbo.BATCH') IS NOT NULL
BEGIN
  SELECT TOP (5000)
    CAST(b.RECID AS nvarchar(40)) AS task_id,
    CAST(b.BATCHJOBID AS nvarchar(40)) AS job_id,
    b.CLASSNUMBER AS class_number,
    b.CAPTION AS caption,
    b.GROUPID AS batch_group,
    b.COMPANY AS company,
    b.STATUS AS status,
    b.STARTDATETIME AS start_time,
    b.ENDDATETIME AS end_time,
    DATEDIFF(second, b.STARTDATETIME, b.ENDDATETIME) AS duration_seconds
  FROM dbo.BATCH b
  WHERE b.STARTDATETIME >= DATEADD(day, -$Days, SYSUTCDATETIME())
  ORDER BY b.STARTDATETIME DESC;
END
"@

Invoke-AxpaSqlQuery -OutputFile "user_sessions.csv" -Query @"
IF OBJECT_ID('dbo.SYSCLIENTSESSIONS') IS NOT NULL
BEGIN
  SELECT TOP (5000)
    $sessionUserExpr,
    $sessionClientTypeExpr,
    $sessionStatusExpr,
    $sessionLoginExpr,
    $sessionAosExpr,
    $sessionComputerExpr
  FROM dbo.SYSCLIENTSESSIONS
  ORDER BY 4 DESC;
END
"@

Invoke-AxpaSqlQuery -OutputFile "aif_services.csv" -Query @"
IF OBJECT_ID('dbo.AIFMESSAGELOG') IS NOT NULL
BEGIN
  SELECT TOP (5000)
    $aifTypeExpr,
    $aifStatusExpr,
    $aifDirectionExpr,
    $aifCreatedExpr,
    $aifModifiedExpr,
    0 AS duration_seconds,
    CAST('' AS nvarchar(20)) AS company
  FROM dbo.AIFMESSAGELOG
  ORDER BY 4 DESC;
END
"@

Invoke-AxpaSqlQuery -OutputFile "retail_load.csv" -Query @"
IF OBJECT_ID('dbo.RETAILTRANSACTIONTABLE') IS NOT NULL
BEGIN
  SELECT TOP (1000)
    DATAAREAID AS company,
    STORE AS store,
    CAST(TRANSDATE AS date) AS trans_date,
    COUNT(*) AS transaction_count
  FROM dbo.RETAILTRANSACTIONTABLE
  WHERE TRANSDATE >= DATEADD(day, -$Days, CAST(GETDATE() AS date))
  GROUP BY DATAAREAID, STORE, CAST(TRANSDATE AS date)
  ORDER BY trans_date DESC, transaction_count DESC;
END
"@

$sourceStatus = @(
  [pscustomobject]@{ source="BATCHJOB"; file="batch_jobs.csv"; status=$(if(Test-AxpaColumn -TableName "dbo.BATCHJOB" -ColumnName "RECID"){"present"}else{"missing"}); note="AX batch job table" },
  [pscustomobject]@{ source="BATCH"; file="batch_tasks.csv"; status=$(if(Test-AxpaColumn -TableName "dbo.BATCH" -ColumnName "RECID"){"present"}else{"missing"}); note="AX batch task table" },
  [pscustomobject]@{ source="SYSCLIENTSESSIONS"; file="user_sessions.csv"; status=$(if(Test-AxpaColumn -TableName "dbo.SYSCLIENTSESSIONS" -ColumnName "RECID"){"present"}else{"missing"}); note="AX user session table" },
  [pscustomobject]@{ source="AIFMESSAGELOG"; file="aif_services.csv"; status=$(if(Test-AxpaColumn -TableName "dbo.AIFMESSAGELOG" -ColumnName "RECID"){"present"}else{"missing"}); note="AX AIF message table" },
  [pscustomobject]@{ source="RETAILTRANSACTIONTABLE"; file="retail_load.csv"; status=$(if(Test-AxpaColumn -TableName "dbo.RETAILTRANSACTIONTABLE" -ColumnName "RECID"){"present"}else{"missing"}); note="AX retail transaction table" }
)
$sourceStatus | Export-Csv -NoTypeInformation -Encoding UTF8 -Path (Join-Path $OutputDirectory "source_status.csv")

Write-Host "AX database snapshot written to $OutputDirectory"
