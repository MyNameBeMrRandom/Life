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

import secrets

import discord
from discord.ext import commands

from bot import Life
from utilities import context, exceptions
from utilities.spotify import client


class Radio(commands.Cog):

    def __init__(self, bot: Life) -> None:
        self.bot = bot

        self.bot.spotify = client.Client(bot=self.bot)

    @commands.command(name='authorise', aliases=['auth'])
    async def authorise(self, ctx: context.Context) -> None:

        if ctx.author.id not in self.bot.spotify.user_states.values():
            self.bot.spotify.user_states[secrets.token_urlsafe(nbytes=32)] = ctx.author.id

        url = f'https://accounts.spotify.com/authorize/?' \
              f'client_id={self.bot.config.spotify_client_id}&' \
              f'response_type=code&' \
              f'redirect_uri=http://{self.bot.config.web_url}/api/spotify/callback&' \
              f'state={list(self.bot.spotify.user_states.keys())[list(self.bot.spotify.user_states.values()).index(ctx.author.id)]}&' \
              f'scope=user-read-recently-played+user-top-read+user-read-currently-playing+playlist-read-private+playlist-read-collaborative&' \
              f'show_dialog=True'

        embed = discord.Embed(colour=ctx.colour, title='Spotify authorisation link:',
                              description=f'Please click [this link]({url}) to authorise this discord account with your spotify account. Do not share this link with anyone as '
                                          f'it will allow people to link their spotify with your account.')

        try:
            await ctx.author.send(embed=embed)
        except discord.Forbidden:
            raise exceptions.VoiceError('I am unable to send direct messages to you, please enable them so that I can DM you your spotify authorisation link.')


def setup(bot: Life):
    bot.add_cog(Radio(bot))
