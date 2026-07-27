# Replace these two values after creating the GitHub repository.
$GitHubOwner = "YOUR_GITHUB_USERNAME"
$GitHubRepository = "baaqmd-current-rules"

# This must be a dedicated folder because the downloader mirrors its contents.
$DestinationFolder = Join-Path $env:USERPROFILE "Documents\BAAQMD Current Rules"
