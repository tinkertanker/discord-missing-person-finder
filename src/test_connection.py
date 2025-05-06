import os
import discord
import asyncio
import csv
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.members = True  # Enable members intent to fetch member list

async def test_connection():
    """Test connection to Discord and show basic server information."""
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

async def export_discord_members():
    """
    Export all Discord members from the server to a text file with the format:
    Discord ID | Display Name | Username | Nickname | Roles
    """
    # Get configuration from environment variables
    token = os.getenv('DISCORD_TOKEN')
    guild_id = os.getenv('GUILD_ID')
    
    if not token:
        print("ERROR: No Discord token found. Please set the DISCORD_TOKEN in your .env file.")
        return
    
    if not guild_id:
        print("ERROR: No Guild ID found. Please set the GUILD_ID in your .env file.")
        return
    
    try:
        guild_id = int(guild_id)  # Convert string to integer
    except ValueError:
        print(f"ERROR: Invalid Guild ID: {guild_id}. Must be an integer.")
        return
    
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
            print(f"Server has {len(members)} members. Exporting details...")
            
            # Generate timestamp for the filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"discord_members_{timestamp}.txt"
            
            # Export member details to text file
            with open(filename, 'w', encoding='utf-8') as f:
                # Write header
                f.write("Discord ID | Display Name | Username | Nickname | Roles\n")
                f.write("-" * 80 + "\n")
                
                # Write member details
                for member in sorted(members, key=lambda m: m.display_name.lower()):
                    # Get roles (excluding @everyone)
                    roles = [role.name for role in member.roles if role.name != "@everyone"]
                    roles_str = ", ".join(roles) if roles else "None"
                    
                    # Format member details
                    line = f"{member.id} | {member.display_name} | {member.name} | "
                    line += f"{member.nick if member.nick else 'None'} | {roles_str}\n"
                    
                    f.write(line)
            
            # Also create a simple CSV file for easier processing
            csv_filename = f"discord_members_{timestamp}.csv"
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                # Write header
                writer.writerow(['Discord ID', 'Display Name', 'Username', 'Nickname', 'Roles'])
                
                # Write member details
                for member in sorted(members, key=lambda m: m.display_name.lower()):
                    roles = [role.name for role in member.roles if role.name != "@everyone"]
                    roles_str = ", ".join(roles) if roles else ""
                    
                    writer.writerow([
                        member.id,
                        member.display_name,
                        member.name,
                        member.nick if member.nick else "",
                        roles_str
                    ])
            
            print(f"Discord members exported to {filename} and {csv_filename}")
            
            # Create a simple version with just names for debugging
            debug_filename = "discord_members.txt"
            with open(debug_filename, 'w', encoding='utf-8') as f:
                for member in sorted(members, key=lambda m: m.display_name.lower()):
                    # Format simplified for name matching debugging
                    roles = [role.name for role in member.roles if role.name != "@everyone"]
                    roles_str = ",".join(roles) if roles else ""
                    
                    # Try to extract cat-x-grp-y pattern from roles
                    group_code = ""
                    for role in roles:
                        if role.startswith("cat-") and "-grp-" in role:
                            group_code = role.split(",")[0].strip()
                            break
                    
                    line = f"{member.id}|{member.display_name}|{member.name}|{member.nick or ''}|{group_code}|{roles_str}\n"
                    f.write(line)
            
            print(f"Simple debug list exported to {debug_filename}")
            
            # Export a specialized file just for group matching
            group_filename = "discord_groups.csv"
            with open(group_filename, 'w', encoding='utf-8') as f:
                f.write("Discord ID,Display Name,Username,Nickname,Group Code,Has Participant Role\n")
                for member in sorted(members, key=lambda m: m.display_name.lower()):
                    # Extract group code
                    group_code = ""
                    has_participant = "No"
                    
                    for role in member.roles:
                        if role.name != "@everyone":
                            if role.name.startswith("cat-") and "-grp-" in role.name:
                                group_code = role.name.split(",")[0].strip()
                            if role.name == "participant":
                                has_participant = "Yes"
                    
                    # Format for group matching
                    f.write(f"{member.id},{member.display_name.replace(',', ' ')},{member.name.replace(',', ' ')},")
                    f.write(f"{(member.nick or '').replace(',', ' ')},{group_code},{has_participant}\n")
            
            print(f"Group matching data exported to {group_filename}")
            
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
    # By default, run the connection test
    command = os.getenv('DISCORD_COMMAND', 'test')
    
    if command == 'export':
        # Run the export function if requested
        asyncio.run(export_discord_members())
    else:
        # Otherwise run the test connection
        asyncio.run(test_connection())