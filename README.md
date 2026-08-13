# BAAD GitHub Automation

This project runs the BAAD rule updater in GitHub Actions. Python is not
installed on the Windows computer. GitHub publishes one current ZIP release,
and a built-in Windows PowerShell script mirrors that release into a selected
local folder.

## Quick setup

### 1. Create the GitHub repository

1. Sign in to GitHub.
2. Select **New repository**.
3. Repository name: `baad-current-rules`
4. Select **Public**. The source documents are already public, and a public
   repository lets the Windows downloader work without storing a GitHub token.
5. Do not initialize it with a README, `.gitignore`, or license.
6. Select **Create repository**.

### 2. Upload this project

1. On the empty repository page, select **uploading an existing file**.
2. Extract the downloaded project ZIP on Windows.
3. Open the extracted `BAAD_GitHub_Automation` folder.
4. Drag all its contents into GitHub's upload area, including:
   - `.github`
   - `windows_downloader`
   - `baad_rules_updater.py`
   - `config.github.json`
   - `requirements.txt`
   - `.gitignore`
   - `README.md`
5. Commit directly to the `main` branch.

### 3. Allow the workflow to publish files

1. In the repository, open **Settings**.
2. Select **Actions**, then **General**.
3. Under **Workflow permissions**, select **Read and write permissions**.
4. Save.

### 4. Run it once

1. Open the repository's **Actions** tab.
2. Select **Update BAAD Rules**.
3. Select **Run workflow**, then **Run workflow** again.
4. The first run normally takes several minutes because it downloads all rules
   and installs Chromium in the temporary GitHub runner.
5. Wait for the workflow to show a green check.
6. Open the repository's **Releases** section.
7. Confirm that **Current BAAD Rules** contains
   `BAAD_Current_Rules.zip`.

### 5. Configure the Windows downloader

1. Open `windows_downloader\settings.ps1` in Notepad.
2. Replace:

   `$GitHubOwner = "YOUR_GITHUB_USERNAME"`

   with your GitHub username.
3. Change `$DestinationFolder` if desired.
4. Save the file.
5. Double-click `windows_downloader\run_download.cmd`.
6. Confirm that the rules appear in the destination folder.

The destination folder must be dedicated to this collection. The downloader
mirrors the GitHub release and removes files in that folder that are not in the
current release.

### 6. Schedule the Windows download

If organizational policy permits scheduled PowerShell scripts:

1. Right-click `windows_downloader\create_weekly_task.ps1`.
2. Select **Run with PowerShell**.
3. It creates a task named **Download Current BAAD Rules** for Monday at
   9:00 AM.

The GitHub workflow runs Monday morning before the Windows download. Change the
times in the workflow or PowerShell file if needed.

If PowerShell or Task Scheduler is blocked, keep the GitHub workflow and
download the latest release ZIP manually. Do not bypass organizational policy.

## Incremental behavior

The release ZIP contains the prior state. Each GitHub run restores it before
checking the BAAD table. Unchanged files remain in place. New or revised PDFs
are downloaded, the CSV is refreshed, and the combined bookmarked PDF is
rebuilt only when needed.
