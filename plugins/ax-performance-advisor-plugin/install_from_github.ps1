param(
  [string]$Repository = "rweisssieker-xp/AX2012_Performance_Advisory",
  [string]$Version = "v0.1.0",
  [string]$CodexHome = "$env:USERPROFILE\.codex",
  [string]$MarketplaceName = "ax-performance-advisory",
  [string]$PluginName = "ax-performance-advisor-plugin",
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

function Update-CodexConfig {
  param(
    [Parameter(Mandatory=$true)][string]$ConfigPath,
    [Parameter(Mandatory=$true)][string]$MarketplaceName,
    [Parameter(Mandatory=$true)][string]$MarketplacePath,
    [Parameter(Mandatory=$true)][string]$PluginName
  )

  $pluginSection = "[plugins.`"$PluginName@$MarketplaceName`"]"
  $marketplaceSection = "[marketplaces.$MarketplaceName]"
  $escapedMarketplacePath = $MarketplacePath.Replace("\", "\\").Replace("'", "''")
  $newBlock = @(
    "",
    $marketplaceSection,
    'last_updated = "' + (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") + '"',
    'source_type = "local"',
    "source = '\\?\$escapedMarketplacePath'",
    "",
    $pluginSection,
    "enabled = true"
  )

  $lines = @()
  if (Test-Path $ConfigPath) {
    $lines = Get-Content -LiteralPath $ConfigPath
  }

  $filtered = New-Object System.Collections.Generic.List[string]
  $skip = $false
  foreach ($line in $lines) {
    if ($line -eq $marketplaceSection -or $line -eq $pluginSection) {
      $skip = $true
      continue
    }
    if ($skip -and $line -match '^\[') {
      $skip = $false
    }
    if (-not $skip) {
      $filtered.Add($line)
    }
  }

  $parent = Split-Path -Parent $ConfigPath
  New-Item -ItemType Directory -Force -Path $parent | Out-Null
  if (Test-Path $ConfigPath) {
    Copy-Item -LiteralPath $ConfigPath -Destination "$ConfigPath.bak-$(Get-Date -Format yyyyMMddHHmmss)" -Force
  }
  ($filtered + $newBlock) | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
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
        category = "Developer Tools"
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

  if (-not $NoConfigUpdate) {
    Write-Step "Enable marketplace and plugin in Codex config"
    Update-CodexConfig -ConfigPath $configPath -MarketplaceName $MarketplaceName -MarketplacePath $marketplaceRoot -PluginName $PluginName
  }
  else {
    Write-Host "Skipped Codex config update because -NoConfigUpdate was set."
  }

  if (-not $SkipPythonCheck -and (Test-Command "python")) {
    Write-Step "Run lightweight plugin validation"
    & python -m json.tool (Join-Path $targetPlugin ".codex-plugin\plugin.json") | Out-Null
    & python (Join-Path $targetPlugin "scripts\generate_dashboard.py") --evidence (Join-Path $targetPlugin "sample\evidence") --output (Join-Path $targetPlugin "out\install-smoke-dashboard.html") | Out-Host
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
