# Immich Extras — Path-to-Publish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take the already-built `immich_extras` integration from "code complete on a feature branch" to "installable from HACS, verified against a live Immich server, first release cut."

**Architecture:** The integration code, tests, CI stack and brand assets are done and pushed on `feat/immich-extras`. Remaining work is (a) GitHub repo settings that gate the PR bot and HACS validation, (b) merging via the `create-dev-pr` workflow, (c) verifying behaviour against a real Immich server (the boundary was mocked in unit tests), (d) fixing any real-API drift, (e) an optional upstream aioimmich jobs PR, and (f) the first tagged release.

**Tech Stack:** Home Assistant custom integration, `aioimmich==0.16.1`, Python 3.13/3.14, GitHub Actions (create-dev-pr / hassfest / hacs / semantic-release), HACS.

## Global Constraints

- Domain is `immich_extras`; never duplicate core `immich` sensors (disk, photo/video counts, usage-by-type, update entity, media source, upload_file).
- Target quality scale: **platinum** (manifest already claims it; keep `quality_scale.yaml` honest — every rule `done`/`exempt` with a comment).
- Commits: Conventional Commits, terse single-imperative subject, **no AI-attribution trailers** (enforced by `.githooks/commit-msg`).
- The `create-dev-pr` workflow OWNS the PR — never hand-create with `gh pr create`.
- Manifest version bumped once, as the last commit before merge; match the level to the PR's type label.
- Every gate must pass before merge: `ruff check .`, `pyright custom_components/`, `pytest`, `bash scripts/skill_audit.sh`, plus green hassfest + HACS CI.

---

### Task 1: Enable GitHub repo settings (unblock PR bot + HACS)

Manual GitHub settings. They fail silently until set — the PR bot cannot open a PR and three HACS checks stay red without them.

**Files:** none (GitHub web UI / `gh` API).

- [ ] **Step 1: Allow Actions to create PRs**

Web: Settings → Actions → General → Workflow permissions → tick **"Allow GitHub Actions to create and approve pull requests"** → Save.

Or via API:
```bash
gh api -X PUT repos/PineappleEmperor/ha-immich/actions/permissions/workflow \
  -F default_workflow_permissions=write \
  -F can_approve_pull_request_reviews=true
```

- [ ] **Step 2: Set repo description + topics (HACS `description`, `topics` checks)**

```bash
gh repo edit PineappleEmperor/ha-immich \
  --description "Home Assistant custom integration exposing extra Immich server data (jobs, per-user usage, quotas)" \
  --add-topic home-assistant --add-topic hacs --add-topic immich \
  --add-topic homeassistant-integration --add-topic photos
```

- [ ] **Step 3: Ensure Issues are enabled (HACS `issues` check)**

```bash
gh repo edit PineappleEmperor/ha-immich --enable-issues
```

- [ ] **Step 4: Verify**

```bash
gh api repos/PineappleEmperor/ha-immich \
  --jq '{desc:.description, issues:.has_issues, topics:.topics}'
gh api repos/PineappleEmperor/ha-immich/actions/permissions/workflow \
  --jq '.default_workflow_permissions'
```
Expected: non-empty description, `issues:true`, ≥1 topic, `write`.

---

### Task 2: Open and land the integration PR via the workflow

The first push already ran `create-dev-pr` and it failed only on the Step-1 permission. Re-run it now that the setting is on; let the action open the PR, watch CI, then merge.

**Files:** none (CI + merge).

- [ ] **Step 1: Re-run the failed dev-PR workflow**

```bash
gh run rerun 29951641841        # the failed Create/Update Dev PR run
# if that id is stale, find the latest:
# gh run list --branch feat/immich-extras --workflow "Create/Update Dev PR" --limit 1
```

- [ ] **Step 2: Confirm the PR opened**

```bash
gh pr list --head feat/immich-extras --json number,title,isDraft,url
```
Expected: one draft PR, title `feat: add immich_extras platinum integration`.

- [ ] **Step 3: Wait for all checks green**

