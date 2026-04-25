param(
  [Parameter(Mandatory=$true)][string]$ConnectionString,
  [Parameter(Mandatory=$true)][string]$OutputDirectory
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$query = @"
SELECT TABLE_SCHEMA + '.' + TABLE_NAME AS source_table
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_SCHEMA, TABLE_NAME;
"@
$conn = [System.Data.SqlClient.SqlConnection]::new($ConnectionString)
$cmd = $conn.CreateCommand()
$cmd.CommandText = $query
$cmd.CommandTimeout = 120
$adapter = [System.Data.SqlClient.SqlDataAdapter]::new($cmd)
$table = [System.Data.DataTable]::new()
try {
  [void]$adapter.Fill($table)
  $table | Export-Csv -NoTypeInformation -Encoding UTF8 -Path (Join-Path $OutputDirectory "dynamicsperf_inventory.csv")
}
finally {
  $conn.Dispose()
}
Write-Host "DynamicsPerf inventory written to $OutputDirectory"
