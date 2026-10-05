# Upload software 0.2.1 to GitHub

Destination: https://github.com/LadyElinor/CORTAC

The `CORTAC_0_2_1_MIT.zip` delivery contains the complete `CORTAC/` source directory, `cortac-0.2.1.bundle`, and `PUSH_TO_GITHUB.txt`. The bundle includes complete Git history through the prepared 0.2.1 commit. There is no patch file. These instructions replace the obsolete 0.2.0 patch instructions.

## PowerShell: import the prepared commit into the existing checkout

Extract the ZIP first. Adjust the two paths below if needed. The checkout path is the existing Git repository, not the newly extracted source folder. Run this block and stop if it reports any error. A clean checkout whose `main` is an ancestor of the bundle can be advanced without rewriting history; divergent work needs a separate reviewed merge.

```powershell
$bundle = 'C:\Users\arren\Downloads\CORTAC_0_2_1_MIT\cortac-0.2.1.bundle'
Set-Location 'C:\Users\arren\Downloads\CORTAC_GitHub_Ready\CORTAC' -ErrorAction Stop

$pending = git status --porcelain
if ($LASTEXITCODE -ne 0) { throw 'This directory must be the existing Git checkout.' }
if ($pending) { throw 'Commit or set aside existing changes before importing the bundle.' }

git switch main
if ($LASTEXITCODE -ne 0) { throw 'Could not switch to main.' }
$origin = git remote get-url origin
if ($LASTEXITCODE -ne 0 -or $origin -notmatch '^(https://github\.com/|git@github\.com:)LadyElinor/CORTAC(\.git)?/?$') {
    throw 'The origin must be LadyElinor/CORTAC. Inspect git remote -v before proceeding.'
}
git bundle verify $bundle
if ($LASTEXITCODE -ne 0) { throw 'Bundle verification failed.' }
git fetch $bundle refs/heads/main
if ($LASTEXITCODE -ne 0) { throw 'Bundle import failed.' }
git merge --ff-only FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'History diverged. Review a merge; do not reset or force-push.' }

py -3 scripts/verify.py
if ($LASTEXITCODE -ne 0) { throw 'Verification failed. Do not publish yet.' }
git log -1 --oneline
git push origin main
if ($LASTEXITCODE -ne 0) { throw 'Push failed. Check GitHub authentication and remote history.' }
```

The bundle already contains the commit; no additional `git add` or `git commit` is needed. Publishing requires your GitHub credentials and repository write access. A remote branch that has advanced incompatibly will cause an ordinary push to refuse; do not force it.

After pushing, inspect the **Offline checks** workflow in GitHub Actions, including **Windows Python 3.12**. Configured jobs and local newline emulation do not establish native Windows success. The source directory can be checked without Git using `py -3 scripts/verify.py`.
