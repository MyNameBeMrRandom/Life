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

import collections
import logging
import time
from typing import Dict, Optional, Union

import aiohttp
import aredis
import asyncpg
import discord
import mystbin
import psutil
from discord.ext import commands

from cogs.web import main
from cogs.web.main import LifeWeb
from config import config
from managers import guild_manager, user_manager
from utilities import context, help, objects, spotify, utils

__log__ = logging.getLogger(__name__)


class Life(commands.AutoShardedBot):

    def __init__(self) -> None:
        super().__init__(
                command_prefix=self.get_prefix, reconnect=True, help_command=help.HelpCommand(),
                activity=discord.Game(name='Cyberpunk 2069'),
                intents=discord.Intents(guilds=True, members=True, bans=False, emojis=False, integrations=False, webhooks=False, invites=False, voice_states=True, presences=True,
                                        messages=True, reactions=True, typing=False)
        )

        self.text_permissions = discord.Permissions(read_messages=True, send_messages=True, embed_links=True, attach_files=True, read_message_history=True, add_reactions=True,
                                                    external_emojis=True)
        self.voice_permissions = discord.Permissions(read_messages=True, send_messages=True, embed_links=True, attach_files=True, read_message_history=True, add_reactions=True,
                                                     external_emojis=True, connect=True, speak=True, use_voice_activation=True)

        self.session = aiohttp.ClientSession(loop=self.loop)
        self.config = config.Config(bot=self)
        self.utils = utils.Utils(bot=self)

        self.guild_manager = guild_manager.GuildConfigManager(bot=self)
        self.user_manager = user_manager.UserConfigManager(bot=self)

        self.socket_stats = collections.Counter()
        self.process = psutil.Process()
        self.start_time = time.time()

        self.mentions_dms_webhook = discord.Webhook.from_url(url=self.config.mentions_dms_url, adapter=discord.AsyncWebhookAdapter(self.session))
        self.logging_webhook = discord.Webhook.from_url(url=self.config.logging_url, adapter=discord.AsyncWebhookAdapter(self.session))
        self.errors_webhook = discord.Webhook.from_url(url=self.config.errors_url, adapter=discord.AsyncWebhookAdapter(self.session))

        self.invite = discord.utils.oauth_url(client_id=self.config.client_id, permissions=discord.Permissions(37080128))
        self.github = f'https://github.com/Axelancerr/Life'
        self.support = f'https://discord.gg/xP8xsHr'

        self.commands_not_allowed_dms = {
            'join', 'play', 'leave', 'skip', 'pause', 'unpause', 'seek', 'volume', 'now_playing', 'queue', 'queue sort', 'queue remove', 'queue history', 'queue history clear',
            'queue history detailed', 'queue shuffle', 'queue clear', 'queue move', 'queue history reverse', 'queue detailed', 'queue loop',

            'icon', 'banner', 'splash', 'server', 'channels', 'member',

            'tag', 'tag create', 'tag transfer', 'tag list', 'tag edit', 'tag all', 'tag delete', 'prefix claim', 'tag info', 'tag search', 'tag raw', 'tag alias',

            'config', 'config prefix', 'config colour',

            'timecard'
        }

        self.first_ready = True

        self.error_formatter = None
        self.imaging = None

        self.redis: Optional[aredis.StrictRedis] = None
        self.mystbin: Optional[mystbin.Client] = None
        self.db: Optional[asyncpg.Connection] = None

        self.life_web: Optional[LifeWeb] = None
        self.spotify: Optional[spotify.client.Client] = None

    async def get_context(self, message: discord.Message, *, cls=context.Context) -> context.Context:
        return await super().get_context(message, cls=cls)

    async def is_owner(self, person: Union[discord.User, discord.Member]) -> bool:
        return person.id in self.config.owner_ids

    async def get_prefix(self, message: discord.Message) -> list:

        if not message.guild:
            return commands.when_mentioned_or(self.config.prefix, 'I-', '')(self, message)

        guild_config = self.guild_manager.get_guild_config(guild_id=message.guild.id)
        if isinstance(guild_config, objects.DefaultGuildConfig):
            return commands.when_mentioned_or(self.config.prefix, 'I-')(self, message)

        return commands.when_mentioned_or(self.config.prefix, 'I-', *guild_config.prefixes)(self, message)

    async def command_check(self, ctx: context.Context) -> bool:

        if ctx.user_config.blacklisted is True and ctx.command.qualified_name not in {'help', 'support'}:
            raise commands.CheckFailure(f'You are blacklisted from using this bot with the reason:\n\n`{ctx.user_config.blacklisted_reason}`')

        elif ctx.guild_config.blacklisted is True and ctx.command.qualified_name not in {'help', 'support'}:
            raise commands.CheckFailure(f'This guild is blacklisted from using this bot with the reason:\n\n`{ctx.guild_config.blacklisted_reason}`')

        if ctx.guild is None and ctx.command.qualified_name in self.commands_not_allowed_dms:
            raise commands.NoPrivateMessage()

        current_permissions = dict(ctx.me.permissions_in(ctx.channel))
        needed_permissions = {permission: value for permission, value in self.text_permissions if value is True}

        if ctx.command.cog and ctx.command.cog in {self.get_cog('Music')}:
            if (channel := getattr(ctx.author.voice, 'channel', None)) is not None:
                needed_permissions.update({permission: value for permission, value in self.voice_permissions if value is True})
                current_permissions.update({permission: value for permission, value in ctx.me.permissions_in(channel) if value is True})

        missing = [permissions for permissions, value in needed_permissions.items() if current_permissions[permissions] != value]

        if missing:
            raise commands.BotMissingPermissions(missing)

        return True

    async def on_ready(self) -> None:

        if self.first_ready is False:
            return

        self.first_ready = False

        self.life_web = await main.load(bot=self)

        await self.user_manager.load()
        await self.guild_manager.load()

        for cog in self.cogs.values():
            if hasattr(cog, 'load'):
                await cog.load()

    async def start(self, *args, **kwargs) -> None:

        try:
            __log__.debug('[PSQL] Attempting connection.')
            db = await asyncpg.create_pool(**self.config.postgresql, max_inactive_connection_lifetime=0)
        except Exception as e:
            __log__.critical(f'[PSQL] Error while connecting.\n{e}\n')
            print(f'\n[POSTGRESQL] An error occurred while connecting to PostgreSQL: {e}')
            raise ConnectionError
        else:
            __log__.info('[PSQL] Successful connection.')
            print(f'\n[POSTGRESQL] Connected to the PostgreSQL database.')
            self.db = db

        try:
            __log__.debug(f'[REDIS] Attempting connection to \'{self.config.redis["host"]}:{self.config.redis["port"]}\' on DB \'{self.config.redis["db"]}\'.')
            redis = aredis.StrictRedis(**self.config.redis)
            await redis.set('connected', 0)
        except aredis.ConnectionError or aredis.ResponseError:
            __log__.critical(f'[REDIS] Error while connecting to Redis DB number \'{self.config.redis["db"]}\'.')
            raise ConnectionError(f'Error while connecting to Redis DB number \'{self.config.redis["db"]}\'.')
        else:
            __log__.info(f'[REDIS] Successful connection to Redis at \'{self.config.redis["host"]}:{self.config.redis["port"]}\' on DB \'{self.config.redis["db"]}\'.')
            print(f'[REDIS] Successful connection to Redis DB number \'{self.config.redis["db"]}\'. \n')
            self.redis = redis

        for extension in self.config.extensions:
            try:
                self.load_extension(extension)
                __log__.info(f'[EXTENSIONS] Loaded - {extension}')
                print(f'[EXTENSIONS] Loaded - {extension}')
            except commands.ExtensionNotFound:
                __log__.warning(f'[EXTENSIONS] Extension not found - {extension}')
                print(f'[EXTENSIONS] Extension not found - {extension}')
            except commands.NoEntryPointError:
                __log__.warning(f'[EXTENSIONS] No entry point - {extension}')
                print(f'[EXTENSIONS] No entry point - {extension}')
            except commands.ExtensionFailed as error:
                __log__.warning(f'[EXTENSIONS] Failed - {extension} - Reason: {error}')
                print(f'[EXTENSIONS] Failed - {extension} - Reason: {error}')

        self.add_check(self.command_check)
        await super().start(*args, **kwargs)

    async def close(self) -> None:

        __log__.info('[BOT] Closing bot down.')
        print('\n[BOT] Closing bot down.')

        __log__.info('[BOT] Closing database connection.')
        print('[DB] Closing database connection.')
        await self.db.close()

        __log__.info('[BOT] Closing aiohttp client session.')
        print('[CS] Closing aiohttp client session.')
        await self.session.close()

        __log__.info('[BOT] Bot has shutdown.')
        print('Bye bye!')
        await super().close()
