param(
  [Parameter(Mandatory=$true)][string]$ConnectionString,
  [Parameter(Mandatory=$true)][string]$OutputDirectory
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$query = @"
IF OBJECT_ID('ModelElement') IS NOT NULL
BEGIN
  SELECT TOP (100000)
    ID AS class_number,
    NAME AS class_name,
    ELEMENTTYPE AS element_type
  FROM ModelElement
  WHERE ELEMENTTYPE IN (45, 42, 44, 40) OR NAME LIKE '%Batch%'
  ORDER BY NAME;
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
  $table | Export-Csv -NoTypeInformation -Encoding UTF8 -Path (Join-Path $OutputDirectory "ax_model_mapping.csv")
}
finally {
  $conn.Dispose()
}
Write-Host "AX model mapping written to $OutputDirectory"
