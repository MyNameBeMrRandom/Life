#  Life
#  Copyright (C) 2020 Axel#3456
#
#  Life is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software
#  Foundation, either version 3 of the License, or (at your option) any later version.
#
#  Life is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
#  PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License along with Life. If not, see https://www.gnu.org/licenses/.
#

from __future__ import annotations

from typing import Dict, Literal, Optional, TYPE_CHECKING, Union
from urllib.parse import quote

import aiohttp

from utilities.spotify import exceptions, objects

if TYPE_CHECKING:
    from bot import Life

BASE_ENDPOINT = 'https://api.spotify.com/v1'


async def json_or_text(response: aiohttp.ClientResponse) -> Union[str, dict]:

    if response.headers['Content-Type'] == 'application/json; charset=utf-8':
        return await response.json()

    return await response.text()


class Request:

    def __init__(self, method: Literal['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'PATCH'], route: str, **params):

        self.method = method
        self.params = params

        self.url = (BASE_ENDPOINT + route)
        if params:
            self.url = self.url.format(**{key: quote(value) if isinstance(value, str) else value for key, value in params.items()})


class Client:

    def __init__(self, bot: Life) -> None:

        self.bot = bot
        self.client_id = bot.config.spotify_client_id
        self.client_secret = bot.config.spotify_client_secret

        self.user_access_tokens: Dict[int, objects.UserAccessToken] = {}
        self.user_states: Dict[str, int] = {}

        self.access_token: Optional[objects.AppAccessToken] = None

    def __repr__(self) -> str:
        return f'<spotify.Client bot={self.bot}>'

    #

    async def _request(self, request: Request, access_token: Union[objects.AppAccessToken, objects.UserAccessToken] = None, *, params=None):

        if not access_token:

            if not self.access_token:
                self.access_token = await objects.AppAccessToken.refresh(client_id=self.client_id, client_secret=self.client_secret, session=self.bot.session)
            access_token = self.access_token

        if access_token.has_expired:
            if isinstance(access_token, objects.UserAccessToken):
                access_token = access_token.refresh(refresh_token=access_token.refresh_token, client_id=self.client_id, client_secret=self.client_secret, session=self.bot.session)
            else:
                access_token = access_token.refresh(client_id=self.client_id, client_secret=self.client_secret, session=self.bot.session)

        headers = {
            'Content-Type':  f'application/json',
            'Authorization': f'Bearer {access_token.access_token}'
        }

        async with self.bot.session.request(request.method, request.url, headers=headers, params=params) as request:
            data = await json_or_text(request)

            if 200 <= request.status < 300:
                return data

            if error := data.get('error'):
                raise exceptions.SpotifyException(error)

            return data

    #

    async def get_album(self, album_id: str) -> objects.Album:
        request = await self._request(Request('GET', '/albums/{album_id}', album_id=album_id))
        return objects.Album(request)

    async def get_artist(self, artist_id: str) -> objects.Artist:
        request = await self._request(Request('GET', '/artists/{artist_id}', artist_id=artist_id))
        return objects.Artist(request)

    async def get_track(self, track_id: str) -> objects.Track:
        request = await self._request(Request('GET', '/tracks/{track_id}', track_id=track_id))
        return objects.Track(request)



    async def get_playlist(self, playlist_id: str):
        r = await self._request(Request("GET", "playlists/{p_id}", p_id=playlist_id))
        return objects.Playlist(r)

    async def recommendations(self, *, limit: int = 5, **p):

        params = dict(limit=limit)

        # TODO: Limit seeds to a total of 5
        valid_seeds = {"seed_artists", "seed_genres", "seed_tracks"}
        for seed in valid_seeds:
            if values := p.get(seed):
                params[seed] = ",".join(values)

        r = await self._request(Request("GET", "recommendations"), params=params)
        return objects.Recommendations(r)
