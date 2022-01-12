# AntiFreeloader cog

This is a cog for the [Red-Discord bot](https://github.com/Cog-Creators/Red-DiscordBot) bot framework. It's purpose is to catch freeloaders. These are people who join Discord servers (which are usually around the bot [Dank Memer](https://dankmemer.lol)) just to join heists. They would then leave after they received their heist payout.

The process that this cog uses to find freeloaders is pretty simple. First, a server staff or admin can specify the type of ban. The valid options are a temp ban or a ban. If they selected a temp ban, they choose how long the temp ban is. Then before a heist, they can run `[p]freeloader start`. This command will start the freeloader system. Then whenever someone joins the server while it is running, they will be recorded. If they say join heist before the freeloader process ends and leaves, they will be banned or temp banned.

This cog does use the BanManager cog which is private, so it would have to be updated to your need.

## Credits

Phenom4n4n - Many improvments<br>
Adam Turaj - General idea and almost all the code.
