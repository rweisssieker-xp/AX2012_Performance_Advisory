param(
  [string]$Repository = "rweisssieker-xp/AX2012_Performance_Advisory",
  [string]$Version = "v0.1.0",
  [string]$CodexHome = "$env:USERPROFILE\.codex",
  [string]$MarketplaceName = "ax-performance-advisory",
  [string]$PluginName = "ax-performance-advisor-plugin",
  [switch]$UpdateCodexConfig,
  [switch]$NoConfigUpdate,
  [switch]$Force,
  [switch]$SkipPythonCheck,
  [switch]$KeepTemp
)

$ErrorActionPreference = "Stop"

function Write-Step {
  param([string]$Message)
  Write-Host "==> $Message"
}

function Test-Command {
  param([string]$Name)
  return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Write-Utf8NoBomLines {
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)][AllowEmptyString()][string[]]$Lines
  )

  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllLines($Path, $Lines, $encoding)
}

function New-CodexConfigBlock {
  param(
    [Parameter(Mandatory=$true)][string]$MarketplaceName,
    [Parameter(Mandatory=$true)][string]$MarketplacePath,
    [Parameter(Mandatory=$true)][string]$PluginName
  )

  $pluginSection = "[plugins.`"$PluginName@$MarketplaceName`"]"
  $marketplaceSection = "[marketplaces.$MarketplaceName]"
  $tomlMarketplacePath = $MarketplacePath.Replace("'", "''")
  $timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  return @(
    "# BEGIN AXPA installer managed block: $PluginName@$MarketplaceName",
    $marketplaceSection,
    "last_updated = `"$timestamp`"",
    'source_type = "local"',
    "source = '$tomlMarketplacePath'",
    "",
    $pluginSection,
    "enabled = true",
    "# END AXPA installer managed block: $PluginName@$MarketplaceName"
  )
}

function Test-TomlSyntax {
  param([Parameter(Mandatory=$true)][string]$Path)

  if (-not (Test-Command "python")) {
    throw "Python is required to validate config.toml before modifying it. Re-run without -UpdateCodexConfig and apply the generated snippet manually."
  }

  & python -c "import sys,tomllib; tomllib.loads(open(sys.argv[1], 'r', encoding='utf-8-sig').read())" $Path
  if ($LASTEXITCODE -ne 0) {
    throw "TOML validation failed for $Path"
  }
}

function Update-CodexConfig {
  param(
    [Parameter(Mandatory=$true)][string]$ConfigPath,
    [Parameter(Mandatory=$true)][string]$MarketplaceName,
    [Parameter(Mandatory=$true)][string]$MarketplacePath,
    [Parameter(Mandatory=$true)][string]$PluginName
  )

  $markerStart = "# BEGIN AXPA installer managed block: $PluginName@$MarketplaceName"
  $markerEnd = "# END AXPA installer managed block: $PluginName@$MarketplaceName"
  $newBlock = New-CodexConfigBlock -MarketplaceName $MarketplaceName -MarketplacePath $MarketplacePath -PluginName $PluginName

  $lines = @()
  if (Test-Path $ConfigPath) {
    $lines = Get-Content -LiteralPath $ConfigPath
  }

  $filtered = New-Object System.Collections.Generic.List[string]
  $skip = $false
  foreach ($line in $lines) {
    if ($line -eq $markerStart) {
      $skip = $true
      continue
    }
    if ($skip -and $line -eq $markerEnd) {
      $skip = $false
      continue
    }
    if (-not $skip) {
      $filtered.Add($line)
    }
  }

  $parent = Split-Path -Parent $ConfigPath
  New-Item -ItemType Directory -Force -Path $parent | Out-Null
  if (Test-Path $ConfigPath) {
    Test-TomlSyntax -Path $ConfigPath
  }

  $candidatePath = "$ConfigPath.axpa-new"
  $backupPath = "$ConfigPath.bak-$(Get-Date -Format yyyyMMddHHmmss)"
  Write-Utf8NoBomLines -Path $candidatePath -Lines ([string[]]($filtered + "" + $newBlock + ""))
  Test-TomlSyntax -Path $candidatePath

  if (Test-Path $ConfigPath) {
    Copy-Item -LiteralPath $ConfigPath -Destination $backupPath -Force
    Write-Host "Backed up Codex config to $backupPath"
  }
  Move-Item -LiteralPath $candidatePath -Destination $ConfigPath -Force
}

function Copy-DirectoryRobust {
  param(
    [Parameter(Mandatory=$true)][string]$Source,
    [Parameter(Mandatory=$true)][string]$Destination
  )
  New-Item -ItemType Directory -Force -Path $Destination | Out-Null
  $log = Join-Path ([IO.Path]::GetTempPath()) ("axpa-robocopy-" + [guid]::NewGuid().ToString("N") + ".log")
  & robocopy $Source $Destination /E /NFL /NDL /NJH /NJS /NP /R:2 /W:1 /LOG:$log | Out-Null
  $code = $LASTEXITCODE
  if ($code -gt 7) {
    $tail = if (Test-Path $log) { (Get-Content -LiteralPath $log -Tail 20) -join "`n" } else { "" }
    throw "robocopy failed with exit code $code. $tail"
  }
  if (Test-Path $log) {
    Remove-Item -LiteralPath $log -Force -ErrorAction SilentlyContinue
  }
}

