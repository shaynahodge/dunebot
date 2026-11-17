A tiny Discord bot that watches normal chat for configured words or phrases. When one appears, it resets that word's timer and replies with the previous streak and record.

## Default behavior

The default tracked word is `DUNE`.

Example:

> 🚨 **DUNE MENTIONED**  
> **0 days since DUNE was last mentioned.**  
> Previous streak: **14 days**. Record: **27 days**.

Matching is case-insensitive and uses whole words/phrases, so `Dune`, `DUNE`, and `dune` all match.

## Setup

1. Create an application/bot in the Discord Developer Portal.
2. On the bot's settings page, enable **Message Content Intent**. The bot needs this because it watches ordinary messages for configured words.
3. Invite the bot to your server with permission to view channels, read message history, send messages, and reply in the channels you want monitored.
4. Install Python 3.8+ and the dependency:

   `python -m pip install -r requirements.txt`

5. Set your bot token as an environment variable named `DISCORD_TOKEN`. Never paste the token into the source code or commit it to Git.
6. Optional: set `TRACK_WORDS` to a comma-separated list such as `DUNE,Fourth Wing`.
7. Run:

   `python days_since_bot.py`

The bot saves timestamps in `counters.json` in the directory where it runs. Set `COUNTER_DATA_FILE` if you want a different location.

## Notes

- Each Discord server gets its own counters.
- Bots are ignored.
- Direct messages are ignored.
- A mention resets the counter immediately.
- The record shown is the longest completed streak observed by the bot.
- Keep `counters.json` on persistent storage if you deploy the bot to a hosting service.

## Good next upgrades

- `/counter add <word>` and `/counter remove <word>` admin commands
- `/counter status` to check the current streak without resetting it
- Limit each counter to selected channels
- Custom response text/emoji for each word
- SQLite storage instead of JSON

## Slash commands

- `/counter add word` - Admin only. Start tracking a word or phrase.
- `/counter remove word` - Admin only. Stop tracking it and delete its saved counter.
- `/counter reset word` - Admin only. Manually reset its clock to now.
- `/counter status word` - Anyone. Show the current streak and record.
- `/counter list` - Anyone. Show all tracked words and their current streaks.

The admin commands require Discord's **Manage Server** permission. Slash commands are globally synced when the bot starts; Discord may take a little time to make newly registered global commands visible everywhere.
