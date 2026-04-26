param(
  [Parameter(Mandatory=$true)][string]$ConnectionString,
  [Parameter(Mandatory=$true)][string]$OutputDirectory,
  [string]$AxDatabaseName = "",
  [switch]$IncludeQueryStore,
  [switch]$IncludeDeadlocks,
  [int]$WaitDeltaSeconds = 0,
  [int]$IndexFragmentationTopTables = 25
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

function Invoke-AxpaSqlQuery {
  param([string]$Query, [string]$OutputFile)
  $connection = [System.Data.SqlClient.SqlConnection]::new($ConnectionString)
  $command = $connection.CreateCommand()
  $command.CommandText = $Query
  $command.CommandTimeout = 120
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
ORDER BY qs.total_worker_time DESC;
"@

Invoke-AxpaSqlQuery -OutputFile "sql_wait_stats.csv" -Query @"
SELECT wait_type, wait_time_ms, signal_wait_time_ms, waiting_tasks_count
FROM sys.dm_os_wait_stats
WHERE wait_type NOT LIKE 'SLEEP%' AND wait_type NOT LIKE 'BROKER%' AND wait_type NOT LIKE 'XE%'
ORDER BY wait_time_ms DESC;
"@

if ($WaitDeltaSeconds -gt 0) {
  $before = Join-Path $OutputDirectory "sql_wait_stats.before.csv"
  $after = Join-Path $OutputDirectory "sql_wait_stats.after.csv"
  Invoke-AxpaSqlQuery -OutputFile "sql_wait_stats.before.csv" -Query @"
SELECT wait_type, wait_time_ms, signal_wait_time_ms, waiting_tasks_count
FROM sys.dm_os_wait_stats
WHERE wait_type NOT LIKE 'SLEEP%' AND wait_type NOT LIKE 'BROKER%' AND wait_type NOT LIKE 'XE%';
"@
  Start-Sleep -Seconds $WaitDeltaSeconds
  Invoke-AxpaSqlQuery -OutputFile "sql_wait_stats.after.csv" -Query @"
SELECT wait_type, wait_time_ms, signal_wait_time_ms, waiting_tasks_count
FROM sys.dm_os_wait_stats
WHERE wait_type NOT LIKE 'SLEEP%' AND wait_type NOT LIKE 'BROKER%' AND wait_type NOT LIKE 'XE%';
"@
  $beforeRows = Import-Csv $before | Group-Object wait_type -AsHashTable -AsString
  $deltaRows = foreach ($row in Import-Csv $after) {
    if ($beforeRows.ContainsKey($row.wait_type)) {
      $old = $beforeRows[$row.wait_type]
      [pscustomobject]@{
        wait_type = $row.wait_type
        wait_time_ms = [int64]$row.wait_time_ms - [int64]$old.wait_time_ms
        signal_wait_time_ms = [int64]$row.signal_wait_time_ms - [int64]$old.signal_wait_time_ms
        waiting_tasks_count = [int64]$row.waiting_tasks_count - [int64]$old.waiting_tasks_count
      }
    }
  }
  $deltaRows | Where-Object { $_.wait_time_ms -gt 0 } | Export-Csv -NoTypeInformation -Encoding UTF8 -Path (Join-Path $OutputDirectory "sql_wait_stats_delta.csv")
}

Invoke-AxpaSqlQuery -OutputFile "blocking.csv" -Query @"
SELECT
  r.session_id AS blocked_session_id,
  r.blocking_session_id,
  r.wait_type,
  r.wait_time AS wait_time_ms,
  DB_NAME(r.database_id) AS database_name,
  OBJECT_SCHEMA_NAME(p.object_id, r.database_id) + '.' + OBJECT_NAME(p.object_id, r.database_id) AS object_name,
  s.program_name,
  s.login_name,
  SYSDATETIMEOFFSET() AS sample_time
FROM sys.dm_exec_requests r
JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
LEFT JOIN sys.dm_tran_locks l ON r.session_id = l.request_session_id
LEFT JOIN sys.partitions p ON l.resource_associated_entity_id = p.hobt_id
WHERE r.blocking_session_id <> 0;
"@

Invoke-AxpaSqlQuery -OutputFile "missing_indexes.csv" -Query @"
SELECT
  DB_NAME(mid.database_id) AS database_name,
  OBJECT_SCHEMA_NAME(mid.object_id, mid.database_id) + '.' + OBJECT_NAME(mid.object_id, mid.database_id) AS object_name,
  mid.equality_columns,
  mid.inequality_columns,
  mid.included_columns,
  migs.avg_total_user_cost,
  migs.avg_user_impact,
  migs.user_seeks,
  migs.user_scans
FROM sys.dm_db_missing_index_details mid
JOIN sys.dm_db_missing_index_groups mig ON mid.index_handle = mig.index_handle
JOIN sys.dm_db_missing_index_group_stats migs ON mig.index_group_handle = migs.group_handle
ORDER BY migs.avg_user_impact DESC, migs.user_seeks DESC;
"@

Invoke-AxpaSqlQuery -OutputFile "file_latency.csv" -Query @"
SELECT
  DB_NAME(vfs.database_id) AS database_name,
  mf.name AS file_logical_name,
  mf.type_desc AS file_type,
  vfs.io_stall_read_ms,
  vfs.num_of_reads,
  vfs.io_stall_write_ms,
  vfs.num_of_writes
FROM sys.dm_io_virtual_file_stats(NULL, NULL) vfs
JOIN sys.master_files mf ON vfs.database_id = mf.database_id AND vfs.file_id = mf.file_id;
"@

Invoke-AxpaSqlQuery -OutputFile "index_fragmentation.csv" -Query @"
DECLARE @db sysname = COALESCE(NULLIF('$AxDatabaseName', ''), DB_NAME());
DECLARE @sql nvarchar(max) = N'
USE ' + QUOTENAME(@db) + N';
WITH top_tables AS (
  SELECT TOP ($IndexFragmentationTopTables) object_id
  FROM sys.partitions
  WHERE index_id IN (0,1)
  GROUP BY object_id
  ORDER BY SUM(rows) DESC
)
SELECT
  DB_NAME() AS database_name,
  OBJECT_SCHEMA_NAME(ips.object_id) + ''.'' + OBJECT_NAME(ips.object_id) AS object_name,
  i.name AS index_name,
  ips.avg_fragmentation_in_percent,
  ips.page_count
FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, ''LIMITED'') ips
JOIN sys.indexes i ON ips.object_id = i.object_id AND ips.index_id = i.index_id
JOIN top_tables tt ON ips.object_id = tt.object_id
WHERE ips.index_id > 0 AND ips.page_count >= 1000
ORDER BY ips.avg_fragmentation_in_percent DESC, ips.page_count DESC;';
EXEC sys.sp_executesql @sql;
"@

Invoke-AxpaSqlQuery -OutputFile "statistics_age.csv" -Query @"
DECLARE @db sysname = COALESCE(NULLIF('$AxDatabaseName', ''), DB_NAME());
DECLARE @sql nvarchar(max) = N'
USE ' + QUOTENAME(@db) + N';
SELECT
  DB_NAME() AS database_name,
  OBJECT_SCHEMA_NAME(s.object_id) + ''.'' + OBJECT_NAME(s.object_id) AS object_name,
  s.name AS stats_name,
  STATS_DATE(s.object_id, s.stats_id) AS last_updated,
  sp.rows,
  sp.modification_counter
FROM sys.stats s
OUTER APPLY sys.dm_db_stats_properties(s.object_id, s.stats_id) sp
WHERE OBJECTPROPERTY(s.object_id, ''IsUserTable'') = 1
ORDER BY sp.modification_counter DESC;';
EXEC sys.sp_executesql @sql;
"@

Invoke-AxpaSqlQuery -OutputFile "tempdb_usage.csv" -Query @"
SELECT
  SUM(user_object_reserved_page_count) * 8 AS user_object_kb,
  SUM(internal_object_reserved_page_count) * 8 AS internal_object_kb,
  SUM(version_store_reserved_page_count) * 8 AS version_store_kb,
  SUM(unallocated_extent_page_count) * 8 AS unallocated_kb,
  SUM(mixed_extent_page_count) * 8 AS mixed_extent_kb
FROM tempdb.sys.dm_db_file_space_usage;
"@

Invoke-AxpaSqlQuery -OutputFile "plan_cache_variance.csv" -Query @"
SELECT TOP (100)
  CONVERT(varchar(34), qs.query_hash, 1) AS query_hash,
  COUNT(DISTINCT qs.query_plan_hash) AS plan_count,
  MIN(qs.total_elapsed_time / NULLIF(qs.execution_count, 0)) / 1000 AS min_avg_duration_ms,
  MAX(qs.total_elapsed_time / NULLIF(qs.execution_count, 0)) / 1000 AS max_avg_duration_ms,
  SUM(qs.execution_count) AS execution_count,
  MIN(qs.last_execution_time) AS first_seen,
  MAX(qs.last_execution_time) AS last_seen
FROM sys.dm_exec_query_stats qs
GROUP BY qs.query_hash
HAVING COUNT(DISTINCT qs.query_plan_hash) > 1
   OR MAX(qs.total_elapsed_time / NULLIF(qs.execution_count, 0)) > 5 * NULLIF(MIN(qs.total_elapsed_time / NULLIF(qs.execution_count, 0)), 0)
ORDER BY max_avg_duration_ms DESC;
"@

if ($IncludeQueryStore) {
  Invoke-AxpaSqlQuery -OutputFile "query_store_status.csv" -Query @"
DECLARE @db sysname = COALESCE(NULLIF('$AxDatabaseName', ''), DB_NAME());
DECLARE @sql nvarchar(max) = N'
USE ' + QUOTENAME(@db) + N';
SELECT
  DB_NAME() AS database_name,
  actual_state_desc,
  desired_state_desc,
  readonly_reason,
  current_storage_size_mb,
  max_storage_size_mb,
  stale_query_threshold_days,
  size_based_cleanup_mode_desc,
  query_capture_mode_desc
FROM sys.database_query_store_options;';
EXEC sys.sp_executesql @sql;
"@

  Invoke-AxpaSqlQuery -OutputFile "query_store_runtime.csv" -Query @"
DECLARE @db sysname = COALESCE(NULLIF('$AxDatabaseName', ''), DB_NAME());
DECLARE @sql nvarchar(max) = N'
USE ' + QUOTENAME(@db) + N';
IF EXISTS (SELECT 1 FROM sys.database_query_store_options WHERE actual_state_desc IN (''READ_WRITE'', ''READ_ONLY''))
BEGIN
  SELECT TOP (100)
    q.query_id,
    p.plan_id,
    qt.query_sql_text,
    rs.avg_duration / 1000.0 AS avg_duration_ms,
    rs.avg_cpu_time / 1000.0 AS avg_cpu_ms,
    rs.avg_logical_io_reads,
    rs.count_executions,
    rsi.start_time,
    rsi.end_time
  FROM sys.query_store_runtime_stats rs
  JOIN sys.query_store_runtime_stats_interval rsi ON rs.runtime_stats_interval_id = rsi.runtime_stats_interval_id
  JOIN sys.query_store_plan p ON rs.plan_id = p.plan_id
  JOIN sys.query_store_query q ON p.query_id = q.query_id
  JOIN sys.query_store_query_text qt ON q.query_text_id = qt.query_text_id
  ORDER BY rs.avg_duration DESC;
END';
EXEC sys.sp_executesql @sql;
"@
}

if ($IncludeDeadlocks) {
  Invoke-AxpaSqlQuery -OutputFile "deadlocks.csv" -Query @"
;WITH target_data AS (
  SELECT CAST(xet.target_data AS xml) AS target_xml
  FROM sys.dm_xe_session_targets xet
  JOIN sys.dm_xe_sessions xe ON xe.address = xet.event_session_address
  WHERE xe.name = 'system_health' AND xet.target_name = 'ring_buffer'
),
events AS (
  SELECT xed.event_data.query('.') AS event_data
  FROM target_data
  CROSS APPLY target_xml.nodes('//RingBufferTarget/event[@name="xml_deadlock_report"]') AS xed(event_data)
)
SELECT
  event_data.value('(event/@timestamp)[1]', 'datetime2') AS event_time,
  event_data.query('(event/data/value/deadlock)[1]') AS deadlock_xml
FROM events
ORDER BY event_time DESC;
"@
}

Invoke-AxpaSqlQuery -OutputFile "plan_xml_inventory.csv" -Query @"
SELECT TOP (20)
  CONVERT(varchar(34), qs.query_hash, 1) AS query_hash,
  CONVERT(varchar(34), qs.query_plan_hash, 1) AS plan_hash,
  qs.total_elapsed_time / 1000 AS total_duration_ms,
  qp.query_plan
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_query_plan(qs.plan_handle) qp
ORDER BY qs.total_elapsed_time DESC;
"@

@{
  environment = $env:AXPA_ENVIRONMENT_NAME
  collectorVersion = "0.1.0"
  analysisVersion = "0.1.0"
  collectedAt = [DateTimeOffset]::Now.ToString("o")
} | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -Path (Join-Path $OutputDirectory "metadata.json")

Write-Host "SQL snapshot written to $OutputDirectory"
