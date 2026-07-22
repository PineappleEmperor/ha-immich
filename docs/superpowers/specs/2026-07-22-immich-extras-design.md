# Immich Extras — Home Assistant custom integration (design)

**Date:** 2026-07-22
**Domain:** `immich_extras`
**Status:** Approved design, pre-implementation

## Purpose

A HACS custom integration that complements the Home Assistant **core** `immich`
integration by exposing additional Immich Server API data as entities. It does
**not** replace or depend on the core integration — it stands alone with its own
config flow.

### Non-duplication boundary

The core `immich` integration already provides (do NOT rebuild): disk size /
available / used / usage-% sensors, photos_count, videos_count, usage_by_photos,
usage_by_videos, an update entity, a media source, an `upload_file` service, and
diagnostics. It uses `aioimmich==0.16.1`, polls every 60 s, is `integration_type:
service`, `iot_class: local_polling`, quality scale **platinum**.

This integration adds only data the core one omits: job/queue backlogs, per-user
usage & quota, my-account quota, and people/tags/albums counts.

## Classification

| Field | Value |
|-------|-------|
| `domain` | `immich_extras` |
| `name` | Immich Extras |
| `integration_type` | `service` |
| `iot_class` | `local_polling` |
| Target quality scale | **Platinum** |
| Auth | Immich API key (own config flow) |
| Library | `aioimmich==0.16.1` |

## Architecture

Standard config-entry + `DataUpdateCoordinator` integration. Units:

- `api.py` — `ImmichExtrasApi`: thin wrapper over `aioimmich.Immich`, plus the
  jobs shim. Sole point of contact with the HTTP API.
- `coordinator.py` — `ImmichExtrasCoordinator(DataUpdateCoordinator[ImmichExtrasData])`:
  one 60 s poll, admin-aware fetch set, typed result dataclass.
- `models.py` — typed dataclasses for coordinator data and parsed jobs payload.
- `entity.py` — base entity classes (server-scoped and user-scoped) with
  `DeviceInfo` and `_attr_has_entity_name = True`.
- `sensor.py`, `binary_sensor.py` — entity platforms.
- `config_flow.py` — user / reauth / reconfigure steps.
- `diagnostics.py` — redacted dump.
- `const.py`, `strings.json`, `translations/en.json`, `icons.json`,
  `quality_scale.yaml`, `manifest.json`.

### API layer (`api.py`)

```
Immich(session, api_key, host, port, use_ssl)  # aioimmich
await immich.async_setup()                      # sets server version (required)
```

`async_setup()` MUST run before any request — `aioimmich.ImmichApi.async_do_request`
raises `ImmichMissingSetup` for any endpoint except `server/version` until the
version is cached.

Wrapped calls (aioimmich namespaces): `server.async_get_server_statistics()`
(admin), `users.async_get_my_user()`, `people`, `tags`, `albums` list/count.

**Jobs shim.** aioimmich has no jobs namespace. One isolated method:

```python
raw = await immich.api.async_do_request("jobs")   # GET /api/jobs, admin-only
```

Parse `raw` (a `{queueName: {jobCounts, queueStatus}}` map) into typed
`JobQueue` models in `models.py`. Keeping the raw call in exactly one method
means an upstream aioimmich change (or a future jobs namespace we migrate to)
touches one place. `jobCounts` keys: `active, waiting, completed, failed,
delayed, paused`.

Injected HA websession (`inject-websession`), async library (`async-dependency`).

### Coordinator (`coordinator.py`)

- Interval: 60 s (matches core).
- Setup: fetch `users/me`, store `is_admin` and `user_id`.
- Refresh set:
  - Always: `users/me` (my quota), `people`/`tags`/`albums` counts.
  - Admin only: `server/statistics` (totals + `usage_by_user`), `jobs`.
- Non-admin key: admin fetches are skipped silently (no repeated warnings —
  `log-when-unavailable` discipline). Admin-only entities are simply not created.
- `always_update=False`.
- Setup failure → `ConfigEntryNotReady`; auth failure → `ConfigEntryAuthFailed`
  (triggers reauth).

`ImmichExtrasData` dataclass fields: `my_user`, `statistics | None`,
`jobs | None`, `people_count`, `tags_count`, `albums_count`.

## Entities

`_attr_has_entity_name = True` throughout. Job and account sensors are
`EntityCategory.DIAGNOSTIC`. **All entities enabled by default.**

### Server device (one per config entry)

Binary sensors:
- `licensed` — from `server/about` `licensed`.
- `problem` — `on` when total failed jobs > 0 (`BinarySensorDeviceClass.PROBLEM`),
  admin only.

