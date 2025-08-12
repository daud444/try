import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from datetime import datetime
import json
import os
import asyncio
import gc

CONFIG_FILE = "check_channels.json"


class CheckCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://api-check-ban.up.railway.app/check_ban/"
        self.session = aiohttp.ClientSession()
        self.config = self.load_config()
        self.cooldowns = {}

    def load_config(self):
        default_config = {
            "servers": {},
            "global_settings": {
                "default_all_channels": False,
                "default_cooldown": 30
            }
        }

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    if "servers" not in config:
                        return {
                            "servers": {k: {"check_channels": v, "config": {}} for k, v in config.items()},
                            "global_settings": default_config["global_settings"]
                        }
                    return config
            except json.JSONDecodeError:
                return default_config
        return default_config

    def save_config(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    async def is_channel_allowed(self, ctx):
        guild_id = str(ctx.guild.id)
        if self.config["global_settings"]["default_all_channels"]:
            return True

        if guild_id not in self.config["servers"]:
            return True

        allowed_channels = self.config["servers"][guild_id].get("check_channels", [])
        return str(ctx.channel.id) in allowed_channels if allowed_channels else True

    async def check_ban(self, user_id):
        try:
            async with self.session.get(f"{self.api_url}{user_id}") as response:
                if response.status == 200:
                    resp = await response.json()
                    data = resp["data"]
                    return {
                        "is_banned": data.get("is_banned", 0),
                        "nickname": data.get("nickname", ""),
                        "period": data.get("period", 0),
                        "region": data.get('region', "N/A")
                    }
                return None
        except Exception:
            return None

    @commands.hybrid_command(name="setcheckchannel", description="Allow a channel for !check commands")
    @commands.has_permissions(administrator=True)
    async def set_check_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        guild_id = str(ctx.guild.id)

        if guild_id not in self.config["servers"]:
            self.config["servers"][guild_id] = {
                "check_channels": [],
                "config": {
                    "cooldown": self.config["global_settings"]["default_cooldown"]
                }
            }

        if str(channel.id) not in self.config["servers"][guild_id]["check_channels"]:
            self.config["servers"][guild_id]["check_channels"].append(str(channel.id))
            self.save_config()
            await ctx.send(f"✅ {channel.mention} is now allowed for `!check` commands")
        else:
            await ctx.send(f"ℹ️ {channel.mention} is already allowed for `!check` commands")

    @commands.hybrid_command(name="removecheckchannel", description="Remove a channel from !check commands")
    @commands.has_permissions(administrator=True)
    async def remove_check_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        guild_id = str(ctx.guild.id)

        if guild_id in self.config["servers"]:
            if str(channel.id) in self.config["servers"][guild_id]["check_channels"]:
                self.config["servers"][guild_id]["check_channels"].remove(str(channel.id))
                self.save_config()
                await ctx.send(f"✅ {channel.mention} has been removed from allowed channels")
            else:
                await ctx.send(f"❌ {channel.mention} is not in the list of allowed channels")
        else:
            await ctx.send("ℹ️ This server has no saved configuration")

    @commands.hybrid_command(name="setcheckcooldown", description="Set the cooldown for check commands")
    @commands.has_permissions(administrator=True)
    async def set_check_cooldown(self, ctx: commands.Context, seconds: int):
        guild_id = str(ctx.guild.id)

        if guild_id not in self.config["servers"]:
            self.config["servers"][guild_id] = {
                "check_channels": [],
                "config": {}
            }

        self.config["servers"][guild_id]["config"]["cooldown"] = seconds
        self.save_config()
        await ctx.send(f"✅ Cooldown set to {seconds} seconds for this server")

    @commands.hybrid_command(name="checkschannels", description="List allowed channels for !check")
    async def list_check_channels(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)

        if guild_id in self.config["servers"] and self.config["servers"][guild_id]["check_channels"]:
            channels = []
            for channel_id in self.config["servers"][guild_id]["check_channels"]:
                channel = ctx.guild.get_channel(int(channel_id))
                channels.append(f"• {channel.mention if channel else f'ID: {channel_id}'}")

            embed = discord.Embed(
                title="Allowed channels for !check",
                description="\n".join(channels),
                color=discord.Color.blue()
            )
            cooldown = self.config["servers"][guild_id]["config"].get("cooldown", self.config["global_settings"][
                "default_cooldown"])
            embed.set_footer(text=f"Current cooldown: {cooldown} seconds")
        else:
            embed = discord.Embed(
                title="Allowed channels for !check",
                description="All channels are allowed (no restriction configured)",
                color=discord.Color.blue()
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="check", description="Check if a Free Fire account is banned")
    @app_commands.describe(uid="Free Fire player ID")
    async def check_ban_command(self, ctx: commands.Context, uid: str):
        try:
            if ctx.interaction:
                # Pour les slash commands, on doit répondre différemment
                await ctx.interaction.response.defer()

            # Afficher que le bot est en train d'écrire
            async with ctx.typing():
                await asyncio.sleep(1)  # Petit délai pour que le message "typing" soit visible

            if not await self.is_channel_allowed(ctx):
                return await ctx.send("❌ This command is not allowed in this channel.", ephemeral=True)

            guild_id = str(ctx.guild.id)
            cooldown = self.config["global_settings"]["default_cooldown"]

            if guild_id in self.config["servers"]:
                cooldown = self.config["servers"][guild_id]["config"].get("cooldown", cooldown)

            if not uid.isdigit() or len(uid) < 6:
                await ctx.reply(
                    "⚠️ Invalid UID! It must:\n"
                    "- Contain only numbers\n"
                    "- Be at least 6 characters long",
                    mention_author=False
                )
                return

            if ctx.author.id in self.cooldowns:
                last_used = self.cooldowns[ctx.author.id]
                if (datetime.now() - last_used).seconds < cooldown:
                    remaining = cooldown - (datetime.now() - last_used).seconds
                    return await ctx.send(f"⏳ Please wait {remaining} seconds before using this command again",
                                          ephemeral=True)

            self.cooldowns[ctx.author.id] = datetime.now()

            try:
                # Afficher à nouveau que le bot travaille pendant la requête API
                async with ctx.typing():
                    ban_status = await self.check_ban(uid)
            except Exception as e:
                await ctx.send(f"{ctx.author.mention} ⚠️ Error:\n```{str(e)}```")
                return

            if ban_status is None:
                return await self._send_api_error(ctx)

            is_banned = int(ban_status.get("is_banned", 0))
            period = ban_status.get("period", "N/A")
            nickname = ban_status.get("nickname", "N/A")
            region = ban_status.get("region", "N/A")
            id_str = f"`{uid}`"

            if isinstance(period, int):
                period_str = f"more than {period} months"
            else:
                period_str = "unavailable"

            embed = discord.Embed(
                color=0xFF0000 if is_banned else 0x00FF00,
                timestamp=ctx.message.created_at
            )

            if is_banned:
                embed.title = "**▌ Banned Account 🛑 **"
                embed.description = (
                    f"**• Reason:** This account was confirmed for using cheats.\n"
                    f"**• Suspension duration:** {period_str}\n"
                    f"**• Nickname:** `{nickname}`\n"
                    f"**• Player ID:** `{id_str}`\n"
                    f"**• Region:** `{region}`"
                )
                embed.set_image(url="https://i.ibb.co/wFxTy8TZ/banned.gif")
            else:
                embed.title = "**▌ Clean Account ✅ **"
                embed.description = (
                    f"**• Status:** No sufficient evidence of cheat usage on this account.\n"
                    f"**• Nickname:** `{nickname}`\n"
                    f"**• Player ID:** `{id_str}`\n"
                    f"**• Region:** `{region}`"
                )
                embed.set_image(url="https://i.ibb.co/Kx1RYVKZ/notbanned.gif")

            embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_footer(text="📌 Garena Free Fire")
            await ctx.send(f"{ctx.author.mention}", embed=embed)

        except Exception as e:
            if ctx.interaction and not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(f"⚠️ Error: {str(e)}", ephemeral=True)
            else:
                await ctx.send(f"⚠️ Error: {str(e)}")
        finally:
            gc.collect()

    async def _send_api_error(self, ctx):
        await ctx.send(
            embed=discord.Embed(
                title="⚠️ Service Unavailable",
                description="The ban check API is not responding at the moment",
                color=0xF39C12
            ).add_field(
                name="Solution",
                value="Try again in a few minutes",
                inline=False
            )
        )

    def cog_unload(self):
        asyncio.create_task(self.session.close())


async def setup(bot):
    await bot.add_cog(CheckCommands(bot))