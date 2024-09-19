import os
import sys
import asyncio
from telethon import TelegramClient
from telethon.errors import FileReferenceExpiredError
from telethon.tl.types import DocumentAttributeFilename
from tabulate import tabulate  # for pretty printing the table
from colorama import Fore, Style  # for coloring the table output


# Set up your API credentials here
api_id = 'your_app_id'
api_hash = 'your_api_hash'
group_name = 'your_private_group_name'  # The name of the Telegram group
download_folder = 'telegram_downloads'
os.makedirs(download_folder, exist_ok=True)

# Path to store the downloaded files list
completed_files_path = 'downloaded_files.txt'

# Initialize the Telegram client
client = TelegramClient('session_name', api_id, api_hash)

# Progress bar callback function
def progress_callback(current, total):
    progress_percentage = current / total * 100
    print(f"\rDownloading... {current // (1024 * 1024)}MB / {total // (1024 * 1024)}MB ({progress_percentage:.2f}%)", end='')

# Function to extract the file name
def get_file_name(message):
    if hasattr(message.media, 'document') and message.media.document:
        for attr in message.media.document.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                return attr.file_name
    if message.photo:
        return f'photo_{message.id}.jpg'
    if message.video:
        return f'video_{message.id}.mp4'
    if message.audio:
        return f'audio_{message.id}.mp3'
    if message.voice:
        return f'voice_{message.id}.ogg'
    return None

# Function to save completed file names to a file
def save_completed_file(file_name):
    with open(completed_files_path, 'a') as f:
        f.write(f"{file_name}\n")

# Function to load completed files
def load_completed_files():
    if os.path.exists(completed_files_path):
        with open(completed_files_path, 'r') as f:
            return set(f.read().splitlines())
    return set()

# Function to clean up partial files
def clean_partial_files(completed_files):
    # Get all files in the download folder
    for file in os.listdir(download_folder):
        file_path = os.path.join(download_folder, file)
        # If the file is not in the completed files list and exists as a partial, delete it
        if file not in completed_files and os.path.isfile(file_path):
            print(f"Deleting partial file: {file}")
            os.remove(file_path)

# Async function to download all attachments from the group sequentially
async def download_attachments():
    await client.start()

    # Load the list of completed files
    completed_files = load_completed_files()

    # Clean up any partial files (not in completed list)
    clean_partial_files(completed_files)

    # Search for the group by its name
    dialogs = await client.get_dialogs()
    group = None

    # Loop through dialogs to find the group by name
    for dialog in dialogs:
        if dialog.name == group_name:
            group = dialog.entity
            break

    if group:
        print(f"Found group: {group_name}")

        # Fetch all the messages in the group one by one and download media
        async for message in client.iter_messages(group):
            if message.media:
                try:
                    file_name = get_file_name(message)
                    if not file_name:
                        continue  # Skip unsupported media types
                    file_ext = file_name.split('.')[-1].lower()
                    if file_ext in ['tgs', 'webp', 'mp4', 'jpg', 'jpeg', 'png']:  # Skip .tgs, .webp and other files
                        continue

                    file_path = os.path.join(download_folder, file_name)

                    # Skip if the file has already been fully downloaded and exists in completed_files
                    if file_name in completed_files and os.path.exists(file_path):
                        print(f"Skipping {file_name}, already downloaded.")
                        continue

                    # Print when the download starts
                    print(f"\nStarting download of: {file_name}")

                    # Download the file with progress callback
                    file_path = await message.download_media(file=download_folder, progress_callback=progress_callback)

                    print(f"\nDownloaded: {file_path}")

                    # Mark the file as completed
                    save_completed_file(file_name)

                except FileReferenceExpiredError:
                    print(f"File reference expired for message ID {message.id}. Re-fetching message...")

                    # Attempt to refresh the file reference by refetching the message
                    fresh_message = await client.get_messages(group, ids=message.id)

                    if fresh_message.media:
                        try:
                            file_name = get_file_name(fresh_message)
                            print(f"\nRetrying download of: {file_name}")
                            file_path = await fresh_message.download_media(file=download_folder, progress_callback=progress_callback)
                            print(f"\nDownloaded after refetch: {file_path}")
                            save_completed_file(file_name)
                        except FileReferenceExpiredError:
                            print(f"File reference expired again for {fresh_message.id}. Skipping file: {file_name or 'Unknown file'}")
                        except Exception as e:
                            print(f"Error after refetch: {str(e)}")
                    else:
                        print(f"Media not found in refetched message {message.id}. Skipping...")
                except Exception as e:
                    print(f"An error occurred: {str(e)}")

    else:
        print(f"Group '{group_name}' not found. Make sure you're part of it.")

