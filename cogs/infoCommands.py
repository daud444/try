import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from datetime import datetime
import json
import os
import asyncio
import io
import uuid
import gc

CONFIG_FILE = "info_channels.json"


class InfoCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://info-api.up.railway.app/info"
        self.generate_url = "https://generate-outfits.onrender.com/generate-outfit"
        self.session = aiohttp.ClientSession()
        self.config_data = self.load_config()
        self.cooldowns = {}

        # self.subscription_api_url = ""
        # self.subscribed_servers = set()
        # self.bot.loop.create_task(self.fetch_subscribed_servers())
        # self.bot.loop.create_task(self.fetch_subscribed_servers_periodically())

    # async def fetch_subscribed_servers(self):
    #     try:
    #         async with self.session.get(self.subscription_api_url) as response:
    #             if response.status == 200:
    #                 data = await response.json()
    #                 self.subscribed_servers = set(data.get('subscribed_servers', []))
    #     except Exception as e:
    #         print(f"Error fetching subscribed servers: {e}")

    # async def fetch_subscribed_servers_periodically(self):
    #     while True:
    #         await self.fetch_subscribed_servers()
    #         await asyncio.sleep(300)

    # def is_server_subscribed(self, guild_id):
    #     return str(guild_id) in self.subscribed_servers

    # def check_request_limit(self, guild_id):
    #     try:
    #         return self.is_server_subscribed(guild_id) or not self.is_limit_reached(guild_id)
    #     except Exception as e:
    #         print(f"Error checking request limit: {e}")
    #         return False

    def load_config(self):
        default_config = {
            "servers": {},
            "global_settings": {
                "default_all_channels": False,
                "default_cooldown": 30,
                "default_daily_limit": 30
            }
        }

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    loaded_config = json.load(f)
                    loaded_config.setdefault("global_settings", {})
                    loaded_config["global_settings"].setdefault("default_all_channels", False)
                    loaded_config["global_settings"].setdefault("default_cooldown", 30)
                    loaded_config["global_settings"].setdefault("default_daily_limit", 30)
                    loaded_config.setdefault("servers", {})
                    return loaded_config
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}")
                return default_config
        return default_config

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving config: {e}")

    # def check_and_reset_daily_limit(self, guild_id):
    #     try:
    #         if self.is_server_subscribed(guild_id):
    #             return

    #         today = datetime.utcnow().date()
    #         guild_id_str = str(guild_id)

    #         # Initialize server data structure if not exists
    #         if guild_id_str not in self.config_data["servers"]:
    #             self.config_data["servers"][guild_id_str] = {
    #                 "info_channels": [],
    #                 "config": {},
    #                 "usage": {
    #                     "count": 0,
    #                     "last_reset": today.isoformat()
    #                 }
    #             }

        #     server = self.config_data["servers"][guild_id_str]
        #     if "usage" not in server:
        #         server["usage"] = {"count": 0, "last_reset": today.isoformat()}

        #     usage = server["usage"]
        #     last_reset = datetime.fromisoformat(usage.get("last_reset", today.isoformat())).date()

        #     if last_reset < today:
        #         usage["count"] = 0
        #         usage["last_reset"] = today.isoformat()
        #         self.save_config()
        # except Exception as e:
        #     print(f"Error in check_and_reset_daily_limit: {e}")

    # def is_limit_reached(self, guild_id):
    #     try:
    #         self.check_and_reset_daily_limit(guild_id)
    #         guild_id_str = str(guild_id)

    #         if guild_id_str not in self.config_data["servers"]:
    #             return False

    #         server_config = self.config_data["servers"][guild_id_str]
    #         usage = server_config.get("usage", {})
    #         count = usage.get("count", 0)
    #         max_requests = server_config.get("config", {}).get(
    #             "daily_limit", self.config_data["global_settings"]["default_daily_limit"]
    #         )
    #         return count >= max_requests
    #     except Exception as e:
    #         print(f"Error in is_limit_reached: {e}")
    #         return False

    # def increment_usage(self, guild_id):
    #     try:
    #         guild_id_str = str(guild_id)
    #         if guild_id_str not in self.config_data["servers"]:
    #             self.config_data["servers"][guild_id_str] = {
    #                 "info_channels": [],
    #                 "config": {},
    #                 "usage": {"count": 0, "last_reset": datetime.utcnow().date().isoformat()}
    #             }

    #         self.config_data["servers"][guild_id_str]["usage"]["count"] += 1
    #         self.save_config()
    #     except Exception as e:
    #         print(f"Error incrementing usage: {e}")

    async def is_channel_allowed(self, ctx):
        try:
            guild_id = str(ctx.guild.id)
            allowed_channels = self.config_data["servers"].get(guild_id, {}).get("info_channels", [])

            # Autoriser tous les salons si aucun salon n'a été configuré pour ce serveur
            if not allowed_channels:
                return True

            # Sinon, vérifier si le salon actuel est dans la liste autorisée
            return str(ctx.channel.id) in allowed_channels
        except Exception as e:
            print(f"Error checking channel permission: {e}")
            return False

    @commands.hybrid_command(name="setinfochannel", description="Allow a channel for !info commands")
    @commands.has_permissions(administrator=True)
    async def set_info_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        guild_id = str(ctx.guild.id)
        self.config_data["servers"].setdefault(guild_id, {"info_channels": [], "config": {}})
        if str(channel.id) not in self.config_data["servers"][guild_id]["info_channels"]:
            self.config_data["servers"][guild_id]["info_channels"].append(str(channel.id))
            self.save_config()
            await ctx.send(f"✅ {channel.mention} is now allowed for `!info` commands")
        else:
            await ctx.send(f"ℹ️ {channel.mention} is already allowed for `!info` commands")

    @commands.hybrid_command(name="removeinfochannel", description="Remove a channel from !info commands")
    @commands.has_permissions(administrator=True)
    async def remove_info_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        guild_id = str(ctx.guild.id)
        if guild_id in self.config_data["servers"]:
            if str(channel.id) in self.config_data["servers"][guild_id]["info_channels"]:
                self.config_data["servers"][guild_id]["info_channels"].remove(str(channel.id))
                self.save_config()
                await ctx.send(f"✅ {channel.mention} has been removed from allowed channels")
            else:
                await ctx.send(f"❌ {channel.mention} is not in the list of allowed channels")
        else:
            await ctx.send("ℹ️ This server has no saved configuration")

    @commands.hybrid_command(name="infochannels", description="List allowed channels")
    async def list_info_channels(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)

        if guild_id in self.config_data["servers"] and self.config_data["servers"][guild_id]["info_channels"]:
            channels = []
            for channel_id in self.config_data["servers"][guild_id]["info_channels"]:
                channel = ctx.guild.get_channel(int(channel_id))
                channels.append(f"• {channel.mention if channel else f'ID: {channel_id}'}")

            embed = discord.Embed(
                title="Allowed channels for !info",
                description="\n".join(channels),
                color=discord.Color.blue()
            )
            cooldown = self.config_data["servers"][guild_id]["config"].get("cooldown", self.config_data["global_settings"]["default_cooldown"])
            embed.set_footer(text=f"Current cooldown: {cooldown} seconds")
        else:
            embed = discord.Embed(
                title="Allowed channels for !info",
                description="All channels are allowed (no restriction configured)",
                color=discord.Color.blue()
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="info", description="Displays information about a Free Fire player")
    @app_commands.describe(uid="Free Fire player ID")
    async def player_info(self, ctx: commands.Context, uid: str):
        guild_id = str(ctx.guild.id)

        if not uid.isdigit() or len(uid) < 6:
            return await ctx.reply("⚠️ Invalid UID! It must:\n- Be only numbers\n- Have at least 6 digits", mention_author=False)

        if not await self.is_channel_allowed(ctx):
            return await ctx.send("❌ This command is not allowed in this channel.", ephemeral=True)

        # if not self.check_request_limit(guild_id):
        #     daily_limit = self.config_data["servers"].get(guild_id, {}).get("config", {}).get(
        #         "daily_limit", self.config_data["global_settings"].get("default_daily_limit", 30))
        #     return await ctx.send(f"🚫 This server has reached its daily usage limit of /info ({daily_limit} commands/day). Contact the developer for unlimited access.")

        cooldown = self.config_data["global_settings"]["default_cooldown"]
        if guild_id in self.config_data["servers"]:
            cooldown = self.config_data["servers"][guild_id]["config"].get("cooldown", cooldown)

        if ctx.author.id in self.cooldowns:
            last_used = self.cooldowns[ctx.author.id]
            if (datetime.now() - last_used).seconds < cooldown:
                remaining = cooldown - (datetime.now() - last_used).seconds
                return await ctx.send(f"⏳ Please wait {remaining}s before using this command again", ephemeral=True)

        self.cooldowns[ctx.author.id] = datetime.now()
        # self.increment_usage(guild_id)

        try:
            async with ctx.typing():
                async with self.session.get(f"{self.api_url}?id={uid}") as response:
                    if response.status == 404:
                        return await self._send_player_not_found(ctx, uid)
                    if response.status != 200:
                        return await self._send_api_error(ctx)
                    data = await response.json()

                player = data.get('data', {}).get('basicInfo', {})
                clan = data.get('data', {}).get('clanBasicInfo', {})
                captain = data.get('data', {}).get('captainBasicInfo', {})
                socialInfo = data.get('data', {}).get('socialInfo', {})
                region = player.get('region', 'Unknown')

            embed = discord.Embed(
                title="📜 Player Information",
                color=discord.Color.blurple(),
                timestamp=datetime.now()
            )
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.add_field(name="👤 ACCOUNT", value="\n".join([
                f"**Nickname:** {player.get('nickname', 'Unknown')}",
                f"**UID:** `{uid}`",
                f"**Level:** {player.get('level', '?')}",
                f"**Region:** {region}",
                f"**Likes:** {player.get('liked', '?')}",
                f"**Last Login:** {player.get('lastLoginAt', 'Unknown')}",
                f"**Created:** {player.get('createAt', 'Unknown')}",
                f"**Signature:** {socialInfo.get('signature', 'N/A') or 'N/A'}"
            ]), inline=False)

            if clan:
                embed.add_field(name="🛡️ GUILD", value="\n".join([
                    f"**Guild Name:** {clan.get('clanName', 'No guild')}",
                    f"**Guild ID:** `{clan.get('clanId', '?')}`",
                    f"**Guild Level:** {clan.get('clanLevel', '?')}",
                    f"**Members:** {clan.get('memberNum', '?')}/{clan.get('capacity', '?')}"
                ]), inline=False)

            if captain:
                embed.add_field(name="👑 GUILD LEADER", value="\n".join([
                    f"**Leader Nickname:** {captain.get('nickname', 'Unknown')}",
                    f"**UID:** `{captain.get('accountId', '?')}`",
                    f"**Level:** {captain.get('level', '?')}",
                    f"**Likes:** {captain.get('liked', '?')}",
                    f"**Last Login:** {captain.get('lastLoginAt', 'Unknown')}"
                ]), inline=False)

            # usage = self.config_data["servers"].get(guild_id, {}).get("usage", {})
            # count = usage.get("count", 0)
            # max_requests = self.config_data["servers"].get(guild_id, {}).get("config", {}).get(
            #     "daily_limit", self.config_data["global_settings"].get("default_daily_limit", 30)
            # )
            # remaining = max_requests - count

            # if self.is_server_subscribed(guild_id):
            #     embed.add_field(name="\u200b", value="✅ This server is subscribed - No daily limits", inline=False)
            # else:
            #     embed.add_field(name="\u200b", value=f"• Not subscribed - `{remaining}/{max_requests}` requests left today", inline=False)

            embed.set_footer(text="Developed by: nopethug", icon_url="https://i.imgur.com/PtAn3zf.gif")

            await ctx.send(embed=embed)

            if region and uid:
                try:
                    async with self.session.get(f"{self.generate_url}?uid={uid}&region={region}") as img_response:
                        if img_response.status == 200:
                            image_generated = await img_response.json()
                            image_url = image_generated.get('image_url')
                            if image_url:
                                async with self.session.get(image_url) as img_file:
                                    if img_file.status == 200:
                                        with io.BytesIO(await img_file.read()) as image_buffer:
                                            file = discord.File(image_buffer, filename=f"outfit_{uuid.uuid4().hex[:8]}.png")
                                            await ctx.send(file=file)
                except Exception:
                    print("Image outfit fetch failed")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
        finally:
            gc.collect()

    @commands.hybrid_command(name="infolimit", description="Check remaining daily usage")
    async def get_daily_usage(self, ctx):
        guild_id = str(ctx.guild.id)
        if self.is_server_subscribed(guild_id):
            return await ctx.send("✅ This server is subscribed - No daily limits")

        server_config = self.config_data["servers"].setdefault(guild_id, {})
        usage = server_config.setdefault("usage", {"count": 0, "last_reset": datetime.utcnow().date().isoformat()})
        count = usage.get("count", 0)
        max_requests = server_config.get("config", {}).get(
            "daily_limit", self.config_data["global_settings"]["default_daily_limit"]
        )
        await ctx.send(f"📊 Remaining usage today (!info): {max_requests - count}/{max_requests}")

    async def cog_unload(self):
        await self.session.close()

    async def _send_player_not_found(self, ctx, uid):
        await ctx.send(embed=discord.Embed(
            title="❌ Player Not Found",
            description=f"The UID `{uid}` does not exist or is not accessible",
            color=0xE74C3C
        ))

    async def _send_api_error(self, ctx):
        await ctx.send(embed=discord.Embed(
            title="⚠️ API Error",
            description="The Free Fire API is not responding. Try again later.",
            color=0xF39C12
        ))

    # @commands.Cog.listener()
    # async def on_command_error(self, ctx, error):
    #     if isinstance(error, commands.MissingPermissions):
    #         await ctx.send("❌ You need to be an administrator to use this command.")
    #     elif isinstance(error, commands.MissingRequiredArgument):
    #         await ctx.send("⚠️ Missing required argument.")
    #     elif isinstance(error, commands.CommandNotFound):
    #         return
    #     else:
    #         print(f"Unhandled error: {error}")
    #         await ctx.send("⚠️ An unexpected error occurred. [1214]")


async def setup(bot):
    await bot.add_cog(InfoCommands(bot))