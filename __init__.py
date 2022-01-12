from redbot.core.bot import Red

from .antifreeloader import AntiFreeloader


async def setup(bot: Red) -> None:
    antifreeloader = AntiFreeloader(bot)
    await antifreeloader.initialize()
    bot.add_cog(antifreeloader)
