# Apply software 0.2.0 to the existing CORTAC repository

Destination: https://github.com/LadyElinor/CORTAC

These are the original patch-delivery instructions. If software 0.2.0 is already present on `main`, use that Git history and create a new branch for further work; do not reapply the initial patch.

This revision is based on `b710938c303d6365e31245d22843cd5a9014b4ec`. The review archive includes a complete `CORTAC` source directory and `cortac-0.2.0.patch`. It contains no Git history or credentials. Nothing is pushed by extracting or checking it.

## PowerShell: apply the patch on a new branch

Open PowerShell inside your existing CORTAC Git checkout. Replace the patch path below with the extracted patch's location. Run one section at a time and stop on any error. These checks require the expected clean base, so they will stop if later work would need merging.

```powershell
$patch = 'C:\Users\arren\Downloads\CORTAC_0_2_0_Review\cortac-0.2.0.patch'

$pending = git status --porcelain
if ($LASTEXITCODE -ne 0) { throw 'Open PowerShell inside the existing Git checkout.' }
if ($pending) { throw 'Commit or set aside existing changes before applying this revision.' }

$base = git rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $base -ne 'b710938c303d6365e31245d22843cd5a9014b4ec') {
    throw 'Base differs. Review and merge the patch into current history; do not reset or force-push.'
}

git switch -c revision/synthetic-verification-0.2.0
if ($LASTEXITCODE -ne 0) { throw 'Could not create the review branch.' }
git apply --check $patch
if ($LASTEXITCODE -ne 0) { throw 'Patch does not apply cleanly.' }
git apply $patch
if ($LASTEXITCODE -ne 0) { throw 'Patch failed.' }

py -3 scripts/verify.py
if ($LASTEXITCODE -ne 0) { throw 'Verification failed.' }
git add .
if ($LASTEXITCODE -ne 0) { throw 'Staging failed.' }
git diff --cached --stat
git diff --cached --check
if ($LASTEXITCODE -ne 0) { throw 'Review whitespace errors before committing.' }
```

Review the changes and the MIT license in `LICENSE`. To publish the reviewed branch:

```powershell
git commit -m 'Scope synthetic reports and add dual constraints and domain lottery'
if ($LASTEXITCODE -ne 0) { throw 'Commit failed; check your Git author identity.' }
git push -u origin revision/synthetic-verification-0.2.0
if ($LASTEXITCODE -ne 0) { throw 'Push failed; check authentication and remote history.' }
```

Then open a pull request against `main`. This package does not claim a remote CI run, branch protection, or merge approval.

## Complete source directory

The included `CORTAC` folder can also be tested without Git using `py -3 scripts/verify.py`. To import it into an existing checkout, use a review branch and compare the diff against the current source. Preserve the checkout's Git metadata and existing history. The patch route above is preferable for the verified base.
