
# TelScrape

A tool that lets you list/download attachments from a Telegram **PRIVATE GROUP** (when i have time i will implement functionality for public groups & channels as well) and keeps track of what’s been downloaded. It also lets you list files, filter specific extensions, and download individual files by index. 

Note that for my needs and also because of Telegram's queing system I've decided to go for sequential downloading. 
![Screenshot 2024-09-19 at 23 27 43](https://github.com/user-attachments/assets/4d7209c5-2928-4f32-b7cf-a30395ff551d)
![Screenshot 2024-09-19 at 23 27 53](https://github.com/user-attachments/assets/b1bc453f-81fc-4657-9398-9fb1fbefc24c)
![Screenshot 2024-09-19 at 23 28 14](https://github.com/user-attachments/assets/ba59a118-4b3e-49d1-93d8-40445a508d6c)
![Screenshot 2024-09-19 at 23 28 29](https://github.com/user-attachments/assets/75c9ab10-c1ed-4442-9981-54d461940e27)

## How to Get Your Telegram `api_id`, `api_hash`, and `group_name`

To use this app, you'll need to get your `api_id` and `api_hash` from Telegram, as well as the `group_name` (or username) of the group you're pulling files from.

1. **Sign up as a Telegram developer**:
    - Go to [my.telegram.org](https://my.telegram.org) and log in with your phone number.
    - Click on **API Development Tools**.
    - Create a new app, and Telegram will provide you with an `api_id` and `api_hash`.

2. **Find the Group's `group_name`**:
    - Open the Telegram app and go to the group you want to scrape files from.
    - If it’s a public group, you’ll see its username in the URL (something like `t.me/groupname`). That’s the `group_name` you need.
    - If it's private, use the display name shown in the group header (e.g., "We Love Red Team").

## How to Use the Tool

Once you have your `api_id`, `api_hash`, and `group_name`:

1. **Install the dependencies**:
   Make sure you have Python 3 and install the required packages by running:
   ```bash
   pip install telethon tabulate colorama
   ```

2. **Set your credentials**:
   Open the script and plug your `api_id`, `api_hash`, and `group_name`.

3. **List all the files in a group**:

   To list all the files in a group, run:
   ```bash
   python3 telscrape.py -l  # for groups that have 1500+ files, it might take 2-3 minutes to list them, paralelization didnt help due to telegram limitations. 
   ```
   You can also exclude certain file types from the list using the `-f` flag, on top of the default filtering I've mentioned previously. For example:
   ```bash
   python3 telscrape.py -l -f exe,pkg
   ```
   This will list all the files **except** `.exe` and `.pkg` files.

4. **Download specific files**:
   When listing files you will get on the first output column a file index. You can use that index(s) to download specific files:
   ```bash
   python3 telscrape.py -d 336
   ```
   This will download the file with index `336`. You can also download multiple files by passing a comma-separated list:
   ```bash
   python3 telscrape.py -d 2,5,10
   ```

5. **Download all files**:
   If you want to download everything (except automatically filtered files like `.tgs` and `.webp`), just run:
   ```bash
   python3 telscrape.py
   ```

## What the App Automatically Filters, How It Tracks Downloads, and How It Works

### Automatic Filtering
The app automatically skips downloading certain irrelevant file types, like Telegram stickers and animations.
For my needs I've included by default, when executing "python3 telscrape.py -l", an automatic filter of 'tgs', 'webp','mp4','jpg','jpeg','png' as there are not relevant to me. Feel free too adjust the code and remove them if you wish, I've added clear comments across the script. 

- `.tgs`  (Telegram stickers)
- `.webp` (Telegram animations)
- `.mp4`  (Telegram animations)
- `.jpg`  (Irelevant to my needs)
- `.jpeg` (Irelevant to my needs)
- `.png`  (Irelevant to my needs)

You can manually exclude other file types with the `-f` flag when listing.

### Important Files:
- **`downloaded_files.txt`**: 
  This file keeps track of every file that’s been fully downloaded, so the app doesn’t re-download the same file next time you run it with no flags.
  
- **`index_to_message_id.txt`**: 
  When you list the files using the `-l` command, this file is generated. It maps the index of each file to its message ID in Telegram. This ensures that when you request to download a file by its index, the app grabs the right one.
  
- **`telegram_downloads` folder**:
  This is where all the downloaded files go.

### How the App Works (High-level Overview):
1. **Listing Files**: The app connects to Telegram using the API, fetches the list of messages in the specified group, and displays a list of files. It automatically skips certain file types (like stickers) and lets you filter other extensions if needed. The file names and sizes are printed in a table format, with some color coding based on size and type.
   
2. **Downloading Files**: You can download all files, or just specific ones by their index. The app uses `index_to_message_id.txt` to map file indexes to Telegram message IDs, ensuring you download the correct file. Progress bars are shown for large files, and once a file is downloaded, it’s marked in `downloaded_files.txt` to prevent re-downloading.

3. **Error Handling**: The app gracefully handles Telegram-specific errors like expired file references, attempting to re-fetch the message when necessary. If a file can't be downloaded, it skips it and moves on.
