#  Lif
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

import enum


class Operations(enum.Enum):

    set = 'set'
    update = 'set'

    reset = 'reset'
    clear = 'reset'

    add = 'add'

    remove = 'remove'
    minus = 'remove'


class Editables(enum.Enum):

    colour = 'colour'

    prefixes = 'prefixes'

    timezone = 'timezone'
    timezone_private = 'timezone_private'

    blacklist = 'blacklist'

    coins = 'coins'
    xp = 'xp'

    level_up_notifications = 'level_up_notifications'

    daily_collected = 'daily_collected'
    daily_streak = 'daily_streak'

    weekly_collected = 'weekly_collected'
    weekly_streak = 'weekly_streak'

    monthly_collected = 'monthly_collected'
    monthly_streak = 'monthly_streak'

    birthday = 'birthday'
    birthday_private = 'birthday_private'

    embed_size = 'embed_size'

    spotify_refresh_token = 'spotify_refresh_token'


