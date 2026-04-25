param(
  [Parameter(Mandatory=$true)][string]$ConnectionString,
  [Parameter(Mandatory=$true)][string]$OutputDirectory,
  [int]$Top = 1000
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$query = @"
IF OBJECT_ID('dbo.SYSTRACETABLESQL') IS NOT NULL
BEGIN
  SELECT TOP ($Top) *
  FROM dbo.SYSTRACETABLESQL
  ORDER BY RECID DESC;
END
"@
$conn = [System.Data.SqlClient.SqlConnection]::new($ConnectionString)
$cmd = $conn.CreateCommand()
$cmd.CommandText = $query
$cmd.CommandTimeout = 120
$adapter = [System.Data.SqlClient.SqlDataAdapter]::new($cmd)
$table = [System.Data.DataTable]::new()
try {
  [void]$adapter.Fill($table)
  $table | Export-Csv -NoTypeInformation -Encoding UTF8 -Path (Join-Path $OutputDirectory "ax_sql_trace.csv")
}
finally {
  $conn.Dispose()
}
Write-Host "AX SQL trace snapshot written to $OutputDirectory"