$releaseBase = "https://github.com/$Repository/releases/download/$Version"
$zipName = "$PluginName-0.1.0.zip"
$manifestName = "$zipName.manifest.json"
$tmp = Join-Path ([IO.Path]::GetTempPath()) ("axpa-codex-install-" + [guid]::NewGuid().ToString("N"))
$downloadDir = Join-Path $tmp "download"
$extractDir = Join-Path $tmp "extract"
$marketplaceRoot = Join-Path (Join-Path $CodexHome "plugins\marketplaces") $MarketplaceName
$pluginsRoot = Join-Path $marketplaceRoot "plugins"
$targetPlugin = Join-Path $pluginsRoot $PluginName
$configPath = Join-Path $CodexHome "config.toml"

try {
  Write-Step "Create temporary install workspace"
  New-Item -ItemType Directory -Force -Path $downloadDir, $extractDir, $pluginsRoot | Out-Null

  $zipPath = Join-Path $downloadDir $zipName
  $manifestPath = Join-Path $downloadDir $manifestName

  Write-Step "Download release manifest from $releaseBase"
  Invoke-WebRequest -Uri "$releaseBase/$manifestName" -OutFile $manifestPath

  Write-Step "Download plugin ZIP from $releaseBase"
  Invoke-WebRequest -Uri "$releaseBase/$zipName" -OutFile $zipPath

  Write-Step "Verify ZIP checksum"
  $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
  $actualHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
  $expectedHash = [string]$manifest.sha256
  if ($actualHash -ne $expectedHash.ToLowerInvariant()) {
    throw "Checksum mismatch. Expected $expectedHash but got $actualHash"
  }

  if ((Test-Path $targetPlugin) -and -not $Force) {
    throw "Plugin already exists at $targetPlugin. Re-run with -Force to replace it."
  }

  Write-Step "Extract plugin ZIP"
  Expand-Archive -LiteralPath $zipPath -DestinationPath $extractDir -Force
  $sourcePlugin = Join-Path $extractDir $PluginName
  if (-not (Test-Path (Join-Path $sourcePlugin ".codex-plugin\plugin.json"))) {
    throw "Extracted ZIP does not contain expected .codex-plugin\plugin.json"
  }

  Write-Step "Install plugin into Codex marketplace folder"
  if (Test-Path $targetPlugin) {
    $backup = "$targetPlugin.backup-$(Get-Date -Format yyyyMMddHHmmss)"
    Move-Item -LiteralPath $targetPlugin -Destination $backup -Force
    Write-Host "Backed up previous install to $backup"
  }
  Copy-DirectoryRobust -Source $sourcePlugin -Destination $targetPlugin

  Write-Step "Write local marketplace manifest"
  $marketplace = @{
    name = $MarketplaceName
    interface = @{ displayName = "AX Performance Advisory" }
    plugins = @(
      @{
        name = $PluginName
        category = "Observability"
        policy = @{
          installation = "AVAILABLE"
          authentication = "ON_INSTALL"
        }
        source = @{
          source = "local"
          path = "./plugins/$PluginName"
        }
      }
    )
  }
  $marketplace | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $marketplaceRoot "marketplace.json") -Encoding UTF8

  $configSnippetPath = Join-Path $marketplaceRoot "codex-config-snippet.toml"
  Write-Utf8NoBomLines -Path $configSnippetPath -Lines ([string[]](New-CodexConfigBlock -MarketplaceName $MarketplaceName -MarketplacePath $marketplaceRoot -PluginName $PluginName))

  if ($UpdateCodexConfig -and -not $NoConfigUpdate) {
    Write-Step "Enable marketplace and plugin in Codex config"
    Update-CodexConfig -ConfigPath $configPath -MarketplaceName $MarketplaceName -MarketplacePath $marketplaceRoot -PluginName $PluginName
  }
  else {
    Write-Host "Skipped automatic Codex config update."
    Write-Host "Config snippet written to $configSnippetPath"
    Write-Host "Review and append this snippet manually, or re-run with -UpdateCodexConfig after backing up config.toml."
  }

  if (-not $SkipPythonCheck -and (Test-Command "python")) {
    Write-Step "Run lightweight plugin validation"
    & python -m json.tool (Join-Path $targetPlugin ".codex-plugin\plugin.json") | Out-Null
    & python (Join-Path $targetPlugin "scripts\generate_dashboard.py") --evidence (Join-Path $targetPlugin "sample\evidence") --output (Join-Path $targetPlugin "out\install-smoke-dashboard.html") | Out-Host
    $installCheck = Join-Path $targetPlugin "scripts\check_plugin_install.py"
    if (Test-Path $installCheck) {
      & python $installCheck --codex-home $CodexHome --marketplace-name $MarketplaceName --plugin-name $PluginName | Out-Host
    }
  }
  elseif (-not (Test-Command "python")) {
    Write-Warning "Python was not found; skipped smoke validation."
  }

  Write-Host ""
  Write-Host "AX Performance Advisor installed."
  Write-Host "Plugin:      $targetPlugin"
  Write-Host "Marketplace: $marketplaceRoot"
  Write-Host "Config:      $configPath"
  Write-Host ""
  Write-Host "Restart Codex to reload local marketplaces/plugins."
}
finally {
  if ($KeepTemp) {
    Write-Host "Kept temp folder: $tmp"
  }
  elseif (Test-Path $tmp) {
    Remove-Item -LiteralPath $tmp -Recurse -Force
  }
}