```bash
gh pr checks feat/immich-extras --watch
```
Expected: Hassfest, HACS Validation, Python Validate, Check Manifest Version, Lint PR, Quality Audit all pass. **If hassfest fails**, fix the reported file (most likely a `strings.json`/`quality_scale.yaml`/manifest issue) on the branch and push; do not merge red.

- [ ] **Step 4: Mark ready and merge**

```bash
gh pr ready feat/immich-extras
gh pr merge feat/immich-extras --squash --delete-branch
```
Expected: branch merged to `main`, `feat/immich-extras` deleted local+remote.

- [ ] **Step 5: Sync local main**

```bash
git checkout main && git pull --ff-only origin main
```

---

### Task 3: Live smoke test against a real Immich (admin key)

Unit tests mocked the aioimmich boundary. This proves the real payloads parse and entities populate. Requires a reachable Immich server and an **admin** API key.

**Files:**
- Temporary: a throwaway HA dev instance or an existing HA with the integration installed.

- [ ] **Step 1: Install the integration into a running HA**

Copy `custom_components/immich_extras/` into the HA config dir (or install the repo via HACS custom repository), restart HA.

- [ ] **Step 2: Add the integration with an admin key**

Settings → Devices & Services → Add Integration → *Immich Extras* → enter URL + admin API key. Expect it to create the server device plus one device per Immich user.

- [ ] **Step 3: Verify the admin entity set populates**

Check that these have real (non-`unknown`) states:
`sensor.*_jobs_active`, `sensor.*_jobs_waiting`, `sensor.*_jobs_failed`,
`sensor.*_total_usage`, each `sensor.*_queue_*_waiting`, the per-user
`sensor.*_user_*_*`, `binary_sensor.*_licensed`, `binary_sensor.*_job_failures`.

- [ ] **Step 4: Capture the real `/jobs` payload for a regression fixture**

From the server, record the actual response so the parser fixture matches production:
```bash
curl -fsS -H "x-api-key: $ADMIN_KEY" "$IMMICH_URL/api/jobs" | jq . > /tmp/immich_jobs.json
```
Compare its queue names and `jobCounts` keys against `TRACKED_QUEUES` in `const.py` and the `JobCounts` fields in `models.py`.

- [ ] **Step 5: Record findings**

Note any queue in the live payload not in `TRACKED_QUEUES` that deserves a sensor, and any missing/renamed `jobCounts` key. These feed Task 4. If nothing drifted, mark Task 4 no-op.

---

### Task 4: Fix any real-API drift (only if Task 3 found some)

Turn each drift finding into a failing test first, then fix. Skip entirely if Task 3 found none.

**Files:**
- Modify: `custom_components/immich_extras/models.py` and/or `const.py`
- Modify: `tests/conftest.py` (update `JOBS_PAYLOAD`/`build_statistics` to the captured real shape)
- Test: `tests/test_models.py`

- [ ] **Step 1: Update the fixture to the captured real payload**

Replace `JOBS_PAYLOAD` in `tests/conftest.py` with the real `/tmp/immich_jobs.json` content (trimmed to two representative queues).

- [ ] **Step 2: Write/adjust the failing test**

```python
def test_parse_jobs_real_payload():
    parsed = parse_jobs(JOBS_PAYLOAD)
    # assert the queue names + counts observed on a live server
    assert "thumbnailGeneration" in parsed
    assert parsed["thumbnailGeneration"].waiting >= 0
```

- [ ] **Step 3: Run it and confirm it fails (if a field/queue changed)**

Run: `.venv/bin/python -m pytest tests/test_models.py -v`
Expected: FAIL on the changed field/queue.

- [ ] **Step 4: Update `models.py`/`const.py` minimally to match**

Add the missing `JobCounts` field with a `0` default, or add the queue to `TRACKED_QUEUES` (plus its `strings.json`/`icons.json`/`en.json` entries — keep the translation-scrape test green).

- [ ] **Step 5: Full gate + commit on a fresh branch**

