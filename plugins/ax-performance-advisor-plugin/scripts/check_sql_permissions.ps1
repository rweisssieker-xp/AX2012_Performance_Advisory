param(
  [Parameter(Mandatory=$true)][string]$ConnectionString,
  [Parameter(Mandatory=$true)][string]$Output
)

$ErrorActionPreference = "Stop"
$queries = @{
  connect = "SELECT 1 AS ok"
  view_server_state = "SELECT HAS_PERMS_BY_NAME(null, null, 'VIEW SERVER STATE') AS ok"
  view_database_state = "SELECT HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'VIEW DATABASE STATE') AS ok"
  can_create_table = "SELECT HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'CREATE TABLE') AS ok"
  can_alter_any_schema = "SELECT HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'ALTER ANY SCHEMA') AS ok"
}
$rows = @()
$conn = [System.Data.SqlClient.SqlConnection]::new($ConnectionString)
try {
  $conn.Open()
  foreach ($name in $queries.Keys) {
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = $queries[$name]
    $ok = $cmd.ExecuteScalar()
    $rows += [pscustomobject]@{ permission = $name; value = $ok }
  }
}
finally {
  $conn.Dispose()
}
$rows | Export-Csv -NoTypeInformation -Encoding UTF8 -Path $Output
Write-Host "Permission check written to $Output"
