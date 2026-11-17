import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord import app_commands

TOKEN = os.environ["DISCORD_TOKEN"]
DATA_FILE = Path(os.environ.get("COUNTER_DATA_FILE", "counters.json"))
DEFAULT_WORDS = [w.strip() for w in os.environ.get("TRACK_WORDS", "DUNE").split(",") if w.strip()]

intents = discord.Intents.default()
intents.message_content = True


def load_data():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {}


def save_data(data):
    DATA_FILE.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def guild_counters(data, guild_id):
    gid = str(guild_id)
    if gid not in data:
        data[gid] = {}
    for word in DEFAULT_WORDS:
        key = word.casefold()
        data[gid].setdefault(key, {"display": word, "last_seen": None, "record_days": 0})
    return data[gid]


def contains_word(text, word):
    pattern = rf"(?<!\w){re.escape(word)}(?!\w)"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def days_since(iso_time):
    if not iso_time:
        return None
    return (datetime.now(timezone.utc) - datetime.fromisoformat(iso_time)).days


class DaysSinceClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced.")


client = DaysSinceClient()


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (id={client.user.id})")
    print(f"Default tracked words: {', '.join(DEFAULT_WORDS)}")


@client.event
async def on_message(message):
    if message.author.bot or message.guild is None:
        return

    data = load_data()
    counters = guild_counters(data, message.guild.id)
    now = datetime.now(timezone.utc)
    changed = False

    for counter in counters.values():
        word = counter["display"]
        if not contains_word(message.content, word):
            continue

        previous = counter.get("last_seen")
        if previous:
            days = (now - datetime.fromisoformat(previous)).days
            counter["record_days"] = max(counter.get("record_days", 0), days)
            response = (
                f"# 🪱 {word.upper()} MENTIONED 🪱\n"
                f"**0 days since {word} was last mentioned.**\n"
                f"Previous streak: **{days} day{'s' if days != 1 else ''}**. "
                f"\nRecord: **{counter['record_days']} day{'s' if counter['record_days'] != 1 else ''}**."
            )
        else:
            response = (
                f"# 🪱 {word.upper()} MENTIONED 🪱\n"
                f"**0 days since {word} was last mentioned.**\n"
                "The clock has begun."
            )

        counter["last_seen"] = now.isoformat()
        changed = True
        try:
            await message.reply(response, mention_author=False)
        except discord.Forbidden:
            channel = message.channel
            category = getattr(channel, "category", None)
            print(
                f"Missing permissions to reply in #{channel} (id={channel.id}, "
                f"category={category.name if category else 'none'}) "
                f"in server '{message.guild.name}' (id={message.guild.id})"
            )

    if changed:
        save_data(data)


counter_group = app_commands.Group(name="counter", description="Manage days-since word counters")
client.tree.add_command(counter_group)


@counter_group.command(name="add", description="Start tracking a word or phrase")
@app_commands.describe(word="Word or phrase to track")
@app_commands.checks.has_permissions(manage_guild=True)
async def counter_add(interaction: discord.Interaction, word: str):
    if interaction.guild_id is None:
        await interaction.response.send_message("This command only works in a server.", ephemeral=True)
        return
    word = word.strip()
    if not word or len(word) > 100:
        await interaction.response.send_message("Choose a word or phrase between 1 and 100 characters.", ephemeral=True)
        return
    data = load_data()
    counters = guild_counters(data, interaction.guild_id)
    key = word.casefold()
    if key in counters:
        await interaction.response.send_message(f"**{counters[key]['display']}** is already being tracked.", ephemeral=True)
        return
    counters[key] = {"display": word, "last_seen": None, "record_days": 0}
    save_data(data)
    await interaction.response.send_message(f"✅ Now tracking **{word}**. The first mention will start its clock.")


@counter_group.command(name="remove", description="Stop tracking a word or phrase")
@app_commands.describe(word="Tracked word or phrase to remove")
@app_commands.checks.has_permissions(manage_guild=True)
async def counter_remove(interaction: discord.Interaction, word: str):
    data = load_data()
    counters = guild_counters(data, interaction.guild_id)
    key = word.strip().casefold()
    if key not in counters:
        await interaction.response.send_message(f"I'm not tracking **{word}**.", ephemeral=True)
        return
    display = counters[key]["display"]
    del counters[key]
    save_data(data)
    await interaction.response.send_message(f"🗑️ Removed **{display}** from tracking.")


@counter_group.command(name="reset", description="Reset a tracked word's clock to now")
@app_commands.describe(word="Tracked word or phrase to reset")
@app_commands.checks.has_permissions(manage_guild=True)
async def counter_reset(interaction: discord.Interaction, word: str):
    data = load_data()
    counters = guild_counters(data, interaction.guild_id)
    key = word.strip().casefold()
    if key not in counters:
        await interaction.response.send_message(f"I'm not tracking **{word}**.", ephemeral=True)
        return
    counters[key]["last_seen"] = datetime.now(timezone.utc).isoformat()
    save_data(data)
    await interaction.response.send_message(f"🔄 **0 days since {counters[key]['display']} was last mentioned.**")


@counter_group.command(name="status", description="Check the current streak for a tracked word")
@app_commands.describe(word="Tracked word or phrase")
async def counter_status(interaction: discord.Interaction, word: str):
    data = load_data()
    counters = guild_counters(data, interaction.guild_id)
    key = word.strip().casefold()
    if key not in counters:
        await interaction.response.send_message(f"I'm not tracking **{word}**.", ephemeral=True)
        return
    counter = counters[key]
    days = days_since(counter.get("last_seen"))
    if days is None:
        text = f"⏳ **{counter['display']}** is being tracked, but it hasn't been mentioned yet."
    else:
        text = (
            f"⏱️ **{days} day{'s' if days != 1 else ''} since {counter['display']} was last mentioned.**\n"
            f"Record: **{counter.get('record_days', 0)} day{'s' if counter.get('record_days', 0) != 1 else ''}**."
        )
    await interaction.response.send_message(text)


@counter_group.command(name="list", description="List all tracked words and phrases")
async def counter_list(interaction: discord.Interaction):
    data = load_data()
    counters = guild_counters(data, interaction.guild_id)
    save_data(data)
    if not counters:
        await interaction.response.send_message("No words are currently being tracked.")
        return
    lines = []
    for counter in sorted(counters.values(), key=lambda x: x["display"].casefold()):
        days = days_since(counter.get("last_seen"))
        status = "not mentioned yet" if days is None else f"{days} day{'s' if days != 1 else ''}"
        lines.append(f"• **{counter['display']}**: {status} | record {counter.get('record_days', 0)} days")
    await interaction.response.send_message("📋 **Tracked counters**\n" + "\n".join(lines))


@client.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        message = "You need the **Manage Server** permission to use that command."
    else:
        print(f"Slash command error: {error}")
        message = "Something went wrong while running that command."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


client.run(TOKEN)
