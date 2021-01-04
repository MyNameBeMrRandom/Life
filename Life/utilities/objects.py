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

import math

import discord
import pendulum


class DefaultGuildConfig:

    __slots__ = ('prefixes', 'colour', 'blacklisted', 'blacklisted_reason', 'embed_size', 'requires_db_update')

    def __init__(self) -> None:

        self.colour = discord.Colour.gold()
        self.prefixes = []

        self.blacklisted = False
        self.blacklisted_reason = 'None'

        self.embed_size = 'normal'

        self.requires_db_update = []

    def __repr__(self) -> str:
        return f'<DefaultGuildConfig colour=\'{self.colour}\' prefixes={self.prefixes}>'


class GuildConfig:

    __slots__ = ('prefixes', 'colour', 'blacklisted', 'blacklisted_reason', 'embed_size', 'requires_db_update')

    def __init__(self, data: dict) -> None:

        self.colour = discord.Colour(int(data.get('colour'), 16))
        self.prefixes = data.get('prefixes')

        self.blacklisted = data.get('blacklisted')
        self.blacklisted_reason = data.get('blacklisted_reason')

        self.embed_size = data.get('embed_size')

        self.requires_db_update = []

    def __repr__(self) -> str:
        return f'<GuildConfig colour=\'{self.colour}\' prefixes={self.prefixes}>'


class DefaultUserConfig:

    __slots__ = ('colour', 'blacklisted', 'blacklisted_reason', 'timezone', 'timezone_private', 'coins', 'xp', 'level_up_notifications', 'daily_collected', 'weekly_collected',
                 'monthly_collected', 'daily_streak', 'weekly_streak', 'monthly_streak', 'created_at', 'birthday', 'birthday_private', 'spotify_refresh_token', 'reminders',
                 'requires_db_update')

    def __init__(self) -> None:

        self.colour = discord.Colour.gold()

        self.blacklisted = False
        self.blacklisted_reason = 'None'

        self.timezone = pendulum.timezone('UTC')
        self.timezone_private = False

        self.xp = 0
        self.coins = 0

        self.level_up_notifications = False

        self.daily_collected = pendulum.now(tz='UTC')
        self.weekly_collected = pendulum.now(tz='UTC')
        self.monthly_collected = pendulum.now(tz='UTC')

        self.daily_streak = 0
        self.weekly_streak = 0
        self.monthly_streak = 0

        self.created_at = pendulum.now(tz='UTC')

        self.birthday = pendulum.DateTime(2020, 1, 1, 0, 0, 0, tzinfo=pendulum.timezone('UTC'))
        self.birthday_private = False

        self.spotify_refresh_token = None

        self.reminders = []
        self.requires_db_update = []

    def __repr__(self) -> str:
        return f'<DefaultUserConfig colour=\'{self.colour}\' coins={self.coins}>'

    @property
    def age(self) -> int:
        return (pendulum.now(tz="UTC") - self.birthday).in_years()

    @property
    def next_birthday(self) -> pendulum.datetime:
        return self.birthday.replace(year=self.birthday.year + self.age + 1)

    @property
    def time(self) -> pendulum.datetime:
        return pendulum.now(tz=self.timezone)

    @property
    def level(self) -> int:
        return math.floor((((self.xp / 100) ** (1.0 / 1.5)) / 3))

    @property
    def next_level_xp(self) -> int:
        return round((((((self.level + 1) * 3) ** 1.5) * 100) - self.xp))


class UserConfig:

    __slots__ = ('colour', 'blacklisted', 'blacklisted_reason', 'timezone', 'timezone_private', 'coins', 'xp', 'level_up_notifications', 'daily_collected', 'weekly_collected',
                 'monthly_collected', 'daily_streak', 'weekly_streak', 'monthly_streak', 'created_at', 'birthday', 'birthday_private', 'spotify_refresh_token', 'reminders',
                 'requires_db_update')

    def __init__(self, data: dict) -> None:

        self.colour = discord.Colour(int(data.get('colour'), 16))

        self.blacklisted = data.get('blacklisted')
        self.blacklisted_reason = data.get('blacklisted_reason')

        self.timezone = pendulum.timezone(data.get('timezone'))
        self.timezone_private = data.get('timezone_private')

        self.xp = data.get('xp')
        self.coins = data.get('coins')

        self.level_up_notifications = data.get('level_up_notifications')

        self.daily_collected = pendulum.instance(data.get('daily_collected'), tz='UTC')
        self.weekly_collected = pendulum.instance(data.get('weekly_collected'), tz='UTC')
        self.monthly_collected = pendulum.instance(data.get('monthly_collected'), tz='UTC')

        self.daily_streak = data.get('daily_streak')
        self.weekly_streak = data.get('weekly_streak')
        self.monthly_streak = data.get('monthly_streak')

        self.created_at = pendulum.instance(data.get('created_at'), tz='UTC')

        self.birthday = pendulum.parse(data.get('birthday').isoformat(), tz='UTC')
        self.birthday_private = data.get('birthday_private')

        self.spotify_refresh_token = data.get('spotify_refresh_token')

        self.reminders = []
        self.requires_db_update = []

    def __repr__(self) -> str:
        return f'<UserConfig colour=\'{self.colour}\' coins={self.coins}>'

    @property
    def age(self) -> int:
        return (pendulum.now(tz="UTC") - self.birthday).in_years()

    @property
    def next_birthday(self) -> pendulum.datetime:
        return self.birthday.replace(year=self.birthday.year + self.age + 1)

    @property
    def time(self) -> pendulum.datetime:
        return pendulum.now(tz=self.timezone)

    @property
    def level(self) -> int:
        return math.floor((((self.xp / 100) ** (1.0 / 1.5)) / 3))

    @property
    def next_level_xp(self) -> int:
        return round((((((self.level + 1) * 3) ** 1.5) * 100) - self.xp))


class Reminder:

    __slots__ = ('user_id', 'channel_id', 'message_id', 'id', 'datetime', 'created_at', 'content', 'link', 'dm', 'task')

    def __init__(self, data: dict) -> None:

        self.user_id = data.get('user_id')
        self.channel_id = data.get('channel_id')
        self.message_id = data.get('message_id')
        self.id = data.get('id')
        self.datetime = pendulum.instance(data.get('datetime'), tz='UTC')
        self.created_at = pendulum.instance(data.get('created_at'), tz='UTC')
        self.content = data.get('content')
        self.link = data.get('link')
        self.dm = data.get('dm')

        self.task = None

    def __repr__(self) -> str:
        return f'<Reminder user_id={self.user_id} id={self.id} datetime={self.datetime} done={self.done}>'

    @property
    def done(self) -> bool:
        return pendulum.now(tz='UTC') > self.datetime
