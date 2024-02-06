import discord
import os
import requests
import asyncio
import subprocess
import tempfile
import shutil
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
async def convert_media(file, target_format, upscale_factor=1):
    original_file_path = os.path.join(download_path, file.filename)
    await file.save(original_file_path)
    
    # Generate a temporary output file path
    temp_dir = tempfile.mkdtemp()
    output_file_name = f"{os.path.splitext(file.filename)[0]}"
    if upscale_factor != 1:
        output_file_name += f"_{upscale_factor}x"
    output_file_name += f".{target_format}"
    temp_output_file_path = os.path.join(temp_dir, output_file_name)

    try:
        if upscale_factor != 1:
            scale = f"scale=iw*{upscale_factor}:-1"
            cmd = ['ffmpeg', '-y', '-i', original_file_path, '-vf', scale, temp_output_file_path]
        else:
            cmd = ['ffmpeg', '-y', '-i', original_file_path, temp_output_file_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            shutil.rmtree(temp_dir)  # Clean up the temporary directory
            return "Failed to convert file due to ffmpeg error."
    except Exception as e:
        print(f"Exception occurred: {e}")
        shutil.rmtree(temp_dir)  # Clean up the temporary directory
        return "Failed to convert file due to an unexpected error."

    # Replace the original file with the converted file
    shutil.move(temp_output_file_path, original_file_path)
    shutil.rmtree(temp_dir)  # Clean up the temporary directory
    
    download_link = generate_download_link(original_file_path)
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
@app_commands.describe(target_format='The format you want to convert to', upscale='The upscale factor (e.g., 2 for 2x, 1 for no upscale)')
async def convert(interaction: discord.Interaction, target_format: app_commands.Choice[str], attachment: discord.Attachment, upscale: float = 1.0):
    is_upscaling_allowed = target_format.value in ['png', 'jpg']

    # Always defer the response first
    await interaction.response.defer(ephemeral=True)

    initial_message = ""
    if upscale > 1 and not is_upscaling_allowed:
        # Prepare an initial note about upscaling limitations
        initial_message = "Note: Upscale is only available for PNG and JPG formats."

    await interaction.edit_original_response(content=initial_message)

    # Proceed with conversion (and upscaling if applicable)
    download_link = await convert_media(attachment, target_format.value, upscale if is_upscaling_allowed else 1)

    # Construct the conversion completion message
    message = f"File converted to {target_format.value}."
    if upscale > 1 and is_upscaling_allowed:
        message += f" Upscaled by {upscale}x."
    message += f" Download link: {download_link}"

    # Delete file after 10 minutes
    unique_id = download_link.split("/")[-1]
    asyncio.create_task(delete_file_after_delay(unique_id, 600))

    # Edit the deferred response with the complete message
    await interaction.edit_original_response(content=message)

# Bot event on ready
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    await bot.tree.sync()

bot.run('YOUR_BOT_TOKEN') # Replace with your bot's token