# Function to list all files in the group, with optional filtering
async def list_files_in_group(filtered_extensions=None):
    await client.start()

    dialogs = await client.get_dialogs()
    group = None

    for dialog in dialogs:
        if dialog.name == group_name:
            group = dialog.entity
            break

    if group:
        print(f"Found group: {group_name}")

        # Dictionary to store index and corresponding message ID
        index_to_message_id = {}
        files = []
        index = 1
        async for message in client.iter_messages(group):
            if message.media:
                file_name = get_file_name(message)
                if not file_name:
                    continue  # Skip unsupported media types

                # Get the file extension and automatically filter out .tgs and .webp
                file_ext = file_name.split('.')[-1].lower()
                if file_ext in ['tgs', 'webp', 'mp4', 'jpg', 'jpeg', 'png']:
                    continue  # Skip irrelevant Telegram stickers and animations

                if filtered_extensions and file_ext in filtered_extensions:
                    continue

                file_size = message.file.size if message.file else 0
                file_size_gb = file_size / (1024 * 1024 * 1024)  # Convert size to GB

                if file_size_gb > 5:
                    color = Fore.RED
                elif file_ext in ['jpg', 'png']:
                    color = Fore.CYAN
                else:
                    color = Fore.GREEN

                # Store the index-to-message_id mapping
                index_to_message_id[index] = message.id

                # Add file info to list
                files.append([f"{color}{index}{Style.RESET_ALL}", 
                              f"{color}{file_name}{Style.RESET_ALL}", 
                              f"{color}{file_size_gb:.2f} GB{Style.RESET_ALL}"])
                index += 1

        # Print files as a table with color coding
        print(tabulate(files, headers=["Index", "File Name", "File Size"]))
        
        # Save index-to-message mapping for use in downloads
        with open('index_to_message_id.txt', 'w') as f:
            for idx, msg_id in index_to_message_id.items():
                f.write(f"{idx},{msg_id}\n")

    else:
        print(f"Group '{group_name}' not found.")

# Function to download specific files by index
async def download_specific_files(file_indexes):
    await client.start()

    # Load the list of completed files
    completed_files = load_completed_files()

    # Clean up any partial files (not in completed list)
    clean_partial_files(completed_files)

    # Load the index-to-message_id mapping
    index_to_message_id = {}
    with open('index_to_message_id.txt', 'r') as f:
        for line in f:
            idx, msg_id = line.strip().split(',')
            index_to_message_id[int(idx)] = int(msg_id)

    dialogs = await client.get_dialogs()
    group = None

    for dialog in dialogs:
        if dialog.name == group_name:
            group = dialog.entity
            break

    if group:
        print(f"Found group: {group_name}")

        for index in file_indexes:
            # Get the message ID corresponding to the file index
            if index not in index_to_message_id:
                print(f"Index {index} not found.")
                continue

            message_id = index_to_message_id[index]
            message = await client.get_messages(group, ids=message_id)

            if message.media:
                try:
                    file_name = get_file_name(message)
                    if not file_name:
                        continue  # Skip unsupported media types
                    file_ext = file_name.split('.')[-1].lower()
                    if file_ext in ['tgs', 'webp']:
                        continue  # Skip .tgs and .webp files

                    file_path = os.path.join(download_folder, file_name)

                    # Skip if the file has already been fully downloaded and exists in completed_files
                    if file_name in completed_files and os.path.exists(file_path):
                        print(f"Skipping {file_name}, already downloaded.")
                        continue

                    # Print when the download starts
                    print(f"\nStarting download of: {file_name}")

                    # Download the file with progress callback
                    file_path = await message.download_media(file=download_folder, progress_callback=progress_callback)

                    print(f"\nDownloaded: {file_path}")

                    # Mark the file as completed
                    save_completed_file(file_name)

                except FileReferenceExpiredError:
                    print(f"File reference expired for message ID {message.id}. Re-fetching message...")

                except Exception as e:
                    print(f"An error occurred: {str(e)}")

    else:
        print(f"Group '{group_name}' not found.")

# Main block to handle command-line arguments and keyboard interrupt
try:
    if len(sys.argv) > 1:
        if sys.argv[1] == '-l':
            # Check for filtering flag
            filtered_extensions = None
            if len(sys.argv) > 3 and sys.argv[2] == '-f':
                filtered_extensions = sys.argv[3].split(',')
            # List files in the group with optional filtering
            client.loop.run_until_complete(list_files_in_group(filtered_extensions))
        elif sys.argv[1] == '-d' and len(sys.argv) > 2:
            # Download specific files by index
            file_indexes = list(map(int, sys.argv[2].split(',')))
            client.loop.run_until_complete(download_specific_files(file_indexes))
        else:
            print("Usage:")
            print("  python3 telscrape.py -l              # List all files")
            print("  python3 telscrape.py -l -f jpg,png    # List files excluding these extensions")
            print("  python3 telscrape.py -d 1,2,3        # Download specific files by index")
    else:
        # Default behavior (download all files)
        with client:
            client.loop.run_until_complete(download_attachments())
except KeyboardInterrupt:
    print("\nUser closed the app. Exiting gracefully...")