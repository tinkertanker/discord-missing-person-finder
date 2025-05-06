import os
import discord
import pandas as pd
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Dict, Optional

# Import our custom modules
from src.attendee_manager import AttendeeManager
from src.name_matcher import NameMatcher

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
    print(f'Connected to {len(bot.guilds)} guilds:')
    for guild in bot.guilds:
        print(f'- {guild.name} (ID: {guild.id})')

@bot.command(name='check_attendance')
async def check_attendance(ctx, file_path: Optional[str] = None, threshold: Optional[int] = 80):
    """
    Check attendance by comparing Discord members against an attendee list.
    
    Args:
        ctx: The Discord context
        file_path (Optional[str]): Path to the attendee list CSV (overrides .env setting)
        threshold (Optional[int]): Similarity threshold for name matching (default: 80)
    """
    # Acknowledge the command
    processing_msg = await ctx.send("📋 Processing attendance check... This might take a moment.")
    
    # Get the guild (server)
    guild = ctx.guild
    if not guild:
        await processing_msg.edit(content="❌ This command must be used in a server.")
        return
    
    try:
        # Load attendees
        manager = AttendeeManager(file_path)
        if not manager.load_attendees():
            await processing_msg.edit(content="❌ Failed to load attendee list. Check the file path and format.")
            return
        
        attendees = manager.get_attendees()
        attendee_names = manager.get_attendee_names()
        groups = manager.get_groups()
        
        # Get Discord members
        members = guild.members
        member_names = [member.name for member in members]
        
        # Match names
        matcher = NameMatcher(similarity_threshold=threshold)
        missing_attendees_names = matcher.find_missing_attendees(member_names, attendee_names)
        
        # Structure missing attendees by group
        missing_by_group = {}
        for name in missing_attendees_names:
            # Find the attendee's group
            group = next((a['group'] for a in attendees if a['name'] == name), "Unknown")
            
            if group not in missing_by_group:
                missing_by_group[group] = []
            missing_by_group[group].append(name)
        
        # Generate report
        if not missing_attendees_names:
            report = "✅ All attendees are present in Discord! Great job!"
        else:
            report = f"🔍 **Missing Attendees Report** ({len(missing_attendees_names)} missing)\n\n"
            
            for group, names in sorted(missing_by_group.items()):
                report += f"**Group: {group}** ({len(names)} missing)\n"
                for i, name in enumerate(sorted(names)):
                    report += f"{i+1}. {name}\n"
                report += "\n"
        
        # Send the report as a message (or multiple messages if too long)
        await processing_msg.edit(content="✅ Attendance check completed!")
        
        # Discord has a 2000 character message limit, so we may need to split the report
        max_length = 1990  # Leaving some room for safety
        if len(report) <= max_length:
            await ctx.send(report)
        else:
            # Split the report into chunks
            chunks = [report[i:i+max_length] for i in range(0, len(report), max_length)]
            for i, chunk in enumerate(chunks):
                await ctx.send(f"📑 Report Part {i+1}/{len(chunks)}:\n{chunk}")
        
        # Save report to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"attendance_report_{timestamp}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            # Write summary
            f.write(f"Attendance Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Server: {guild.name} (ID: {guild.id})\n")
            f.write(f"Total Discord Members: {len(members)}\n")
            f.write(f"Total Attendees: {len(attendees)}\n")
            f.write(f"Missing Attendees: {len(missing_attendees_names)}\n\n")
            
            # Write detailed report
            f.write(report)
        
        await ctx.send(f"📄 Full report saved to `{filename}`")
    
    except Exception as e:
        await processing_msg.edit(content=f"❌ An error occurred: {str(e)}")

@bot.command(name='export_missing')
async def export_missing(ctx, file_path: Optional[str] = None, threshold: Optional[int] = 80):
    """
    Export missing attendees to an Excel file.
    
    Args:
        ctx: The Discord context
        file_path (Optional[str]): Path to the attendee list CSV (overrides .env setting)
        threshold (Optional[int]): Similarity threshold for name matching (default: 80)
    """
    processing_msg = await ctx.send("📊 Exporting missing attendees... This might take a moment.")
    
    # Get the guild (server)
    guild = ctx.guild
    if not guild:
        await processing_msg.edit(content="❌ This command must be used in a server.")
        return
    
    try:
        # Load attendees
        manager = AttendeeManager(file_path)
        if not manager.load_attendees():
            await processing_msg.edit(content="❌ Failed to load attendee list. Check the file path and format.")
            return
        
        attendees = manager.get_attendees()
        attendee_names = manager.get_attendee_names()
        
        # Get Discord members
        members = guild.members
        member_names = [member.name for member in members]
        
        # Match names
        matcher = NameMatcher(similarity_threshold=threshold)
        missing_attendees_names = matcher.find_missing_attendees(member_names, attendee_names)
        
        # Create dataframe for the missing attendees
        missing_data = []
        for name in missing_attendees_names:
            # Find the complete attendee record
            attendee = next((a for a in attendees if a['name'] == name), None)
            if attendee:
                missing_data.append({
                    'Name': name,
                    'Group': attendee['group']
                })
        
        # Create Excel file
        if missing_data:
            df = pd.DataFrame(missing_data)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"missing_attendees_{timestamp}.xlsx"
            df.to_excel(filename, index=False)
            
            await processing_msg.edit(content=f"✅ Export completed! {len(missing_data)} missing attendees saved to `{filename}`")
        else:
            await processing_msg.edit(content="✅ No missing attendees found! Everyone is present.")
    
    except Exception as e:
        await processing_msg.edit(content=f"❌ An error occurred: {str(e)}")

@bot.command(name='help_attendance')
async def help_attendance(ctx):
    """Show help information for attendance checking commands."""
    help_text = """
**Discord Attendance Checker Help**

**Commands:**
`!check_attendance [file_path] [threshold]`
Check attendance and list missing students by group.

`!export_missing [file_path] [threshold]`
Export missing attendees to an Excel file.

**Parameters:**
- `file_path` (optional): Path to the attendee CSV file. If not provided, uses the path in .env.
- `threshold` (optional): Similarity threshold for name matching (0-100). Default: 80.

**Example:**
`!check_attendance ./my_attendees.csv 75`
"""
    await ctx.send(help_text)

def main():
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        raise ValueError("No Discord token found. Please set the DISCORD_TOKEN environment variable.")
    bot.run(token)

if __name__ == "__main__":
    main()