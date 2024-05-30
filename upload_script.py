# Base libraries
import asyncio
import logging
import os
import signal
import re

# Third-party libraries
from dotenv import load_dotenv
from PIL import Image
from pyrogram import Client, idle
from pyrogram.errors import FloodWait
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


# Load environment variables
load_dotenv()

CHAT_ID = os.environ.get("CHAT_ID")
TELEGRAM_API_HASH = os.environ.get("TELEGRAM_API_HASH")
TELEGRAM_APP_ID = os.environ.get("TELEGRAM_APP_ID")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
THUMB = r"{}".format(os.environ.get("THUMB"))
WATCH_DIRECTORY = r"{}".format(os.environ.get("WATCH_DIRECTORY"))
upload_thumb = os.path.join(WATCH_DIRECTORY, "thumb.jpg")

# Logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler()],
    format="%(asctime)s - %(name)s - %(message)s",
)
LOGGER = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.INFO)

# Files to upload are stored in a queue, so they gets uploaded one by one instead of all at once
file_queue = asyncio.Queue()
loop = None


# Everytime a chunk is uploaded to Telegram, this function is called
def progress(current, total, file_path):
    LOGGER.info(f"{file_path} : {current * 100 / total:.1f}%")


# Creates a thumbnail with the right format and size based on the provided image
def create_thumb():
    if os.path.exists(THUMB):
        size = 320, 320

        try:
            with Image.open(THUMB) as im:
                # Ensure the image have no transparency so it can be saved as JPEG
                if im.mode in ("RGBA", "LA"):
                    background = Image.new("RGB", im.size, (255, 255, 255))
                    alpha_channel = im.getchannel('A')
                    background.paste(im, mask=alpha_channel)
                    im = background

                im.thumbnail(size, Image.Resampling.LANCZOS)
                im.save(upload_thumb, "JPEG")
                LOGGER.info(f"Thumbnail created : {upload_thumb}")
        except Exception as e:
            LOGGER.info(f"Failed to create thumbnail : {e}")


# Main class that handles the file system events
class UploadHandler(FileSystemEventHandler):
    # Constructor that receives the event loop
    def __init__(self, loop):
        self.loop = loop


    # Watch for file creation events
    def on_created(self, event):
        self.loop.call_soon_threadsafe(self.loop.create_task, self.process(event.src_path))


    # Watch for file modification events (ex: file is still being written to disk)
    def on_modified(self, event):
        self.loop.call_soon_threadsafe(self.loop.create_task, self.delayed_process(event.src_path))


    # Watch for file move events (ex: file is being moved to the watched directory, or renamed)
    def on_moved(self, event):
        self.loop.call_soon_threadsafe(self.loop.create_task, self.process(event.dest_path))


    # Allows to delay the processing of a file by 10 seconds
    async def delayed_process(self, file_path):
        await asyncio.sleep(10)
        await self.process(file_path)


    # Process the file, check if it's a valid file and queue it for upload
    async def process(self, file_path):
        if os.path.isfile(file_path):
            LOGGER.info(f"Processing file : {file_path}")
            # Checks if the file is not a temporary file and has a valid extension (*.zip, *.rar, .*7z, *.tar, *.tar.*, and all of the previous ones with a .XXX extension at the end (splitted files))
            valid_extensions = r"(\.zip|\.rar|\.7z|\.tar(\.\w+)?)(\.\d{3})?$"
            if (not file_path.endswith(".tmp")) and (re.search(valid_extensions, file_path)):
                LOGGER.info(f"Valid file : {file_path}")
                # Checks if the file is still being written to disk
                initial_size = os.path.getsize(file_path)
                await asyncio.sleep(5)
                final_size = os.path.getsize(file_path)

                if initial_size == final_size:
                    LOGGER.info(f"Queueing file for upload : {file_path}")
                    await file_queue.put(file_path)
                else:
                    LOGGER.info(f"File size changed, delaying processing : {file_path}")
                    await self.delayed_process(file_path)


async def main():
    # Create a global asyncio loop, ensuring that all the coroutines are running in the same loop
    global loop
    loop = asyncio.get_running_loop()

    # Create the bot after the loop is created
    global bot
    bot = Client(
        "upload_script",
        api_id=TELEGRAM_APP_ID,
        api_hash=TELEGRAM_API_HASH,
        bot_token=TELEGRAM_BOT_TOKEN
    )

    # Create the thumbnail
    create_thumb()

    # Try to start the bot, allow to check for PEER_ID_INVALID beforehand
    try:
        await bot.start()
        await bot.send_message(CHAT_ID, "Bot started")
        LOGGER.info("Bot started")
    except Exception as e:
        LOGGER.info(f"Failed to start bot : {e}")
        return

    # Sets up the file system watcher, doesn't watch subdirectories
    event_handler = UploadHandler(loop)
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIRECTORY, recursive=False)
    observer.start()
    LOGGER.info(f"Watching directory : {WATCH_DIRECTORY}")

    # Start the upload worker
    upload_task = asyncio.create_task(upload_worker())

    try:
        # Keep the bot running
        await idle()
    except KeyboardInterrupt:
        LOGGER.info("Received exit, stopping...")
    finally:
        # Remove the generated thumbnail
        if os.path.exists(upload_thumb):
            os.remove(upload_thumb)

        # Stop the observer, empty the queue and stop the bot
        observer.stop()
        observer.join()
        await bot.send_message(CHAT_ID, "Bot stopping")
        upload_task.cancel()
        await bot.stop()
        LOGGER.info("Bot stopped")


# Handles the upload of files to Telegram
async def upload_worker():
    while True:
        # Get the next file to upload from the queue
        file_path = await file_queue.get()

        try:
            LOGGER.info(f"Uploading file : {file_path}")
            # Sends the file to Telegram, with the right thumbnail if it exists and without notifications
            await bot.send_document(
                chat_id=CHAT_ID,
                document=file_path,
                disable_notification=True,
                progress=progress,
                progress_args=(file_path,),
                thumb=upload_thumb if os.path.exists(upload_thumb) else None
            )
            LOGGER.info(f"Uploaded : {file_path}")
            # Remove the file after it's uploaded
            os.remove(file_path)
            LOGGER.info(f"Deleted : {file_path}")
        except FloodWait as f:
            # If a FloodWait is encountered (too much messages sent in a short amount of time, see it as a cooldown), sleep for the time provided by Telegram and requeue the file
            LOGGER.info(f"FloodWait encountered, sleeping for {f.value} seconds")
            await asyncio.sleep(f.value)
            await file_queue.put(file_path)
        except Exception as e:
            LOGGER.info(f"Failed to upload {file_path} : {e}")
        finally:
            # Mark the task as done, allowing the next file to be processed
            file_queue.task_done()


# Hackish way to handle Ctrl+C even when the script is stuck or doesn't allow it
def handle_exit(signal, frame):
    raise KeyboardInterrupt


# Starts the script, and defines the signal handlers
if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    try:
        # Run the main coroutine asynchronously
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        LOGGER.info("Bot stopped")
