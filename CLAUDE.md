# Immich Extras — project instructions

Home Assistant custom integration (`custom_components/immich_extras/`) that
complements the HA **core** `immich` integration with extra server sensors
(jobs, per-user usage/quota, my-account quota, people/tags/albums counts).

## AI sessions

Before writing or modifying integration code (config flow, platforms, manifest,
coordinator, services…), invoke the `ha-integration` skill. Re-invoke it after any
`/compact`, since compaction can drop the skill's guidance from context.

## Repo setup

Enable the commit hook once per clone (terse subjects, no AI-attribution trailers):

```
git config core.hooksPath .githooks
```

## Boundaries

Do not rebuild what core `immich` already provides: disk sensors, photo/video
counts, usage-by-type, the update entity, media browsing, or the `upload_file`
service. This integration adds only the data core omits.

## Checks before a PR

```
ruff check custom_components/
python -m pyright custom_components/
python -m pytest
bash scripts/skill_audit.sh
```
