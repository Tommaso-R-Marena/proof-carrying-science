# A1: your private archive of the 22 responses to withhold (Windows PowerShell)

**Your action. Nothing here has been done for you.** The 22 original responses (21 Nemotron, 1 Cohere)
are unchanged on the branch. They are withheld only after you send the two values in step 5, and not
before (`MODEL_OUTPUT_LICENSING.md`, section 7).

The procedure copies the public repository to your computer, builds the archive there, and makes a
second copy on a drive you own. Nothing is uploaded. The archive goes in your user folder, not in
OneDrive, Dropbox or any other synced folder. A copy in a cloud service, or only in a temporary folder,
does not count.

You need Git for Windows, Python 3 and about 0.6 GB of space. Steps 1 to 4 take a few minutes.

## Steps

Open PowerShell (Windows PowerShell or PowerShell 7) and paste one block at a time.

**1. Check the tools.** Each command prints a version. If `python` opens the Microsoft Store or
fails, use `py -3` instead of `python` in every step below.

```powershell
git --version
python --version
```

**2. Copy the repository and fix the exact commit.** The last line must print
`e6099049b303cde902e461f067c38d061f78c495`.

```powershell
$Clone = "$env:USERPROFILE\pcs-a1"
git clone --single-branch --branch tommaso-r-marena/festive-galileo-4a5m5k -c core.longpaths=true https://github.com/Tommaso-R-Marena/proof-carrying-science.git $Clone
git -C $Clone checkout --detach e6099049b303cde902e461f067c38d061f78c495
git -C $Clone rev-parse HEAD
```

**3. Build and check the archive in your user folder.** The `icacls` line is optional. It restricts
the folder to your Windows account alone. It is only needed if other people have accounts on this
computer.

```powershell
$Tool = "$Clone\research\claimcheck_v1_1\governance\archive_model_outputs.py"
$Archive = "$env:USERPROFILE\pcs-private-archive"
New-Item -ItemType Directory -Force $Archive | Out-Null
icacls $Archive /inheritance:r /grant:r "${env:USERNAME}:(OI)(CI)F"
python -I $Tool --out $Archive
"exit code: $LASTEXITCODE"
(Get-FileHash -Algorithm SHA256 "$Archive\model-outputs-withheld.tar").Hash.ToLower()
```

What you should see:

* the printed JSON ends with `"recoverable_and_complete": true`;
* `exit code: 0`;
* the last line is `91acf4ff324f6547eaa51cc9a03e2a377c43a7544adc65f3cb2da38c2a6669a3`.

**4. Make a second copy on a drive you own, and check that copy.** Replace `E:` with your USB or
external drive's letter. An encrypted drive (for example BitLocker To Go) is best. Otherwise keep the
drive somewhere private.

```powershell
Copy-Item -Recurse $Archive E:\
python -I $Tool --verify E:\pcs-private-archive\model-outputs-withheld.tar
"exit code: $LASTEXITCODE"
(Get-FileHash -Algorithm SHA256 E:\pcs-private-archive\model-outputs-withheld.tar).Hash.ToLower()
```

You should see the same three results as in step 3.

**5. Send me two values:** the SHA-256 from steps 3 and 4, and `recoverable_and_complete` from both.
Please don't send the files, the JSON or your folder paths, which contain your Windows user name.

Afterwards you may delete `$env:USERPROFILE\pcs-a1`: the archive does not depend on it. Any later
copy of the repository can check the archive again (`--verify`), because the inventory keeps every
original's SHA-256.

## If something differs

* **`recoverable_and_complete` is `false`, or the exit code is `1`:** the archive is incomplete. Do not
  rely on it. Send me the lines `missing_from_archive`, `digest_mismatches`, `unexpected_members` and
  `error`. They contain file names and digests, not response text.
* **The SHA-256 differs from `91acf4ff…69a3`, but the result is `true` and exit code `0`:** the
  archive is complete and checked against the inventory, but its bytes differ from the build tested
  here. Send me the SHA-256 and your Python version (`python --version`). I will find the cause before
  anything is withheld.
* **`git clone` reports "Filename too long":** the clone path is too long for Windows. Use a shorter
  folder, for example `$Clone = "C:\pcs-a1"`. The longest path in the repository is 149 characters.

## What the archive is

`model-outputs-withheld.tar` is a standard tar file with 23 entries:

* the 22 original files, at their repository paths under `model-outputs-withheld/`;
* `MANIFEST.json`, which gives each file's path, group, model, SHA-256, size, Git blob and source
  commit.

It is built the same way everywhere (sorted names, fixed times, owners and modes), so the same
history gives the same bytes. `--verify` reads every file back from the archive, recomputes its
SHA-256, and compares it with the archive's manifest and with the repository's inventory.

To read the archive later, Windows 10 and 11 include `tar`:

* `tar -tf E:\pcs-private-archive\model-outputs-withheld.tar` lists it;
* `tar -xf <archive> -C <a private folder>` extracts it.

## What was tested here (2026-11-21), and what was not

Tested on Linux:

* **Same result from GitHub.** A fresh clone from GitHub at the pinned commit gave
  `91acf4ff…69a3` and `true`, with the tool run as a plain script in isolated mode (`python -I`).
* **Same bytes on three Python versions:** 3.11, 3.12 and 3.13.
* **Same bytes with converting Git settings.** With `core.autocrlf=true` and a configured textconv,
  the archive was unchanged. The tool reads the stored Git objects with `git cat-file blob`, not files
  on disk.
* **Same archive after the withholding.** In a throwaway clone, a simulated withholding commit
  replaced the 22 files with the tool's stubs. That clone was not your decision and is deleted. The
  archive rebuilt from its history was byte-identical, and the earlier archive still verified
  against it.
* **Damaged copies fail.** A changed byte, a missing response, an extra member and a truncated file
  each gave `false` and exit code `1`.
* **No output inside the repository.** The tool refuses to write the archive there.
* **Safe paths for Windows.** The 10,095 paths contain no characters Windows forbids, no reserved
  names, no case collisions and no symbolic links.

Not tested: Windows itself, and PowerShell. PowerShell is not available in this environment, and
installing it here was not permitted. The commands above use only Git, Python and standard
PowerShell commands (`New-Item`, `icacls`, `Copy-Item`, `Get-FileHash`). If a command fails, send me
its error message.

Every copy made here for these tests was deleted afterwards.

## After you confirm, and not before

These are the steps I will then take on the draft branch. None of them changes Git history, frozen
benchmark files or protected `main`.

1. **Withhold.** Run
   `withhold_model_outputs --apply --groups N,C --decision "<your confirmation: date, SHA-256>"`.
   The 22 files become provenance stubs, which keep each original's SHA-256 and size.
2. **Check the withholding.**
   * the stubs' recorded digests equal the inventory's;
   * the freeze check passes, and so do the v1 and v1.1 suites;
   * the withholding-effect comparison (`withholding/withholding-effect.json`) is regenerated.
3. **Commit** the withholding as one commit, and push it.
4. **Regenerate the admission evidence at that exact commit, under H1-b.** This uses
   `prepare_core_admission --history clean`, `check_admission_consistency --history clean`, the 12
   H1-b tests and the C2b dry run. It now reports `all_as_expected: true`, with no withheld response
   reachable from the proposed retained commit.
5. **Independent review.** An independent subagent, under the same restrictions, reviews the
   regenerated evidence against `INDEPENDENT_REVIEW_CHECKLIST.md`.

Nothing is merged, tagged or applied as a protected change. Those remain your separate decisions.
