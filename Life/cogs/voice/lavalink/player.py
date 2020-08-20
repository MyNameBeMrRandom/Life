import asyncio
import time
from abc import ABC

import async_timeout

import discord
from discord import VoiceProtocol

from cogs.voice.lavalink import objects, queue
from utilities import exceptions


class Player(VoiceProtocol, ABC):

    def __init__(self, bot, channel: discord.VoiceChannel) -> None:

        self.bot = self.client = bot
        self.channel = channel
        self.guild = channel.guild

        self.text_channel = None
        self.node = None
        self.task = None

        self.paused = False
        self.current = None
        self.volume = 100

        self.last_position = 0
        self.last_update = 0
        self.last_time = 0

        self.voice_state = {}

        self.queue = queue.Queue(player=self)
        self.past_queue = queue.Queue(player=self)

        self.wait_queue_add = asyncio.Event()
        self.wait_track_start = asyncio.Event()
        self.wait_track_end = asyncio.Event()

    def __repr__(self) -> str:
        return f'<LavaLinkPlayer node={self.node!r} guild={self.guild!r} channel={self.channel!r}>'

    async def on_voice_server_update(self, data: dict) -> None:

        self.voice_state.update({'event': data})
        await self.dispatch_voice_update()

    async def on_voice_state_update(self, data: dict) -> None:

        self.voice_state.update({'sessionId': data.get('session_id')})

        channel_id = data.get('channel_id')
        if not channel_id:
            self.voice_state.clear()
            return

        self.channel = self.guild.get_channel(int(channel_id))
        await self.dispatch_voice_update()

    async def dispatch_voice_update(self) -> None:

        if {'sessionId', 'event'} == self.voice_state.keys():
            await self.node.send(op='voiceUpdate', guildId=str(self.guild.id), **self.voice_state)

    async def dispatch_event(self, *, data: dict) -> None:

        event = getattr(objects, data.pop('type'), None)
        if not event:
            return

        event = event(data)
        self.bot.dispatch(str(event), event)

    async def update_state(self, *, data: dict) -> None:

        player_state = data.get('state')

        self.last_position = player_state.get('position', 0)
        self.last_time = player_state.get('time', 0)
        self.last_update = time.time() * 1000

    @property
    def is_connected(self) -> bool:
        return self.channel is not None

    @property
    def is_playing(self) -> bool:
        return self.is_connected is True and self.current is not None

    @property
    def is_paused(self) -> bool:
        return self.paused is True

    @property
    def position(self) -> float:

        if not self.is_playing or not self.current:
            return 0

        if self.paused:
            return min(self.last_position, self.current.length)

        position = self.last_position + ((time.time() * 1000) - self.last_update)

        if position > self.current.length:
            return 0

        return min(position, self.current.length)

    async def connect(self, *, timeout: float, reconnect: bool) -> None:

        await self.guild.change_voice_state(channel=self.channel, self_deaf=True)
        self.task = self.bot.loop.create_task(self.loop())

    async def disconnect(self, *, force: bool = True) -> None:

        await self.guild.change_voice_state(channel=None)
        self.cleanup()

        self.channel = None

    async def stop(self) -> None:

        await self.node.send(op='stop', guildId=str(self.guild.id))
        self.current = None

    async def destroy(self) -> None:

        await self.disconnect()

        if self.node.is_connected:
            await self.stop()
            await self.node.send(op='destroy', guildId=str(self.guild.id))

        self.task.cancel()
        del self.node.players[self.guild.id]

    async def play(self, *, track: objects.Track, start: int = 0, end: int = 0) -> None:

        self.last_position = 0
        self.last_time = 0
        self.last_update = 0

        payload = {
            'op': 'play',
            'guildId': str(self.guild.id),
            'track': str(track.track_id),
        }
        if 0 < start < track.length:
            payload['startTime'] = start
        if 0 < end < track.length:
            payload['endTime'] = end

        await self.node.send(**payload)
        self.current = track

    async def set_position(self, *, position: int) -> None:

        if not self.current:
            return

        await self.node.send(op='seek', guildId=str(self.guild.id), position=position)

    async def set_volume(self, *, volume: int) -> None:

        await self.node.send(op='volume', guildId=str(self.guild.id), volume=volume)
        self.volume = volume

    async def set_pause(self, *, pause: bool) -> None:

        await self.node.send(op='pause', guildId=str(self.guild.id), pause=pause)
        self.paused = pause

    async def send(self, *, message: str = None, embed: discord.Embed = None) -> None:

        if not self.text_channel:
            return

        try:
            if message:
                await self.text_channel.send(message)
            if embed:
                await self.text_channel.send(embed=embed)
        except discord.Forbidden:
            return

    async def invoke_controller(self):

        track = self.current

        embed = discord.Embed(title='Life bot music controller:', colour=track.ctx.colour)
        embed.add_field(name=f'Now playing:', value=f'**[{track.title}]({track.uri})**', inline=False)

        embed.add_field(name='Track info:', value=f'Author: `{track.author}`\nSource: `{track.source.title()}`\nRequester: {track.requester.mention}')
        embed.add_field(name='\u200B', value='\u200B')
        time_format = f'`{self.bot.utils.format_time(round(self.position) / 1000)} / {self.bot.utils.format_time(round(track.length) / 1000)}`'
        embed.add_field(name='Player info:', value=f'Time: {time_format}\nPaused: `{self.is_paused}\n`Volume: `{self.volume}`')

        embed.add_field(name='Queue info:', value=f'Looping: `{self.queue.is_looping}`\nEntries: `{len(self.queue)}`')

        entries = [f'`{index + 1}.` [{str(entry.title)}]({track.uri}) | `{self.bot.utils.format_time(round(entry.length) / 1000)}` | '
                   f'{entry.requester.mention}' for index, entry in enumerate(self.queue[:5])]
        embed.add_field(name='Up next:', value='\n'.join(entries) if entries else 'There are no tracks in the queue.', inline=False)

        embed.set_thumbnail(url=track.thumbnail)
        await self.send(embed=embed)

    async def loop(self):

        while True:

            if self.queue.is_empty:

                try:
                    with async_timeout.timeout(timeout=20):
                        await self.wait_queue_add.wait()
                except asyncio.TimeoutError:
                    await self.send(message='No tracks have been added to the queue for 20 seconds, I am leaving the voice channel.')
                    await self.destroy()
                    self.task.cancel()
                    break

            self.wait_queue_add.clear()

            track = await self.queue.get()
            if track.source == 'spotify':
                try:
                    search = await self.node.search(query=f'{track.author} - {track.title}', ctx=track.ctx)
                except exceptions.VoiceError as error:
                    await self.send(message=f'{error}')
                    continue
                else:
                    track = search.tracks[0]

            await self.play(track=track)

            try:
                with async_timeout.timeout(timeout=10):
                    await self.wait_track_start.wait()
            except asyncio.TimeoutError:
                await self.send(message='Something went wrong while playing a track, maybe try playing it again, or join the support server for more information.')
                continue

            self.wait_track_start.clear()

            await self.wait_track_end.wait()
            self.wait_track_end.clear()

            self.current = None
