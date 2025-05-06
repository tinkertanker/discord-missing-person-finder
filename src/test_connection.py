import os
import discord
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.members = True  # Enable members intent to fetch member list

async def test_connection():
    # Get configuration from environment variables
    token = os.getenv('DISCORD_TOKEN')
    guild_id = os.getenv('GUILD_ID')
    
    if not token:
        print("ERROR: No Discord token found. Please set the DISCORD_TOKEN in your .env file.")
        return
    
    if not guild_id:
        print("ERROR: No Guild ID found. Please set the GUILD_ID in your .env file.")
        return
    
    guild_id = int(guild_id)  # Convert string to integer
    
    # Create Discord client
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        try:
            print(f"Connected to Discord as {client.user} (ID: {client.user.id})")
            
            # Get the guild (server) object
            guild = client.get_guild(guild_id)
            
            if not guild:
                print(f"ERROR: Could not find guild with ID {guild_id}")
                await client.close()
                return
            
            print(f"Successfully connected to server: {guild.name} (ID: {guild.id})")
            
            # Fetch members
            members = guild.members
            print(f"Server has {len(members)} members")
            
            # Print 5 members as a sample
            print("\nSample of members:")
            for i, member in enumerate(members[:5]):
                print(f"{i+1}. {member.name}#{member.discriminator} (ID: {member.id})")
            
            # Close the client
            await client.close()
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            await client.close()
    
    try:
        await client.start(token)
    except discord.errors.LoginFailure:
        print("ERROR: Invalid Discord token. Please check your DISCORD_TOKEN in the .env file.")
    except Exception as e:
        print(f"ERROR: Failed to connect to Discord: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_connection())