Sensors:
- `people_count`, `tags_count`, `albums_count`.
- `total_usage` (bytes, `DATA_SIZE`) — admin, from statistics.
- My-account (always available): `my_quota_size` (bytes), `my_quota_usage`
  (bytes), `my_quota_pct` (%).
- Job aggregates (admin): `jobs_active`, `jobs_waiting`, `jobs_failed` — summed
  across every queue.
- Per-queue waiting (admin): `waiting` count for `thumbnailGeneration`,
  `metadataExtraction`, `faceDetection`, `smartSearch`, `backupDatabase`,
  `library`.

### Per-user devices (admin only)

One device per Immich user from `statistics.usage_by_user`, `via_device` →
server device. Sensors: `user_photos`, `user_videos`, `user_usage` (bytes),
`user_quota` (bytes, only if quota set), `user_quota_pct` (%).

Dynamic user add/remove handled: new users create devices on refresh
(`dynamic-devices`); `async_remove_config_entry_device` returns `True` only for a
user no longer present (`stale-devices`).

## Config / reauth / reconfigure flows

- User step: `CONF_URL` (required), `CONF_API_KEY` (required, password),
  `CONF_VERIFY_SSL` (bool, default true). Parse URL → host/port/ssl, store parts.
- Validate by `async_setup()` + `users/me`; `unique_id = user id`
  (`unique-config-entry`). `test-before-configure`.
- Reauth (`async_step_reauth`): update API key only.
- Reconfigure (`async_step_reconfigure`): update URL + verify_ssl, keep key.
- Errors: invalid URL, `ImmichUnauthorizedError`, connection error.

## Quality scale — Platinum plan

`quality_scale.yaml` lists every canonical rule as `done`/`exempt` (comment on
each exempt). Manifest gets `"quality_scale": "platinum"` only once all rules are
`done`/`exempt`.

Likely `exempt` (with comments): `discovery`, `discovery-update-info`,
`dynamic-devices` is **done** (per-user devices), `repair-issues` (no repairable
condition), `docs-supported-devices` (service, not a device). `appropriate-polling`
= done (60 s poll justified).

Each `done` rule that is behavioural gets a test (hassfest checks structure, not
behaviour):
- `reconfiguration-flow` — reconfigure success + error tests.
- `diagnostics` — payload shape + key/host `**REDACTED**`.
- `stale-devices` — `async_remove_config_entry_device` → `False` while user
  present, `True` once gone.
- `entity/exception/icon-translations` — scrape `translation_key`s used in code,
  assert each resolves in `strings.json`.
- Jobs parser — unit test on a sample `/jobs` payload.
- Real setup-entry `LOADED` test (aioimmich mocked at the boundary, not our own
  functions); two-entry parallel LOADED test.

Platinum specifics: `strict-typing` (pyright standard, full annotations,
`from __future__ import annotations`, typed `ConfigEntry` alias), fully async (no
blocking I/O), `always_update=False`, `inject-websession`, `async-dependency`,
diagnostics.

## Repo scaffold

Full CI stack copied from the `ha-integration` skill `templates/`:
`semantic_release.yml`, `release.yml` (zip asset), `create-dev-pr.yml`,
`release_drafter.yml`, `pr-labeler.yml`, `lint_pr.yml`, `hacs_validate.yml`,
`hassfest_validate.yml`, `python_validate.yml` (py3.14), `check-manifest-version.yml`,
`quality_audit.yml` + `scripts/skill_audit.sh`; `.github/release-drafter.yml`,
`.github/pr-labeler.yml`, `.github/dependabot.yml`.

Root files: `CLAUDE.md` (skill-enforcement rule for future AI sessions),
`README.md` (AI-assistance disclaimer note + at least one image for HACS
`images` check), `hacs.json` (`zip_release`, `filename: immich_extras.zip`),
`pyproject.toml` (ruff/pylint py314), `pyrightconfig.json`, `.gitignore`,
`.githooks/commit-msg`.

Brand assets under `custom_components/immich_extras/brand/`: `icon.png` (256²),
`icon@2x.png` (512²), `logo.png`, `logo@2x.png`.

GitHub repo settings needed for HACS validation (set manually): description,
Issues enabled, at least one topic.

## Out of scope (YAGNI)

- Options flow / configurable interval (60 s fixed).
- Camera / image / media entities (core owns media browsing).
- Switches / buttons (trigger scan, favorite, delete) — no write actions v1.
- `notify` platform.
- Server-reachable binary sensor (redundant — coordinator failure already marks
  entities unavailable).
- `update_available` binary sensor (core's update entity owns version state).
