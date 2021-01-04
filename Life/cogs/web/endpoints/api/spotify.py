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

from typing import TYPE_CHECKING
import aiohttp.web

from utilities.enums import Editables, Operations
from utilities.spotify import exceptions, objects

if TYPE_CHECKING:
    from bot import Life


class Spotify:

    async def get(self, request: aiohttp.web.Request):

        bot: Life = request.app.bot

        if (state := request.query.get('state')) is None:
            return aiohttp.web.json_response({'error': 'state parameter not found.'}, status=401)

        if (user := bot.get_user(bot.spotify.user_states.get(state))) is None:
            return aiohttp.web.json_response({'error': 'user matching state parameter not found.'}, status=401)

        #

        if (error := request.query.get('error')) is not None:
            await user.send(f'Something went wrong while connecting your spotify account, please try again.')
            return aiohttp.web.json_response({'error': error}, status=401)

        elif (code := request.query.get('code')) is not None:

            data = {
                'grant_type':   'authorization_code',
                'code':         code,
                'redirect_uri': f'http://{request.app.bot.config.web_url}/api/spotify/callback',

                'client_id':     request.app.bot.config.spotify_client_id,
                'client_secret': request.app.bot.config.spotify_client_secret
            }

            async with request.app.session.post('https://accounts.spotify.com/api/token', data=data) as post:

                data = await post.json()

                if (error := data.get('error')) is not None:
                    raise exceptions.SpotifyRequestError(f'Error while requesting user access/refresh tokens: {error}')

            await bot.user_manager.edit_user_config(user_id=user.id, editable=Editables.spotify_refresh_token, operation=Operations.set, value=data.get('refresh_token'))

            bot.spotify.user_access_tokens[user.id] = objects.UserAccessToken(**data)
            del bot.spotify.user_states[state]

            await user.send(f'Your spotify account was successfully linked.')
            return aiohttp.web.Response(body='Spotify account link was successful, you can close this page now.', status=200)

        return aiohttp.web.Response(status=500)


def setup(app: aiohttp.web.Application) -> None:

    spotify = Spotify()

    app.add_routes([
        aiohttp.web.get(r'/api/spotify/callback', spotify.get),
    ])
