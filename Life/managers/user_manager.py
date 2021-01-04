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

import io
import logging
import math
import os
import random
import typing

import discord
import pendulum
from PIL import Image, ImageDraw, ImageFont
from discord.ext import tasks

from managers import reminder_manager
from utilities import exceptions, objects
from utilities.enums import Editables, Operations

log = logging.getLogger(__name__)


class UserConfigManager:

    def __init__(self, bot) -> None:
        self.bot = bot

        self.default_user_config = objects.DefaultUserConfig()
        self.configs = {}

        self.update_database.start()

        self.remind_manager = reminder_manager.ReminderManager(bot=self.bot)

    async def load(self) -> None:

        user_configs = await self.bot.db.fetch('SELECT * FROM user_configs')
        for user_config in user_configs:
            self.configs[user_config['id']] = objects.UserConfig(data=dict(user_config))

        log.info(f'[USER MANAGER] Loaded user configs. [{len(user_configs)} users]')
        print(f'[USER MANAGER] Loaded user configs. [{len(user_configs)} users]')

        await self.remind_manager.load()

    #

    @tasks.loop(seconds=60)
    async def update_database(self) -> None:

        if not self.configs:
            return

        need_updating = {user_id: user_config for user_id, user_config in self.configs.items() if len(user_config.requires_db_update) >= 1}

        async with self.bot.db.acquire(timeout=300) as db:
            for user_id, user_config in need_updating.items():

                query = ','.join(f'{editable.value} = ${index + 2}' for index, editable in enumerate(user_config.requires_db_update))
                values = [getattr(user_config, attribute.value) for attribute in user_config.requires_db_update]
                await db.execute(f'UPDATE user_configs SET {query} WHERE id = $1', user_id, *values)

                user_config.requires_db_update = []

    @update_database.before_loop
    async def before_update_database(self) -> None:

        await self.bot.wait_until_ready()

    #

    async def create_user_config(self, *, user_id: int) -> objects.UserConfig:

        data = await self.bot.db.fetchrow('INSERT INTO user_configs (id) values ($1) ON CONFLICT (id) DO UPDATE SET id = excluded.id RETURNING *', user_id)
        self.configs[user_id] = objects.UserConfig(data=dict(data))

        log.info(f'[USER MANAGER] Created config for user with id \'{user_id}\'')
        return self.configs[user_id]

    def get_user_config(self, *, user_id: int) -> typing.Union[objects.DefaultUserConfig, objects.UserConfig]:
        return self.configs.get(user_id, self.default_user_config)

    async def edit_user_config(self, *, user_id: int, editable: Editables, operation: Operations, value: typing.Any = None) -> objects.UserConfig:

        user_config = self.get_user_config(user_id=user_id)
        if isinstance(user_config, objects.DefaultUserConfig):
            user_config = await self.create_user_config(user_id=user_id)

        log.info(f'[USER MANAGERS] Edited user config for user with id \'{user_id}\'. Editable: {editable.value} | Operation: {operation.value} | Value: {value}')

        if editable == Editables.colour:

            operations = {
                Operations.set.value: ('UPDATE user_configs SET colour = $1 WHERE id = $2 RETURNING colour', f'0x{str(value).strip("#")}', user_id),
                Operations.reset.value: ('UPDATE user_configs SET colour = $1 WHERE id = $2 RETURNING colour', f'0x{str(discord.Colour.gold()).strip("#")}', user_id),
            }

            data = await self.bot.db.fetchrow(*operations[operation.value])
            user_config.colour = discord.Colour(int(data['colour'], 16))

        elif editable == Editables.blacklist:

            operations = {
                Operations.set.value:
                    ('UPDATE user_configs SET blacklisted = $1, blacklisted_reason = $2 WHERE id = $3 RETURNING blacklisted, blacklisted_reason', True, value, user_id),
                Operations.reset.value:
                    ('UPDATE user_configs SET blacklisted = $1, blacklisted_reason = $2 WHERE id = $3 RETURNING blacklisted, blacklisted_reason', False, None, user_id)
            }

            data = await self.bot.db.fetchrow(*operations[operation.value])
            user_config.blacklisted = data['blacklisted']
            user_config.blacklisted_reason = data['blacklisted_reason']

        elif editable == Editables.timezone:

            operations = {
                Operations.set.value: ('UPDATE user_configs SET timezone = $1 WHERE id = $2 RETURNING timezone', value, user_id),
                Operations.reset.value: ('UPDATE user_configs SET timezone = $1 WHERE id = $2 RETURNING timezone', 'UTC', user_id)
            }

            data = await self.bot.db.fetchrow(*operations[operation.value])
            user_config.timezone = pendulum.timezone(data['timezone'])

        elif editable == Editables.timezone_private:

            operations = {
                Operations.set.value: ('UPDATE user_configs SET timezone_private = $1 WHERE id = $2 RETURNING timezone_private', True, user_id),
                Operations.reset.value: ('UPDATE user_configs SET timezone_private = $1 WHERE id = $2 RETURNING timezone_private', False, user_id)
            }

            data = await self.bot.db.fetchrow(*operations[operation.value])
            user_config.timezone_private = data['timezone_private']

        elif editable == Editables.xp:

            if operation.value == 'add':
                user_config.xp += value
            elif operation.value == 'minus':
                user_config.xp -= value
            elif operation.value == 'set':
                user_config.xp = value

            if Editables.xp not in user_config.requires_db_update:
                user_config.requires_db_update.append(Editables.xp)

        elif editable == Editables.coins:

            if operation.value == 'add':
                user_config.coins += value
            elif operation.value == 'minus':
                user_config.coins -= value
            elif operation.value == 'set':
                user_config.coins = value

            if Editables.coins not in user_config.requires_db_update:
                user_config.requires_db_update.append(Editables.coins)

        elif editable == Editables.level_up_notifications:

            operations = {
                Operations.set.value: ('UPDATE user_configs SET level_up_notifications = $1 WHERE id = $2 RETURNING level_up_notifications', True, user_id),
                Operations.reset.value: ('UPDATE user_configs SET level_up_notifications = $1 WHERE id = $2 RETURNING level_up_notifications', False, user_id)
            }

            data = await self.bot.db.fetchrow(*operations[operation.value])
            user_config.level_up_notifications = data['level_up_notifications']

        elif editable in {Editables.daily_collected, Editables.weekly_collected, Editables.monthly_collected}:

            operations = {
                Operations.set.value: (f'UPDATE user_configs SET {editable.value} = $1 WHERE id = $2 RETURNING {editable.value}', value, user_id),
                Operations.reset.value: (f'UPDATE user_configs SET {editable.value} = $1 WHERE id = $2 RETURNING {editable.value}', pendulum.now(tz='UTC'), user_id)
            }

            data = await self.bot.db.fetchrow(*operations[operation.value])
            setattr(user_config, editable.value, pendulum.instance(data[editable.value], tz='UTC'))

        elif editable in {Editables.daily_streak, Editables.weekly_streak, Editables.monthly_streak}:

            value = getattr(user_config, editable.value)

            operations = {
                Operations.add.value: (f'UPDATE user_configs SET {editable.value} = $1 WHERE id = $2 RETURNING {editable.value}', value + 1, user_id),
                Operations.reset.value: (f'UPDATE user_configs SET {editable.value} = $1 WHERE id = $2 RETURNING {editable.value}', 0, user_id)
            }

            data = await self.bot.db.fetchrow(*operations[operation.value])
            setattr(user_config, editable.value, data[editable.value])

        elif editable == Editables.birthday:

            operations = {
                Operations.set.value: ('UPDATE user_configs SET birthday = $1 WHERE id = $2 RETURNING birthday', value, user_id),
                Operations.reset.value: ('UPDATE user_configs SET birthday = $1 WHERE id = $2 RETURNING birthday', pendulum.datetime(year=2020, month=1, day=1), user_id)
            }

            data = await self.bot.db.fetchrow(*operations[operation.value])
            user_config.birthday = pendulum.parse(data['birthday'].isoformat(), tz='UTC')

        elif editable == Editables.birthday_private:

            operations = {
                Operations.set.value: ('UPDATE user_configs SET birthday_private = $1 WHERE id = $2 RETURNING birthday_private', True, user_id),
                Operations.reset.value: ('UPDATE user_configs SET birthday_private = $1 WHERE id = $2 RETURNING birthday_private', False, user_id)
            }

            data = await self.bot.db.fetchrow(*operations[operation.value])
            user_config.birthday_private = data['birthday_private']

        elif editable == Editables.spotify_refresh_token:

            operations = {
                Operations.set.value: ('UPDATE user_configs SET spotify_refresh_token = $1 WHERE id = $2 RETURNING spotify_refresh_token', value, user_id),
                Operations.reset.value: ('UPDATE user_configs SET spotify_refresh_token = $1 WHERE id = $2 RETURNING spotify_refresh_token', None, user_id),
            }

            data = await self.bot.db.fetchrow(*operations[operation.value])
            user_config.spotify_refresh_token = data['spotify_refresh_token']

        return user_config

    #

    async def add_xp(self, *, user_id: int) -> None:

        if await self.bot.redis.exists(f'{user_id}_xp_gain') is True:
            return

        user_config = self.get_user_config(user_id=user_id)
        if isinstance(user_config, objects.DefaultUserConfig):
            user_config = await self.create_user_config(user_id=user_id)

        xp = random.randint(10, 25)

        if xp >= user_config.next_level_xp:
            self.bot.dispatch('xp_level_up', user_id, user_config)

        await self.edit_user_config(user_id=user_id, editable=Editables.xp, operation=Operations.add, value=xp)
        await self.bot.redis.setex(name=f'{user_id}_xp_gain', time=60, value=None)

    #

    async def create_timecard(self, *, guild_id: int) -> io.BytesIO:

        guild = self.bot.get_guild(guild_id)
        if not guild:
            raise exceptions.ArgumentError('Guild with that id not found.')

        configs = sorted(self.configs.items(), key=lambda kv: kv[1].time.offset_hours)
        timezone_users = {}

        for user_id, config in configs:

            if config.timezone_private or config.timezone == pendulum.timezone('UTC'):
                continue

            user = guild.get_member(user_id)
            if not user:
                continue

            if timezone_users.get(config.time.format('HH:mm (ZZ)')) is None:
                timezone_users[config.time.format('HH:mm (ZZ)')] = [io.BytesIO(await user.avatar_url_as(format='png', size=256).read())]

            else:
                timezone_users[config.time.format('HH:mm (ZZ)')].append(io.BytesIO(await user.avatar_url_as(format='png', size=256).read()))

        if not timezone_users:
            raise exceptions.ArgumentError('There are no users with timezones set in this server.')

        buffer = await self.bot.loop.run_in_executor(None, self.create_timecard_image, timezone_users)
        return buffer

    def create_timecard_image(self, timezone_users: dict) -> io.BytesIO:

        width_x = (1600 * (len(timezone_users.keys()) if len(timezone_users.keys()) < 5 else 5)) + 100
        height_y = (1800 * math.ceil(len(timezone_users.keys()) / 5)) + 100

        image = Image.new('RGBA', (width_x, height_y), color='#f1c30f')
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(os.path.abspath(os.path.join(os.path.dirname(__file__), '../resources/arial.ttf')), 120)

        x = 100
        y = 100

        for timezone, users in timezone_users.items():

            draw.text((x, y), timezone, font=font, fill='#1b1a1c')

            user_x = x
            user_y = y + 200

            for user in users[:36]:

                avatar = Image.open(user)
                avatar = avatar.resize((250, 250))

                image.paste(avatar, (user_x, user_y))

                if user_x < x + 1200:
                    user_x += 250
                else:
                    user_y += 250
                    user_x = x

            if x > 6400:
                y += 1800
                x = 100
            else:
                x += 1600

        buffer = io.BytesIO()
        image.save(buffer, 'png')
        buffer.seek(0)

        image.close()
        del image
        del draw
        del font

        return buffer

    #

    def rank(self, *, user_id: int, guild_id: int = None) -> int:

        if not guild_id:

            configs = sorted(self.configs.items(), key=lambda kv: kv[1].xp, reverse=True)

        else:

            guild = self.bot.get_guild(guild_id)
            if not guild:
                raise exceptions.ArgumentError('Guild with that id not found.')

            user_ids = [member.id for member in guild.members]
            configs = sorted({user_id: user_config for user_id, user_config in self.configs.items() if user_id in user_ids}.items(), key=lambda kv: kv[1].xp, reverse=True)

        return [config[0] for config in configs].index(user_id) + 1

    def leaderboard(self, *, leaderboard_type: typing.Literal['level', 'xp', 'coins'], guild_id: int = None) -> typing.List[objects.UserConfig]:

        if not guild_id:

            configs = {user_id: config for user_id, config in self.configs.items() if self.bot.get_user(user_id) is not None}.items()

        else:

            guild = self.bot.get_guild(guild_id)
            if not guild:
                raise exceptions.ArgumentError('Guild with that id not found.')

            member_ids = [member.id for member in guild.members]
            configs = {user_id: config for user_id, config in self.configs.items() if user_id in member_ids}.items()

        return sorted(configs, key=lambda kv: getattr(kv[1], leaderboard_type), reverse=True)
