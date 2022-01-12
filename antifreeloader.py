from datetime import datetime, timedelta
from typing import Any, Dict
import asyncio

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import pagify

from .converters import BanLength, Bantype
from .menus import BanMenu, ConfirmMenu, FormatBanMenu

import logging

logger = logging.getLogger("red.serverknight.antifreeloader")


async def is_tempban(ctx: commands.Context) -> bool:
    cog = ctx.cog
    if not await cog.config.guild(ctx.guild).bantype():
        raise commands.UserFeedbackCheckFailure(
            "The ban type is not `tempban`. You can set it with `sk freeloader settings bantype tempban`."
        )
    return True


class AntiFreeloader(commands.Cog):
    """
    Prevents Freeloaders
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=38274572352,
            force_registration=True,
        )

        self.default_guild = {
            "joins": [],
            "joinedheist": [],
            "running": False,
            "bantype": 0,
            "banlength": 0,
            "tempbans": {},
        }

        self.config.register_guild(**self.default_guild)

        self.guild_cache: Dict[int, Dict[str, Any]] = {}

        self.tempban.start()

    def cog_unload(self):
        self.tempban.cancel()

    async def build_cache(self):
        self.guild_cache = await self.config.all_guilds()

    async def initialize(self):
        await self.build_cache()

    @commands.group()
    @commands.bot_has_permissions(ban_members=True)
    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def freeloader(self, ctx):
        """The cogs Anti-Freeloaders commands!"""

    @freeloader.command()
    async def start(self, ctx):
        """Starts the process to find those annoying freeloaders.
        This command will help prevent the freeloaders by temp-banning or banning them.
        To use this command please make sure you have set the length and ban type.
        """

        guild = ctx.guild
        if await self.config.guild(ctx.guild).running():
            return await ctx.message.reply(
                f"You already have a freeloader check going, you can stop it with `{ctx.prefix}freeloader stop`."
            )

        async with self.config.guild(guild).all() as f:
            f["joins"] = []
            f["joinedheist"] = []
            f["running"] = True

        await self.build_cache()

        embed = discord.Embed(
            title="Freeloading Check Activated 🚨",
            description=f"I will be watching for freeloaders until you run the command `{ctx.prefix}freeloader stop`. Then you can chose to **BAN** them",
            timestamp=datetime.utcnow(),
            color=0x00FF00,
        )
        embed.set_author(name=guild.name, icon_url=guild.icon_url)
        embed.set_footer(text="We are not liable for any false bans, use this at your own risk.")
        await ctx.send(embed=embed)

    @freeloader.command()
    async def stop(self, ctx):
        """Stops the freeloading check and bans the freeloaders
        This command will stop tracking joins and people saying `join heist`. It will then create you a report and will ban them.
        Note:
        *We are not liable with any false bans.*
        """

        guild = ctx.guild

        async with ctx.typing():
            dict = await self.config.guild(ctx.guild).all()

            if not dict["running"]:
                return await ctx.message.reply(
                    "You do not currently have a freeloader check running right now."
                )

            if not guild.chunked:
                await guild.chunk()

            report = ""
            freeloaders = []
            for user_id in dict["joinedheist"]:
                user = await self.bot.get_or_fetch_user(user_id)
                if user not in guild.members:
                    report += f"{user.name} ({user_id})\n"
                    freeloaders.append(user)

            self.freeloaders = set(freeloaders)

            await self.config.guild(guild).running.set(False)
            await self.build_cache()

            if len(report) > 1024:
                pages = list(pagify(report, page_length=1024))
                i = await BanMenu(
                    ctx,
                    source=FormatBanMenu(pages),
                    delete_message_after=False,
                    clear_reactions_after=True,
                    timeout=180,
                ).start(ctx, wait=False)

            elif not report:
                await ctx.send("There were no freeloaders reported today!")
                return
            else:
                i = await ConfirmMenu(report).prompt(ctx)

            if i:
                await self.banall(ctx)

    @freeloader.group()
    async def settings(self, ctx: commands.context):
        """Anti-Freeloaders settings commands"""

    @settings.command()
    async def view(self, ctx):
        """View the Anti-Freeloaders current settings
        View the Anti-Freeloaders current set commands. It will display the `ban type` and `ban length`
        """
        i = await self.config.guild(ctx.guild).all()

        bantype = i["bantype"]
        banlength = i["banlength"]

        if bantype:
            bantype = "Tempban"
            banlength = "{} days".format(banlength)
        else:
            bantype = "Ban"
            banlength = "N/A"

        embed = discord.Embed(
            description=f"**Ban type**\n{bantype}\n**Ban length**\n{banlength}",
            color=0x00FF00,
        )
        embed.set_author(name="Anti-Freeloader Settings", icon_url=ctx.guild.icon_url)
        await ctx.send(embed=embed)

    @settings.command()
    async def bantype(self, ctx, ban_type: Bantype):
        """Sets the type of ban.
        <ban_type> the type of ban. Must be either a `ban` or a `tempban`.
        """
        if ban_type == 0:
            await self.config.guild(ctx.guild).bantype.set(0)
            await ctx.send("The ban type has succesfully been updated to a `ban`.")
        elif ban_type == 1:
            async with self.config.guild(ctx.guild).all() as f:
                f["bantype"] = 1
                f["banlength"] = 7
            await ctx.send(
                "The ban type has succesfully been updated to a `tempban`.\nThe ban length is set to 7 days by default. To change that use `sk freeloader settings banlength <days>`."
            )

        await self.build_cache()

    @settings.command()
    @commands.check(is_tempban)
    async def banlength(self, ctx, ban_length: BanLength):
        """Sets the length of the tempban.
        <ban_length> the length of the ban. Must be entered as a valid integer and must be between 1 and 7 days.
        """

        await self.config.guild(ctx.guild).banlength.set(ban_length)
        await self.build_cache()

        await ctx.send(f"The tempban length has been set to {ban_length} days.")

    async def temp_ban_loop(self):
        try:
            await self.tempban()
        except Exception as err:
            logger.exception("There was an error in the temp ban loop", exc_info=err)

        await asyncio.sleep(60)

    async def tempban(self):
        for guild_id, guild_data in (self.guild_cache).items():
            guild = self.bot.get_guild(guild_id)

            if not guild:
                continue

            tempbans = guild_data["tempbans"]
            if not tempbans:
                continue

            if not guild.me.guild_permissions.ban_members:
                continue

            for member_id, end_time in tempbans.copy().items():
                member = await self.bot.get_or_fetch_user(member_id)
                if end_time and datetime.utcnow().timestamp() > end_time:
                    cog = self.bot.get_cog("BanManager")
                    await cog.unban(guild, member.id)
                    del tempbans[member_id]

            await self.config.guild(guild).tempbans.set(tempbans)

            await self.build_cache()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        all = self.guild_cache.get(member.guild.id)

        if not all:
            return

        if member.id not in all["joins"] and all["running"]:
            async with self.config.guild(member.guild).joins() as i:
                i.append(member.id)
            await self.build_cache()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return
        if message.author.bot:
            return
        if not message.content:
            return
        if "join heist" not in message.content.lower():
            return
        data = self.guild_cache.get(message.guild.id)

        if not data:
            return

        if message.author.id not in data["joins"] or message.author.id in data["joinedheist"]:
            return

        async with self.config.guild(message.guild).joinedheist() as i:
            i.append(message.author.id)
        await self.build_cache()

    async def banall(self, ctx: commands.context):
        bancog = ctx.bot.get_cog("BanManager")
        if not bancog:
            raise commands.CommandError(
                "The BanManager cog is not loaded. Please reach out to the developers to fix it."
            )

        guild = ctx.guild

        dict = self.guild_cache.get(ctx.guild.id)

        bantype = dict["bantype"]
        banlength = dict["banlength"]

        async with ctx.typing():

            for member in self.freeloaders:
                if not bantype:
                    try:
                        await member.send(
                            f"**Action:** You have been banned.\n**Reason:** Freeloading.\n**Server:** {guild.name}."
                        )
                    except discord.Forbidden:
                        pass
                    await bancog.maybe_ban(guild, member.id, "Freeloader banned.")
                    banmsg = "banned"
                else:
                    try:
                        await member.send(
                            f"**Action:** You have been tempbanned for {banlength} days.\n**Reason:** Freeloading.\n**Server:** {ctx.guild.name}."
                        )
                    except discord.Forbidden:
                        pass

                    ending = datetime.utcnow() + timedelta(days=banlength)
                    dict["tempbans"][member.id] = ending.timestamp()
                    await self.config.guild(guild).set(dict)
                    await bancog.maybe_ban(
                        guild,
                        member.id,
                        f"Freeloader tempbanned for {banlength} days.",
                    )
                    banmsg = f"tempbanned for {banlength} days"

            await ctx.send(
                f"**{len(self.freeloaders)}** freeloader{'s were' if len(self.freeloaders) > 1 else ' was'} {banmsg}."
            )
