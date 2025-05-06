import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

def main():
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        raise ValueError("No Discord token found. Please set the DISCORD_TOKEN environment variable.")
    bot.run(token)

if __name__ == "__main__":
    main()