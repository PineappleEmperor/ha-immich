# Immich Extras

<img src="custom_components/immich_extras/brand/logo.png" alt="Immich Extras" width="320">

A [Home Assistant](https://www.home-assistant.io/) custom integration that
**complements the official core [`immich`](https://www.home-assistant.io/integrations/immich/)
integration** by exposing additional data from the [Immich](https://immich.app/)
server API as Home Assistant entities.

> [!NOTE]
> **AI assistance:** I'm a programmer; this project is built with AI (Claude, via Claude Code) for implementation, code review, and QA — under human direction, guided by my [`ha-integration`](https://github.com/PineappleEmperor/pineapple-claude-hacs) skill. Architecture and final review are mine; every change is human-reviewed before it merges.

## What it adds

The core `immich` integration already covers disk usage, global photo/video
counts, a version-update entity, media browsing and an `upload_file` service.
**Immich Extras does not duplicate any of that.** It adds:

- **Job/queue sensors** — active / waiting / failed totals across every Immich
  job queue, plus per-queue *waiting* sensors for thumbnail generation, metadata
  extraction, face detection, smart search, database backup and library scans.
- **Per-user usage & quota** — one device per Immich user with photo count,
  video count, storage used, quota size and quota-usage percentage.
- **My-account quota** — your own quota size, usage and percentage (works with a
  non-admin API key).
- **Counts & status** — people, tags and albums counts; a *Licensed* binary
  sensor; and a *Job failures* problem binary sensor.

### Use cases

- Notify when the **library-scan** or **backup** queue backs up, or when the
  *Job failures* sensor turns on.
- Track **per-user storage** and alert a household member approaching their quota.
- Put Immich **people / albums** counts on a dashboard.

### Supported functions

| Platform | Entities |
|----------|----------|
| `sensor` | people / tags / albums counts, my-account quota (size / used / %), total usage, job aggregates (active / waiting / failed), per-queue waiting, per-user (photos / videos / usage / quota / quota %) |
| `binary_sensor` | licensed, job failures (problem) |

Admin-only entities (per-user, total usage, jobs) appear **only** when the
configured API key belongs to an Immich admin.

## Installation

### HACS (recommended)

1. In HACS, add this repository as a **custom repository** (category: Integration):
   `https://github.com/PineappleEmperor/ha-immich`.
2. Install **Immich Extras**, then restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for
   *Immich Extras*.

### Manual

Copy `custom_components/immich_extras/` into your Home Assistant `config/custom_components/`
directory and restart.

## Configuration

Added via the UI (config flow). Parameters:

| Field | Required | Description |
|-------|----------|-------------|
| **URL** | yes | Full URL of your Immich server, e.g. `https://immich.example.com`. |
| **API key** | yes | An Immich API key (Account Settings → API Keys). An **admin** key unlocks the per-user, total-usage and job sensors; a non-admin key still provides my-account quota and the counts. |
| **Verify SSL certificate** | yes | Turn off only for a self-signed certificate. |

Connection settings can be changed later via **Reconfigure**; a new API key can be
supplied via **Reauthenticate** without removing the integration.

### Data update

The integration polls the Immich server every **60 seconds** via a single
coordinator. `always_update=False`, so entity state is only written when a value
changes.

## Examples

Alert on job failures:

```yaml
automation:
  - alias: Immich job failures
    triggers:
      - trigger: state
        entity_id: binary_sensor.immich_job_failures
        to: "on"
    actions:
      - action: notify.mobile_app_phone
        data:
          message: "Immich has failed background jobs."
```

## Removal

Delete the integration from **Settings → Devices & Services**. Per-user devices
are removed automatically once the user no longer exists on the server; a device
can also be deleted from its device page. Then remove the repository from HACS.

## Known limitations

- **Admin data needs an admin key.** Per-user usage, total usage and job sensors
  require an admin API key; Immich exposes those endpoints to admins only.
- **Jobs endpoint is unwrapped upstream.** Job data uses a thin raw call because
  `aioimmich` does not yet expose a jobs namespace; a future library change may
  supersede it.
- **Polling interval is fixed** at 60 seconds.

## Troubleshooting

- **Only a few sensors appear** — the API key is non-admin. Use an admin key to
  unlock per-user, total-usage and job entities.
- **Cannot connect / invalid auth** — verify the URL (scheme + port) and that the
  API key is valid; for a self-signed certificate, disable *Verify SSL*.
- **Deeper diagnostics** — download diagnostics from the integration's device
  page (secrets are redacted).

## Contributing

Enable the commit hook once per clone: `git config core.hooksPath .githooks`.
See [`CLAUDE.md`](CLAUDE.md) for the development workflow and checks.
