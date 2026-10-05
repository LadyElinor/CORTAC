# Upload CORTAC to GitHub

Destination: https://github.com/LadyElinor/CORTAC

The destination was confirmed empty during preparation. The archive contains the contents of the repository in one `CORTAC` folder, including `.github`, `.gitignore`, and `.gitattributes`. It excludes Git history, credentials, caches, and virtual environments. Nothing is pushed by extracting or testing it.

## Windows PowerShell

Install Git and Python 3.10 or newer if needed. Extract `CORTAC_GitHub_Ready.zip`, open PowerShell inside its `CORTAC` folder, and run:

```powershell
py -3 scripts/verify.py
if ($LASTEXITCODE -ne 0) { throw 'Verification failed; stop before upload.' }

git init -b main
if ($LASTEXITCODE -ne 0) { throw 'Git initialization failed.' }
git add .
if ($LASTEXITCODE -ne 0) { throw 'Staging failed.' }
git diff --cached --stat
```

Review the file list, then commit and upload:

```powershell
git commit -m "Initialize CORTAC offline WAC reference tools"
if ($LASTEXITCODE -ne 0) { throw 'Commit failed. Check your Git author identity.' }
git remote add origin https://github.com/LadyElinor/CORTAC.git
if ($LASTEXITCODE -ne 0) { throw 'Remote already exists or could not be added; inspect git remote -v.' }
git push -u origin main
if ($LASTEXITCODE -ne 0) { throw 'Push failed. Check authentication and remote history; do not force-push.' }
```

Git may ask you to authenticate to GitHub. If Git requires an author name/email, configure your own identity before committing. No identity is supplied in this package.

## macOS or Linux

From the extracted `CORTAC` folder:

```sh
python3 scripts/verify.py &&
git init -b main &&
git add . &&
git diff --cached --stat
```

After reviewing the staged files:

```sh
git commit -m "Initialize CORTAC offline WAC reference tools" &&
git remote add origin https://github.com/LadyElinor/CORTAC.git &&
git push -u origin main
```

If the repository has gained commits since preparation, clone that history and import the files on a new branch, then open a pull request. Do not replace history or force-push this initial tree.

## GitHub browser upload

Upload the contents inside `CORTAC`, not the ZIP itself and not an extra enclosing directory. Include `.github/workflows/ci.yml`, `.gitignore`, and `.gitattributes`. A Git push is preferable because it preserves those files and the intended root layout.

After upload, check the **Offline checks** workflow. Its configuration is included; remote runs and required-check settings were not verified during local preparation.
