# Pilot Data Closeout and Retention Execution

This is an engineering operations procedure, not legal advice and not a substitute for the governing pilot agreement.

## Goal

At pilot closeout, every regular file in the dedicated partner workspace must be explicitly classified as either:

- `RETAIN` — permitted and required to remain; or
- `DELETE` — no longer permitted or needed.

PCS does not treat "we probably deleted the raw data" as an auditable control.

The closeout formats are:

- `pcs-pilot-closeout-plan-v1`
- `pcs-pilot-closeout-receipt-v1`

Both are hash-bound.

## Safety model

The closeout tool is intentionally narrow:

- every regular file must be explicitly classified;
- retain/delete sets must be disjoint;
- symlinks are rejected;
- paths must be normalized relative POSIX paths;
- the plan records exact SHA-256 and size for every file;
- apply requires the operator to repeat the exact plan SHA-256;
- if any file is added, removed, changed, or changes type after planning, deletion aborts;
- only files explicitly marked DELETE are unlinked;
- retained files are re-hashed after deletion;
- the receipt records hashes of deleted and retained files without embedding their contents.

The tool does **not** claim secure media erasure. Filesystem unlinking does not prove removal from snapshots, backups, cloud-provider retention, journal history, disk remanence, or third-party transfer systems. Those obligations remain governed by the partner agreement and infrastructure policy.

## Keep closeout records outside the partner workspace

The plan and receipt should live in an engagement-control directory that is allowed to survive closeout. Do not create the only deletion receipt inside a workspace that the plan is about to delete.

Example:

```text
operations/
  PCS-PILOT-0001/
    closeout-plan.json
    closeout-receipt.json

partner-workspaces/
  PCS-PILOT-0001/
    ...
```

## Create the plan

Inventory every file and classify it explicitly:

```bash
python scripts/pilot_closeout.py plan \
  --workspace partner-workspaces/PCS-PILOT-0001 \
  --pilot-id PCS-PILOT-0001 \
  --retain final-delivery/study.pcs.zip \
  --retain final-delivery/verification-receipt.json \
  --delete raw/input.csv \
  --delete work/intermediate.json \
  -o operations/PCS-PILOT-0001/closeout-plan.json
```

If any workspace file is missing from the classification, plan creation fails.

Review:

- every path;
- RETAIN versus DELETE action;
- file size;
- SHA-256;
- the final `plan_sha256`.

## Apply the plan

Only after reviewer acceptance and the contractual closeout trigger:

```bash
python scripts/pilot_closeout.py apply \
  --workspace partner-workspaces/PCS-PILOT-0001 \
  --plan operations/PCS-PILOT-0001/closeout-plan.json \
  --confirm-plan-sha256 <exact-plan-sha256> \
  -o operations/PCS-PILOT-0001/closeout-receipt.json
```

If the workspace changed after planning, apply fails without deleting planned files.

The resulting receipt binds:

- pilot ID;
- workspace label;
- plan SHA-256;
- application timestamp;
- hashes/sizes of deleted files;
- hashes/sizes of retained files;
- receipt SHA-256.

## Default first-pilot retention posture

Unless the signed agreement requires something else:

Retain only what is necessary to support the assurance record, such as:

- final signed PCS bundle;
- public signer material and lifecycle record;
- reviewer receipt/policy;
- final limitations statement;
- release metadata and approved operational records;
- closeout plan/receipt.

Delete unnecessary partner-provided raw data, temporary transformations, scratch outputs, and local copies after the agreed closeout trigger.

Do not retain partner artifacts for:

- model training;
- unrelated PCS research;
- public demos;
- academic publication;
- benchmark construction;

unless the partner separately authorized that use and any other required approvals were obtained.

## Incident behavior

If closeout cannot be completed exactly as planned:

1. stop;
2. do not weaken the plan to make it pass;
3. preserve the plan and minimal diagnostic evidence;
4. determine why the workspace changed or why an expected target cannot be removed;
5. follow the governing data-handling/incident procedure;
6. issue a new reviewed closeout plan if needed.

## Reviewer interpretation

A successful closeout receipt proves only that the local tool observed the planned bytes, unlinked the specified local files, and re-observed the retained files during that execution.

It does not prove secure erasure outside the local workspace.
