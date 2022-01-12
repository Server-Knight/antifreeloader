from redbot.core import commands


class Bantype(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str):
        cog = ctx.cog
        bantype = await cog.config.guild(ctx.guild).bantype()

        if arg.lower() not in ["ban", "tempban"]:
            raise commands.BadArgument(
                f"`{arg}` is not a valid ban type. The only valid ban types are `ban` and `tempban`."
            )
        elif arg.lower() == "ban":
            if bantype:
                return 0

            await ctx.message.reply("The ban type is already set to `ban`.")
            return 2
        else:
            if not bantype:
                return 1

            await ctx.message.reply("The ban type is already set to `tempban`.")
            return 2


class BanLength(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str):
        if not arg.isnumeric():
            raise commands.BadArgument("Please enter a valid length.")
        elif int(arg) < 1:
            raise commands.BadArgument("You cannot set the length to anything less than 1 day.")
        return int(arg)
