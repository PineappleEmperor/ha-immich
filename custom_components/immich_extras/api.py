"""Thin wrapper over aioimmich, plus the raw jobs shim."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aioimmich import Immich

from .models import ImmichExtrasData, JobCounts, parse_jobs

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from aioimmich.users.models import ImmichUserObject


class ImmichExtrasApi:
    """Fetches the data this integration exposes from an Immich server.

    Wraps the ``aioimmich`` namespaces for everything the library covers and
    adds a single raw call for the ``/jobs`` endpoint, which aioimmich does not
    yet wrap. Keeping the raw call isolated here means an upstream change (or a
    future jobs namespace) touches exactly one method.
    """

    def __init__(
        self,
        session: ClientSession,
        api_key: str,
        host: str,
        port: int,
        use_ssl: bool,
    ) -> None:
        """Initialise the API wrapper."""
        self._immich = Immich(session, api_key, host, port, use_ssl, "home-assistant")
        self._setup_done = False

    async def async_setup(self) -> ImmichUserObject:
        """Perform the one-time library setup and return the authenticated user."""
        if not self._setup_done:
            await self._immich.async_setup()
            self._setup_done = True
        return await self._immich.users.async_get_my_user()

    async def async_get_jobs(self) -> dict[str, JobCounts]:
        """Fetch job-queue counts via the raw jobs endpoint (admin only)."""
        raw = await self._immich.api.async_do_request("jobs")
        assert isinstance(raw, dict)
        return parse_jobs(raw)

    async def async_get_data(self, *, is_admin: bool) -> ImmichExtrasData:
        """Fetch a full snapshot of the data this integration exposes.

        Admin-only data (server statistics, jobs) is fetched only when the
        authenticated API key belongs to an admin; for a non-admin key those
        fields are ``None`` and no request is made.
        """
        my_user = await self._immich.users.async_get_my_user()
        about = await self._immich.server.async_get_about_info()
        people_count = await self._immich.people.async_get_people_count()
        tags_count = len(await self._immich.tags.async_get_all_tags())
        albums_count = len(await self._immich.albums.async_get_all_albums())

        statistics = None
        jobs = None
        if is_admin:
            statistics = await self._immich.server.async_get_server_statistics()
            jobs = await self.async_get_jobs()

        return ImmichExtrasData(
            my_user=my_user,
            licensed=about.licensed,
            people_count=people_count,
            tags_count=tags_count,
            albums_count=albums_count,
            statistics=statistics,
            jobs=jobs,
        )
