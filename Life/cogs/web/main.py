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

import importlib
import logging
from typing import TYPE_CHECKING

import aiohttp.web

if TYPE_CHECKING:
    from bot import Life

__log__ = logging.getLogger(__name__)


class LifeWeb(aiohttp.web.Application):

    def __init__(self, bot: Life) -> None:
        super().__init__()

        self.bot = bot
        self.session = aiohttp.ClientSession()


async def load(bot: Life) -> LifeWeb:

    app = LifeWeb(bot=bot)
    endpoints = ['api.spotify']

    for endpoint in [importlib.import_module(f'cogs.web.endpoints.{endpoint}') for endpoint in endpoints]:
        endpoint.setup(app=app)

    runner = aiohttp.web.AppRunner(app=app)
    await runner.setup()

    site = aiohttp.web.TCPSite(runner, bot.config.web_address, bot.config.web_port)
    await site.start()

    return app
