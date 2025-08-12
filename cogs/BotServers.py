from discord import app_commands
from discord.ext import commands
import discord
import os

class BotServers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="botservers",
                             description="List all servers where this bot is present (Bot owner only)")
    @app_commands.describe(show_ids="Whether to show server IDs (true/false)")
    async def botservers(self, ctx: commands.Context, show_ids: bool = False):


        YOUR_USER_ID = os.getenv("AUTHORIZED_USER_IDS")

        if ctx.author.id != YOUR_USER_ID:
            embed = discord.Embed(
                title="❌ Access Denied",
                description="You don't have permission to use this command.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed, ephemeral=True)

        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)

        embed = discord.Embed(
            title=f"🖥️ Servers where this bot is present ({len(guilds)})",
            color=discord.Color.blue()
        )

        entries = []
        for index, guild in enumerate(guilds, start=1):
            owner = await self.bot.fetch_user(guild.owner_id)
            entry = (
                f"{index}. **{guild.name}**\n"
                f"👑 Owner: {owner.display_name}\n"
                f"👥 Members: {guild.member_count}"
            )
            if show_ids:
                entry += f"\n🆔 ID: {guild.id}"
            entries.append(entry)

        # Split into chunks of 5 servers per field to avoid hitting embed field limits
        for i in range(0, len(entries), 5):
            chunk = entries[i:i+5]
            embed.add_field(
                name="\u200b",
                value="\n\n".join(chunk),
                inline=False
            )

        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(BotServers(bot))