```bash
git checkout -b fix/jobs-payload-drift origin/main
.venv/bin/ruff check . && .venv/bin/pyright custom_components/ && \
  .venv/bin/python -m pytest && bash scripts/skill_audit.sh
git add -A && git commit -m "fix: match live immich jobs payload shape"
git push -u origin fix/jobs-payload-drift    # create-dev-pr opens the PR
```

---

### Task 5 (optional): Upstream a jobs namespace to aioimmich

The jobs shim uses `immich.api.async_do_request("jobs")` because aioimmich has no jobs namespace. Contributing one upstream lets a future version replace the shim and tightens the platinum `dependency-transparency` story. Optional and out of our release's critical path.

**Files (in a clone of `mib1185/aioimmich`, not this repo):**
- Create: `src/aioimmich/jobs/__init__.py`, `src/aioimmich/jobs/models.py`
- Modify: `src/aioimmich/__init__.py` (wire `self.jobs = ImmichJobs(self.api)`)

- [ ] **Step 1: Add a typed `ImmichJobs.async_get_all_jobs()`**

Mirror the existing `ImmichServer` pattern: a `ImmichSubApi` subclass calling `self.api.async_do_request("jobs")` and returning parsed models.

- [ ] **Step 2: Open the PR upstream, wait for merge + release.**

- [ ] **Step 3: Migrate our shim once released**

Bump `requirements` in `manifest.json` to the new aioimmich version and replace `ImmichExtrasApi.async_get_jobs` body with `self._immich.jobs.async_get_all_jobs()`. Keep the return type (`dict[str, JobCounts]`) stable so no entity code changes. Full gate + PR.

---

### Task 6: Cut the first release (v0.1.0)

After the integration is on `main` and green, tag the first release so HACS can install a zip asset. `manifest.json` is already `0.1.0`.

**Files:** none (tag + release).

- [ ] **Step 1: Confirm `main` is green and manifest is 0.1.0**

```bash
git checkout main && git pull --ff-only
jq -r .version custom_components/immich_extras/manifest.json   # -> 0.1.0
```

- [ ] **Step 2: Tag and push**

```bash
git tag v0.1.0
git push origin v0.1.0
```

- [ ] **Step 3: Verify the release + zip asset**

`semantic_release.yml` drafts/publishes the release on the tag; publishing fires `release.yml` which attaches `immich_extras.zip`.
```bash
gh release view v0.1.0 --json assets --jq '.assets[].name'
```
Expected: `immich_extras.zip` present. **If absent**, publish the drafted release from the GitHub UI (the `release: published` trigger needs a human publish, not a token-created release), then re-check.

- [ ] **Step 4: Install-test from HACS**

Add the repo as a HACS custom repository (category Integration), install, restart, confirm setup. A `Could not download` error means the zip asset is missing → revisit Step 3.

---

### Task 7 (optional): Submit to the HACS default store

Only once the integration is stable and released. Note the brand-rendering caveat: the HACS dashboard still reads the legacy brands CDN, so an integration shipping only inline `brand/` images renders blank in the HACS store list until HACS points its dashboard at the proxy — a HACS-side gap, not a repo defect. Nothing to fix here.

- [ ] **Step 1:** Confirm all HACS validation checks pass on `main` (`gh run list --workflow "HACS Validation"`).
- [ ] **Step 2:** Open a PR to `hacs/default` adding `PineappleEmperor/ha-immich` under `integration`, following that repo's CONTRIBUTING.
- [ ] **Step 3:** Address the HACS reviewer bot feedback until merged.

---

## Self-Review

- **Spec coverage:** The design spec's integration scope (sensors, flows, quality, CI, brand) is already implemented and merged via Tasks 1–2; this plan covers only the remaining publish path. Live verification (Task 3) closes the one gap unit tests can't — real-payload correctness.
- **Placeholder scan:** No TBD/TODO; every command is concrete. Tasks 4/5/7 are explicitly conditional/optional, not vague.
- **Type consistency:** Task 4/5 keep `parse_jobs` → `dict[str, JobCounts]` and `TRACKED_QUEUES` names consistent with `models.py`/`const.py` as built.
