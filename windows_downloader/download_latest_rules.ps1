$ErrorActionPreference = "Stop"
$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDirectory "settings.ps1")

if ($GitHubOwner -eq "YOUR_GITHUB_USERNAME") {
    throw "Open settings.ps1 and replace YOUR_GITHUB_USERNAME first."
}

$ReleaseApi = "https://api.github.com/repos/$GitHubOwner/$GitHubRepository/releases/tags/baaqmd-current"
$Headers = @{
    "Accept" = "application/vnd.github+json"
    "User-Agent" = "BAAQMD-Rules-Windows-Downloader"
}

$WorkingDirectory = Join-Path $env:TEMP "BAAQMD_Rules_Download"
$ZipPath = Join-Path $WorkingDirectory "BAAQMD_Current_Rules.zip"
$ExtractedDirectory = Join-Path $WorkingDirectory "Extracted"

if (Test-Path $WorkingDirectory) {
    Remove-Item $WorkingDirectory -Recurse -Force
}
New-Item -ItemType Directory -Path $ExtractedDirectory -Force | Out-Null

Write-Host "Finding the current BAAQMD rules release..."
$Release = Invoke-RestMethod -Uri $ReleaseApi -Headers $Headers
$Asset = $Release.assets | Where-Object { $_.name -eq "BAAQMD_Current_Rules.zip" } | Select-Object -First 1
if (-not $Asset) {
    throw "The release exists, but BAAQMD_Current_Rules.zip was not found."
}

Write-Host "Downloading the current rules ZIP..."
Invoke-WebRequest -Uri $Asset.browser_download_url -Headers $Headers -OutFile $ZipPath
Expand-Archive -Path $ZipPath -DestinationPath $ExtractedDirectory -Force

$SourceFolder = Join-Path $ExtractedDirectory "BAAQMD_Current_Rules"
if (-not (Test-Path $SourceFolder)) {
    throw "The ZIP did not contain the expected BAAQMD_Current_Rules folder."
}

New-Item -ItemType Directory -Path $DestinationFolder -Force | Out-Null
Write-Host "Updating $DestinationFolder ..."
& robocopy.exe $SourceFolder $DestinationFolder /MIR /R:2 /W:3 /NFL /NDL /NJH /NJS
$RobocopyCode = $LASTEXITCODE
if ($RobocopyCode -ge 8) {
    throw "Robocopy failed with exit code $RobocopyCode."
}

Remove-Item $WorkingDirectory -Recurse -Force
Write-Host "Finished. Current rules are in: $DestinationFolder"
