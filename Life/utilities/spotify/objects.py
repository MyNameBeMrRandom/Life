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

import time
from typing import Literal, Optional, List
import pendulum

import aiohttp

from utilities.spotify import exceptions


class AppAccessToken:

    def __init__(self, access_token: str, token_type: str, expires_in: int, scope: str = None) -> None:

        self.access_token = access_token
        self.token_type = token_type
        self.expires_in = expires_in
        self.scope = scope

        self.time_authorized = time.time()

    @property
    def has_expired(self) -> bool:
        return (time.time() - self.time_authorized) >= self.expires_in

    @classmethod
    async def refresh(cls, client_id: str, client_secret: str, session: aiohttp.ClientSession) -> AppAccessToken:

        data = {
            'grant_type':    'client_credentials',

            'client_id':     client_id,
            'client_secret': client_secret
        }

        async with session.post('https://accounts.spotify.com/api/token', data=data) as post:
            data = await post.json()

            if (error := data.get('error')) is not None:
                raise exceptions.SpotifyRequestError(f'Error while requesting application access/refresh tokens: {error}')

        return cls(**data)


class UserAccessToken:

    def __init__(self, access_token: str, token_type: str, expires_in: int, scope: str, refresh_token: str) -> None:

        self.access_token = access_token
        self.token_type = token_type
        self.expires_in = expires_in

        self.scopes = scope
        self.refresh_token = refresh_token

        self.time_authorized = time.time()

    @property
    def has_expired(self) -> bool:
        return (time.time() - self.time_authorized) >= self.expires_in

    @classmethod
    async def refresh(cls, refresh_token: str, client_id: str, client_secret: str, session: aiohttp.ClientSession) -> UserAccessToken:

        data = {
            'grant_type':   'refresh_token',
            'refresh_token': refresh_token,

            'client_id':     client_id,
            'client_secret': client_secret
        }

        async with session.post('https://accounts.spotify.com/api/token', data=data) as post:
            data = await post.json()

            if (error := data.get('error')) is not None:
                raise exceptions.SpotifyRequestError(f'Error while refreshing user access token: {error}')

        return cls(**data)


class PagingObject:

    def __init__(self, data: dict) -> None:
        self.data = data

        self.href = data.get('href')
        self.items = data.get('items')
        self.limit = data.get('limit')
        self.next = data.get('next')
        self.offset = data.get('offset')
        self.previous = data.get('previous')
        self.total = data.get('total')

    def __repr__(self) -> str:
        return '<spotify.PagingObject>'


class SimpleAlbum:

    def __init__(self, data: dict) -> None:

        self.group: Literal['album', 'single', 'compilation', 'appears_on'] = data.get('album_group')
        self.type: Literal['album', 'type', 'compilation'] = data.get('album_type')
        self.artists = [SimpleArtist(artist) for artist in data.get('artists', [])]
        self.available_markets = data.get('available_markets', [])
        self.external_urls = data.get('external_urls')  # TODO: Format this somehow.
        self.href = data.get('href')
        self.id = data.get('id')
        self.images = [Image(image) for image in data.get('images', [])]
        self.name = data.get('name')
        self.release_date = pendulum.parse(data.get('release_date'), strict=False)
        self.release_data_precision = data.get('release_date_precision')
        self.restrictions = Restriction(data.get('restrictions'))
        self.type = data.get('type')
        self.uri = data.get('uri')

    def __repr__(self) -> str:
        return f'<spotify.SimpleAlbum name=\'{self.name}\' id=\'{self.id}\' url=\'<{self.url}>\' artists={self.artists}>'

    @property
    def url(self) -> Optional[str]:
        return self.external_urls.get('spotify')


class Album(SimpleAlbum):

    def __init__(self, data: dict) -> None:
        super().__init__(data)

        self.copyrights = data.get('copyrights')  # TODO: Maybe format this.
        self.external_ids = data.get('external_ids')  # TODO: Format this somehow.
        self.genres = data.get('genres', [])
        self.label = data.get('label')
        self.popularity = data.get('popularity')
        self.tracks = [SimpleTrack(track) for track in PagingObject(data.get('tracks', [])).items]
        self.total_tracks = data.get('total_tracks')

    def __repr__(self) -> str:
        return f'<spotify.Album name=\'{self.name}\' id=\'{self.id}\' url=\'<{self.url}>\' artists={self.artists} total_tracks=\'{self.total_tracks}\'>'


