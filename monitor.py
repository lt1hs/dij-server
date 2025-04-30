import os
import asyncio
import requests
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler
from datetime import datetime
import signal

# Load environment variables
load_dotenv()

# Configure Telegram bot
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_IDS = [id.strip() for id in os.getenv('TELEGRAM_CHAT_ID').split(',')]
WEBSITE_URL = os.getenv('WEBSITE_URL')

def check_website():
    try:
        response = requests.get(WEBSITE_URL, timeout=10)
        return response.status_code == 200
    except requests.RequestException:
        return False

async def send_telegram_message(bot, message):
    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            await bot.send_message(chat_id=chat_id, text=message)
            print(f"Message sent to chat ID: {chat_id}")
        except Exception as e:
            print(f"Failed to send message to chat ID {chat_id}: {e}")

async def check_status_command(update, context):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_up = check_website()
    
    if is_up:
        message = f"✅ Website Status Check\nTime: {current_time}\nURL: {WEBSITE_URL}\nStatus: ONLINE"
    else:
        message = f"❌ Website Status Check\nTime: {current_time}\nURL: {WEBSITE_URL}\nStatus: OFFLINE"
    
    await update.message.reply_text(message)

# Define a stop event
stop_event = asyncio.Event()

# Signal handler to set the stop event
def signal_handler():
    print("Stopping bot...")
    stop_event.set()

async def monitor_website(bot):
    last_status = True  # Assume website is initially up
    while not stop_event.is_set():
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            is_up = check_website()
            
            if last_status and not is_up:
                message = f"🔴 Website is DOWN!\nTime: {current_time}\nURL: {WEBSITE_URL}"
                await send_telegram_message(bot, message)
                print(f"Website is down at {current_time}")
            elif not last_status and is_up:
                message = f"🟢 Website is back UP!\nTime: {current_time}\nURL: {WEBSITE_URL}"
                await send_telegram_message(bot, message)
                print(f"Website is back up at {current_time}")
            
            last_status = is_up
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=30)
            except asyncio.TimeoutError:
                pass  # This is expected, continue the loop
        except Exception as e:
            print(f"Error in monitoring: {e}")
            await asyncio.sleep(5)

def main():
    """Run the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("check", check_status_command))
    
    # Register signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    async def start():
        print("Website monitoring started...")
        print(f"Monitoring URL: {WEBSITE_URL}")
        print(f"Sending notifications to {len(TELEGRAM_CHAT_IDS)} chat IDs")
        print("Bot started successfully! You can now use /check command.")
        
        # Start the Bot
        await application.initialize()
        await application.start()
        
        # Start the monitoring task
        monitor = asyncio.create_task(monitor_website(application.bot))
        
        # Run the bot until the user presses Ctrl-C
        await application.updater.start_polling()
        
        # Wait for stop event
        await stop_event.wait()
        
        # Stop the monitoring task
        monitor.cancel()
        try:
            await monitor
        except asyncio.CancelledError:
            pass
        
        # Stop the Bot
        await application.stop()
        await application.shutdown()
    
    try:
        asyncio.run(start())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()