# telegram-auto-upload-folder
Automatically uploads the content of a folder to a specific chat when certain conditions are met, and removes the files as they're uploaded

## The authors
The idea behind this project and its original code have been created by [@Soundhunter6154](https://github.com/Soundhunter6154)  
I ([@EDM115](https://github.com/EDM115)) fixed most of the code, added features and made it more user-friendly

## The reason behind this project
Imagine you have 50 Gb left on your disk. You have a 200Gb archive that you want to compress and send to Telegram. You don't have enough space to store the compressed archive, so you can't send it.  
This script solves this problem by uploading the files as they're compressed, and removing them as they're uploaded.

## How to use
1. Run the following commands :
    ```bash
    git clone https://github.com/EDM115/telegram-auto-upload-folder.git
    cd telegram-auto-upload-folder
    pip install -U asyncio dotenv pillow pyrogram tgcrypto watchdog
    ```
2. Edit the `.env` file with your own values, example :
    ```env
    CHAT_ID=-100123
    TELEGRAM_API_HASH="abc123"
    TELEGRAM_APP_ID=123
    TELEGRAM_BOT_TOKEN="123:abc123"
    THUMB="/path/to/image.png"
    WATCH_DIRECTORY="/path/to/watch/dir"
    ```
    Warning points :
    - Don't remove any existing quote, and don't addd space around the equal signs
    - You can keep `THUMB` empty if you don't plan to use one
    - Both `WATCH_DIRECTORY` and `THUMB` have to be absolute paths
    - Even on Windows, use `/` instead of `\` in paths (else it will very likely break). Example : `THUMB="D:/EDM115/Pictures/Downloaded/flushed_bread.png"` (wanna see the flushed bread ? check [@Dziurwa14](https://github.com/Dziurwa14)'s profile)
    - The `CHAT_ID` can be found by adding [@MissRose_bot](https://t.me/MissRose_bot) to your chat and sending `/id`. It can also be a username (without the `@`)
    - The `TELEGRAM_API_HASH` and `TELEGRAM_APP_ID` can be found by creating a new app on [my.telegram.org](https://my.telegram.org)
    - The `TELEGRAM_BOT_TOKEN` can be found by creating a new bot on [@BotFather](https://t.me/BotFather)
3. Add the bot to the chat you want to upload to
4. Start the bot with `python upload_script.py`

Example command to test the bot :
```bash
7z a -v50m path_to_watch_dir\test.zip path_to_big_folder
```

## Features
- Automatically uploads the content of a folder to a specific chat (doesn't support topics)
- Watches for files ending in :
  - `.zip`
  - `.rar`
  - `.7z`
  - `.tar`
  - `.tar.*`
  - All of the above but also ends in `.XXX` (splitted archives)
  - Skips `.tmp` files (ex : outputs of 7z while compressing)
- Automatically removes the files as they're uploaded
- Thumbnail support
- Stores files to upload in a queue, so they get uploaded in the order they were added and not all at once
- Doesn't watch for subdirectories
- Handles FloodWait errors (cooldowns by Telegram)
- Runs everything asynchronously
- You can <kbd>Ctrl</kbd>+<kbd>C</kbd> to stop the script at any time

## License
This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details
