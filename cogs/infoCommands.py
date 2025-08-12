# Modified infoCommands.py with region detection from UID
import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime, timedelta
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
        self.config_data = self.load_config()
        self.cooldowns = {}
        self.regions = {
            "1": "EN",  # Europe/International
            "2": "VN",  # Vietnam
            "3": "TH",  # Thailand
            "4": "ID",  # Indonesia
            "5": "RU",  # Russia
            "6": "PT",  # Portugal/Brazil
            "7": "DE",  # Germany
            "8": "FR",  # France
            "9": "ES",  # Spain
            "10": "TR",  # Turkey
            "11": "PK",  # Pakistan
            "12": "IN",  # India
            "13": "BD",  # Bangladesh
            "14": "SA",  # Saudi Arabia
            "15": "AE",  # UAE
            "16": "MY",  # Malaysia
            "17": "PH",  # Philippines
            "18": "BR",  # Brazil
            "19": "MX",  # Mexico
            "20": "US",  # USA
        }
        self.ranks = ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Heroic"]
        self.titles = ["Rookie", "Veteran", "Elite", "Master", "Grandmaster", "Legend"]
        self.avatars = [f"1020000{str(i).zfill(2)}" for i in range(1, 30)]
        self.banners = [f"90103{str(i).zfill(3)}" for i in range(1, 50)]
        self.pins = [f"91003{str(i).zfill(3)}" for i in range(1, 50)]
        self.skills = [
            204000921, 211000168, 203000348, 203001297, 
            205000545, 211001236, 214037004, 214037005, 
            214037006, 214037007, 214037008
        ]

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
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return default_config
        return default_config

    def save_config(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config_data, f, indent=4, ensure_ascii=False)

    async def is_channel_allowed(self, ctx):
        guild_id = str(ctx.guild.id)
        allowed_channels = self.config_data["servers"].get(guild_id, {}).get("info_channels", [])
        return True if not allowed_channels else str(ctx.channel.id) in allowed_channels

    def detect_region_from_uid(self, uid):
        """Detect region based on UID pattern"""
        # First digit method (simplified version)
        if len(uid) >= 1:
            first_digit = uid[0]
            return self.regions.get(first_digit, "PK")  # Default to PK if not found
        
        return "PK"  # Default to Pakistan if UID is empty

    def generate_mock_data(self, uid):
        """Generate mock player data based on UID"""
        region = self.detect_region_from_uid(uid)
        level = random.randint(1, 70)
        exp = random.randint(1000, 500000)
        likes = random.randint(0, 5000)
        honor_score = random.choice([100, 200, 300, 400, 500])
        ob_version = f"OB{random.randint(30, 44)}"
        
        # Generate random dates
        created_at = datetime.now() - timedelta(days=random.randint(100, 1000))
        last_login = datetime.now() - timedelta(days=random.randint(0, 30))
        
        # Random guild data (50% chance to have a guild)
        has_guild = random.choice([True, False])
        guild_data = {}
        if has_guild:
            guild_data = {
                "clanName": random.choice(["NOOBRIII", "PROSQUAD", "LEGENDS", "GHOST", "PHANTOM"]),
                "clanId": random.randint(1000000000, 2000000000),
                "clanLevel": random.randint(1, 10),
                "memberNum": random.randint(1, 35),
                "capacity": 35,
                "captain": {
                    "nickname": random.choice(["Rehman3755N", "ProPlayer", "TopG", "FFKing", "NoobSlayer"]),
                    "accountId": random.randint(1000000000, 3000000000),
                    "level": random.randint(1, 70),
                    "liked": random.randint(0, 5000),
                    "lastLoginAt": (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d %H:%M:%S")
                }
            }
        
        return {
            "basicInfo": {
                "nickname": f"Player{random.randint(100, 999)}",
                "level": level,
                "exp": exp,
                "region": region,
                "liked": likes,
                "honorScore": honor_score,
                "createAt": created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "lastLoginAt": last_login.strftime("%Y-%m-%d %H:%M:%S"),
                "signature": random.choice(["**", "Pro Player", "Noob", "Add me!", "Let's play!"]),
                "avatarId": random.choice(self.avatars),
                "bannerId": random.choice(self.banners),
                "pinId": random.choice(self.pins),
                "equippedSkills": random.sample(self.skills, 7),
                "currentBPBadges": "Not found",
                "brRank": f"{random.choice(self.ranks)} {random.randint(1000, 5000)}",
                "csRank": random.choice(["Not found", f"{random.choice(self.ranks)} ?"]),
                "mostRecentOB": ob_version,
                "title": random.choice(self.titles)
            },
            "clanBasicInfo": guild_data if has_guild else {},
            "petInfo": {
                "hasPet": random.choice([True, False]),
                "petName": random.choice(["Rockie", "Dreki", "Panda", "Fox", "Not Found"]),
                "petExp": random.randint(1000, 10000),
                "petLevel": random.randint(1, 10)
            }
        }

    @commands.hybrid_command(name="info", description="Displays information about a Free Fire player")
    @app_commands.describe(uid="Free Fire player ID")
    async def player_info(self, ctx: commands.Context, uid: str):
        if not uid.isdigit() or len(uid) < 6:
            return await ctx.reply("⚠️ Invalid UID! It must:\n- Be only numbers\n- Have at least 6 digits", mention_author=False)

        if not await self.is_channel_allowed(ctx):
            return await ctx.send("❌ This command is not allowed in this channel.", ephemeral=True)

        # Check cooldown
        cooldown = self.config_data["global_settings"]["default_cooldown"]
        guild_id = str(ctx.guild.id)
        if guild_id in self.config_data["servers"]:
            cooldown = self.config_data["servers"][guild_id]["config"].get("cooldown", cooldown)

        if ctx.author.id in self.cooldowns:
            last_used = self.cooldowns[ctx.author.id]
            if (datetime.now() - last_used).seconds < cooldown:
                remaining = cooldown - (datetime.now() - last_used).seconds
                return await ctx.send(f"⏳ Please wait {remaining}s before using this command again", ephemeral=True)

        self.cooldowns[ctx.author.id] = datetime.now()

        try:
            async with ctx.typing():
                # Generate mock data with region detection
                mock_data = self.generate_mock_data(uid)
                player = mock_data["basicInfo"]
                clan = mock_data.get("clanBasicInfo", {})
                pet = mock_data.get("petInfo", {})
                captain = clan.get("captain", {}) if clan else {}

            embed = discord.Embed(
                title="📜 Player Information",
                color=discord.Color.blurple(),
                timestamp=datetime.now()
            )
            embed.set_thumbnail(url=ctx.author.display_avatar.url)

            # Basic Info
            basic_info = [
                f"**Nickname:** {player.get('nickname', 'Unknown')}",
                f"**UID:** `{uid}`",
                f"**Level:** {player.get('level', '?')} (Exp: {player.get('exp', '?')})",
                f"**Region:** {player.get('region', 'Unknown')} (auto-detected)",
                f"**Likes:** {player.get('liked', '?')}",
                f"**Honor Score:** {player.get('honorScore', '?')}",
                f"**Signature:** {player.get('signature', 'N/A')}",
                f"**Created:** {player.get('createAt', 'Unknown')}",
                f"**Last Login:** {player.get('lastLoginAt', 'Unknown')}"
            ]
            embed.add_field(name="┌ ACCOUNT BASIC INFO", value="\n".join(basic_info), inline=False)

            # Activity Info
            activity_info = [
                f"**Most Recent OB:** {player.get('mostRecentOB', '?')}",
                f"**Current BP Badges:** {player.get('currentBPBadges', '?')}",
                f"**BR Rank:** {player.get('brRank', '?')}",
                f"**CS Rank:** {player.get('csRank', '?')}",
                f"**Title:** {player.get('title', '?')}"
            ]
            embed.add_field(name="├─ ACCOUNT ACTIVITY", value="\n".join(activity_info), inline=False)

            # Overview
            overview_info = [
                f"**Avatar ID:** {player.get('avatarId', '?')}",
                f"**Banner ID:** {player.get('bannerId', '?')}",
                f"**Pin ID:** {player.get('pinId', '?')}",
                f"**Equipped Skills:** {player.get('equippedSkills', [])}"
            ]
            embed.add_field(name="├─ ACCOUNT OVERVIEW", value="\n".join(overview_info), inline=False)

            # Pet Info
            if pet.get("hasPet", False):
                pet_info = [
                    f"**Equipped?:** Yes",
                    f"**Pet Name:** {pet.get('petName', '?')}",
                    f"**Pet Exp:** {pet.get('petExp', '?')}",
                    f"**Pet Level:** {pet.get('petLevel', '?')}"
                ]
                embed.add_field(name="├─ PET DETAILS", value="\n".join(pet_info), inline=False)

            # Guild Info
            if clan:
                guild_info = [
                    f"**Guild Name:** {clan.get('clanName', '?')}",
                    f"**Guild ID:** `{clan.get('clanId', '?')}`",
                    f"**Guild Level:** {clan.get('clanLevel', '?')}",
                    f"**Live Members:** {clan.get('memberNum', '?')}/{clan.get('capacity', '?')}"
                ]
                if captain:
                    guild_info.extend([
                        "**Leader Info:**",
                        f"├─ **Leader Name:** {captain.get('nickname', '?')}",
                        f"├─ **Leader UID:** `{captain.get('accountId', '?')}`",
                        f"├─ **Leader Level:** {captain.get('level', '?')}",
                        f"├─ **Last Login:** {captain.get('lastLoginAt', '?')}"
                    ])
                embed.add_field(name="┌ GUILD INFO", value="\n".join(guild_info), inline=False)

            embed.set_footer(text="Developed by: nopethug | Region detected from UID")
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
        finally:
            gc.collect()

async def setup(bot):
    await bot.add_cog(InfoCommands(bot))