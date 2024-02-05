import discord
import ffmpeg
import os
import requests
import asyncio
from discord.ext import commands
from discord import app_commands

# Bot configuration
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=';', intents=intents)

# File download and serving configuration
download_path = "DOWNLOAD/PATH/LOCATION/" # The path where files will be saved
server_url = "http://YOUR.DOMAIN/" # Your domain where files will be served

# Supported formats
supported_formats = ['mp4', 'mp3', 'gif', 'png', 'jpg']

# Function to save the original file from Discord and convert it
async def convert_media(file, target_format):
    original_file_path = os.path.join(download_path, file.filename)
    await file.save(original_file_path)
    
    output_file_name = f"{os.path.splitext(file.filename)[0]}.{target_format}"
    output_file_path = os.path.join(download_path, output_file_name)
    
    ffmpeg.input(original_file_path).output(output_file_path).run(overwrite_output=True)
    
    os.remove(original_file_path)  # Remove original file if only the converted file is needed
    
    download_link = generate_download_link(output_file_path)
    return download_link

# Function to generate a unique download link for the converted file
def generate_download_link(file_path):
    unique_id = generate_unique_id()
    success = add_file_to_flask_app(unique_id, file_path)
    if success:
        return f"{server_url}{unique_id}"
    else:
        return "Failed to generate download link"

# Generate a unique ID for each file
def generate_unique_id(length=7):
    import string, random
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

# Add file mapping to the Flask app
def add_file_to_flask_app(unique_id, file_path):
    flask_url = "http://localhost:5000/add_mapping"
    data = {"unique_id": unique_id, "file_path": file_path}
    response = requests.post(flask_url, json=data)
    return response.status_code == 200

async def delete_file_after_delay(unique_id, delay):
    await asyncio.sleep(delay)
    flask_url = f"http://localhost:5000/delete_file/{unique_id}"
    response = requests.post(flask_url)

# Slash command for converting media files
@bot.tree.command(name='convert', description='Convert media files to a different format')
@app_commands.choices(target_format=[
    app_commands.Choice(name='mp4', value='mp4'),
    app_commands.Choice(name='mp3', value='mp3'),
    app_commands.Choice(name='gif', value='gif'),
    app_commands.Choice(name='png', value='png'),
    app_commands.Choice(name='jpg', value='jpg')
])
@app_commands.describe(target_format='The format you want to convert to')
async def convert(interaction: discord.Interaction, target_format: app_commands.Choice[str], attachment: discord.Attachment):
    if target_format.value not in supported_formats:
        await interaction.response.send_message(f"The format `{target_format.value}` is not supported.", ephemeral=True)
        return

    download_link = await convert_media(attachment, target_format.value)

    unique_id = download_link.split("/")[-1]
    asyncio.create_task(delete_file_after_delay(unique_id, 600))  # Delete the file after 10 minutes

    await interaction.response.send_message(f"File converted to {target_format.value}. Download link: {download_link}", ephemeral=True)

# Bot event on ready
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    await bot.tree.sync()

bot.run('YOUR_BOT_TOKEN') # Replace with your bot's token
