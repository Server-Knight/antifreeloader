from __future__ import annotations

from typing import Iterable

import discord
from redbot.vendored.discord.ext import menus


class ConfirmMenu(menus.Menu):
    def __init__(self, freeloaders):
        super().__init__(timeout=180.0, delete_message_after=False)
        self.freeloaders = freeloaders
        self.result = False

    async def send_initial_message(self, ctx, channel):
        embed = discord.Embed(
            title="📝Freeloader Report!",
            description=f"The following users are most likely freeloaders:\n```{self.freeloaders}```\nReact to 🔨 for those freeloaders to be banned!",
            color=0xFFFFFF,
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/788199676226699344.png?v=1")
        return await channel.send(embed=embed)

    @menus.button("🔨")
    async def do_ban(self, payload):
        self.result = True
        self.stop()

    @menus.button("❌")
    async def dont_ban(self, payload):
        self.result = False
        self.stop()

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.result


class FormatBanMenu(menus.ListPageSource):
    def __init__(self, methods: Iterable[str]):
        super().__init__(methods, per_page=1)

    async def format_page(self, menu: BanMenu, entry) -> discord.Embed:
        embed = discord.Embed(
            title="📝Freeloader Report!",
            description=f"The following users are most likely freeloaders:\n```{entry}```\nReact to 🔨 for those freeloaders to be banned!",
            color=0xFFFFFF,
        )
        embed.set_footer(text=f"Page {menu.current_page + 1} of {self.get_max_pages()}")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/788199676226699344.png?v=1")
        return embed


class BanMenu(menus.MenuPages, inherit_buttons=False):
    def __init__(
        self,
        freeloaders: list,
        source: menus.PageSource,
        **kwargs,
    ):
        super().__init__(source, **kwargs)
        self.freeloaders = freeloaders

    def reaction_check(self, payload):
        if payload.message_id != self.message.id:
            return False
        if payload.user_id not in (*self.bot.owner_ids, self._author_id):
            return False

        return payload.emoji in self.buttons

    def _skip_single_arrows(self):
        max_pages = self._source.get_max_pages()
        if max_pages is None:
            return True
        return max_pages == 1

    @menus.button(
        "◀️",
        position=menus.First(0),
        skip_if=_skip_single_arrows,
    )
    async def prev(self, payload: discord.RawReactionActionEvent):
        await self.show_checked_page(self.current_page - 1)

    @menus.button("🔨", position=menus.Position(0))
    async def ban(self, payload: discord.RawReactionActionEvent):
        return True

    @menus.button("❌", position=menus.Position(1))
    async def stop_pages_default(self, payload: discord.RawReactionActionEvent) -> None:
        self.stop()

    @menus.button(
        "▶️",
        position=menus.Last(0),
        skip_if=_skip_single_arrows,
    )
    async def next(self, payload: discord.RawReactionActionEvent):
        await self.show_checked_page(self.current_page + 1)