class SimpleArtist:

    def __init__(self, data: dict) -> None:

        self.external_urls = data.get('external_urls')  # TODO: Format this somehow.
        self.href = data.get('href')
        self.id = data.get('id')
        self.name = data.get('name')
        self.type = data.get('type')
        self.uri = data.get('uri')

    def __repr__(self) -> str:
        return f'<spotify.SimpleArtist name=\'{self.name}\' id=\'{self.id}\' url=\'<{self.url}>\'>'

    @property
    def url(self) -> Optional[str]:
        return self.external_urls.get('spotify')


class Artist(SimpleArtist):

    def __init__(self, data: dict) -> None:
        super().__init__(data)

        self.followers = Followers(data.get('followers'))
        self.genres = data.get('genres', [])
        self.images = [Image(image) for image in data.get('images', [])]
        self.popularity = data.get('popularity')

    def __repr__(self) -> str:
        return f'<spotify.Artist name=\'{self.name}\' id=\'{self.id}\' url=\'<{self.url}>\'>'


class SimpleTrack:

    def __init__(self, data: dict) -> None:

        self.artists = [SimpleArtist(artist) for artist in data.get('artists', [])]
        self.available_markets = data.get('available_markets')
        self.disk_number = data.get('disc_number')
        self.duration = data.get('duration_ms')
        self.explicit = data.get('explicit')
        self.external_urls = data.get('external_urls')  # TODO: Format this somehow.
        self.href = data.get('href')
        self.id = data.get('id')
        self.is_playable = data.get('is_playable')
        self.restrictions = Restriction(data.get('restrictions'))
        self.name = data.get('name')
        self.preview_url = data.get('preview_url')
        self.track_number = data.get('track_number')
        self.type = data.get('type')
        self.uri = data.get('uri')
        self.is_local = data.get('is_local')

    def __repr__(self) -> str:
        return f'<spotify.SimpleTrack name=\'{self.name}\' id=\'{self.id}\' url=\'<{self.url}>\' artists={self.artists}>'

    @property
    def url(self):
        return self.external_urls.get('spotify')


class Track(SimpleTrack):

    def __init__(self, data: dict) -> None:
        super().__init__(data)

        self.album = SimpleAlbum(data.get('album'))
        self.external_ids = data.get('external_ids')  # TODO: Format this somehow.
        self.popularity = data.get('popularity')

    def __repr__(self) -> str:
        return f'<spotify.Track name=\'{self.name}\' id=\'{self.id}\' url=\'<{self.url}>\' artists={self.artists} album={self.album}>'

    @property
    def images(self) -> Optional[List[Image]]:
        return getattr(self.album, 'images', [])



class Playlist:

    def __init__(self, data):
        super().__init__(data)

        self.items = [PlaylistTrack(track) for track in data['tracks']['items']]


class PlaylistTrack:

    def __init__(self, data):

        self.is_local = data.get('is_local')
        self.track = Track(data['track'])


class Recommendations:

    def __init__(self, data):

        self.tracks = [Track(t) for t in data['tracks']]
        self.seeds = data['seeds']  # TODO: Make a seeds class (sort of just debug data)


#


class Followers:

    def __init__(self, data: dict) -> None:

        self.href = data.get('href')
        self.total = data.get('total')

    def __repr__(self) -> str:
        return f'<spotify.Followers total={self.total}>'


class Image:

    def __init__(self, data: dict) -> None:

        self.url = data.get('url')
        self.width = data.get('width')
        self.height = data.get('height')

    def __repr__(self) -> str:
        return f'<spotify.Image url=\'<{self.url}>\' width=\'{self.width}\' height=\'{self.height}\'>'

    def __str__(self):
        return self.url


class Restriction:

    def __init__(self, data: dict) -> None:
        pass  # TODO: Finish this

