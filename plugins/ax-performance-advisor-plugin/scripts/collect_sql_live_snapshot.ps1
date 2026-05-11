param(
  [Parameter(Mandatory=$true)][string]$ConnectionString,
  [Parameter(Mandatory=$true)][string]$OutputDirectory,
  [switch]$IncludeQueryStore
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

function Invoke-AxpaSqlQuery {
  param([string]$Query, [string]$OutputFile)
  $connection = [System.Data.SqlClient.SqlConnection]::new($ConnectionString)
  $command = $connection.CreateCommand()
  $command.CommandText = $Query
  $command.CommandTimeout = 30
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

Invoke-AxpaSqlQuery -OutputFile "ax_live_blocking.csv" -Query @"
SELECT
  s.login_name AS user_id,
  COALESCE(s.host_name, '') AS host_name,
  r.session_id,
  r.blocking_session_id,
  s.program_name,
  r.status AS sql_status,
  DB_NAME(r.database_id) AS database_name,
  r.command,
  r.wait_type,
  r.wait_time AS wait_time_ms,
  r.cpu_time AS cpu_time_ms,
  r.total_elapsed_time AS elapsed_time_ms,
  r.reads,
  r.writes,
  r.logical_reads,
  SUBSTRING(t.text, (r.statement_start_offset/2)+1,
    ((CASE r.statement_end_offset WHEN -1 THEN DATALENGTH(t.text) ELSE r.statement_end_offset END - r.statement_start_offset)/2)+1) AS statement_text,
  SYSDATETIMEOFFSET() AS check_time,
  CASE
    WHEN s.program_name LIKE '%Dynamics AX%' THEN 'AX'
    WHEN s.program_name LIKE '%Microsoft Dynamics%' THEN 'AX'
    ELSE 'SQL'
  END AS workload_family,
  CASE
    WHEN s.program_name LIKE '%Batch%' THEN 'Batch'
    WHEN s.program_name LIKE '%Dynamics AX%' AND r.blocking_session_id <> 0 THEN 'Worker-Blocked'
    WHEN s.program_name LIKE '%Dynamics AX%' THEN 'Worker'
    ELSE ''
  END AS ax_client_type,
  CASE
    WHEN r.blocking_session_id <> 0 THEN 'Wird beendet - Blockiert'
    ELSE r.status
  END AS ax_status
FROM sys.dm_exec_requests r
JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) t
WHERE
  s.program_name LIKE '%Dynamics AX%'
  OR s.program_name LIKE '%Microsoft Dynamics%'
  OR r.blocking_session_id <> 0
ORDER BY r.blocking_session_id DESC, r.total_elapsed_time DESC;
"@

Invoke-AxpaSqlQuery -OutputFile "blocking.csv" -Query @"
SELECT
  r.session_id AS blocked_session_id,
  r.blocking_session_id,
  r.wait_type,
  r.wait_time AS wait_time_ms,
  DB_NAME(r.database_id) AS database_name,
  s.program_name,
  s.login_name,
  s.host_name,
  SYSDATETIMEOFFSET() AS sample_time
FROM sys.dm_exec_requests r
JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
WHERE r.blocking_session_id <> 0;
"@

Invoke-AxpaSqlQuery -OutputFile "sql_wait_stats.csv" -Query @"
SELECT TOP (50)
  wait_type,
  wait_time_ms,
  signal_wait_time_ms,
  waiting_tasks_count
FROM sys.dm_os_wait_stats
WHERE wait_type NOT LIKE 'SLEEP%' AND wait_type NOT LIKE 'BROKER%' AND wait_type NOT LIKE 'XE%'
ORDER BY wait_time_ms DESC;
"@

Invoke-AxpaSqlQuery -OutputFile "sql_top_queries.csv" -Query @"
SELECT TOP (50)
  CONVERT(varchar(34), qs.query_hash, 1) AS query_hash,
  CONVERT(varchar(34), qs.query_plan_hash, 1) AS plan_hash,
  DB_NAME(st.dbid) AS database_name,
  OBJECT_SCHEMA_NAME(st.objectid, st.dbid) + '.' + OBJECT_NAME(st.objectid, st.dbid) AS object_name,
  SUBSTRING(st.text, (qs.statement_start_offset/2)+1,
    ((CASE qs.statement_end_offset WHEN -1 THEN DATALENGTH(st.text) ELSE qs.statement_end_offset END - qs.statement_start_offset)/2)+1) AS statement_text,
  qs.total_worker_time / 1000 AS total_cpu_ms,
  qs.total_elapsed_time / 1000 AS total_duration_ms,
  qs.total_logical_reads,
  qs.execution_count,
  (qs.total_elapsed_time / NULLIF(qs.execution_count, 0)) / 1000 AS avg_duration_ms,
  qs.total_logical_reads / NULLIF(qs.execution_count, 0) AS avg_logical_reads,
  qs.last_execution_time
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
ORDER BY qs.last_execution_time DESC;
"@

if ($IncludeQueryStore) {
  Invoke-AxpaSqlQuery -OutputFile "query_store_runtime.csv" -Query @"
IF EXISTS (SELECT 1 FROM sys.database_query_store_options WHERE actual_state_desc = 'READ_WRITE')
BEGIN
  SELECT TOP (50)
    qsq.query_id,
    qsp.plan_id,
    AVG(rs.avg_duration) / 1000.0 AS avg_duration_ms,
    AVG(rs.avg_logical_io_reads) AS avg_logical_io_reads,
    MAX(rsi.end_time) AS last_interval_end
  FROM sys.query_store_query qsq
  JOIN sys.query_store_plan qsp ON qsq.query_id = qsp.query_id
  JOIN sys.query_store_runtime_stats rs ON qsp.plan_id = rs.plan_id
  JOIN sys.query_store_runtime_stats_interval rsi ON rs.runtime_stats_interval_id = rsi.runtime_stats_interval_id
  GROUP BY qsq.query_id, qsp.plan_id
  ORDER BY MAX(rsi.end_time) DESC, AVG(rs.avg_duration) DESC;
END
"@
}

Write-Host "Lightweight SQL live snapshot written to $OutputDirectory"
