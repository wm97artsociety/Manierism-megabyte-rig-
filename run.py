#!/usr/bin/env python3

import os, time, json, random, uuid, hashlib, threading, requests, webbrowser
from bs4 import BeautifulSoup
from flask import Flask, render_template_string
from decimal import Decimal, getcontext
import math

getcontext().prec = 200

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    MOTOR_PIN = 18
    RESISTOR_PIN = 23
    CAPACITOR_PIN = 24
    GPIO.setup(MOTOR_PIN, GPIO.OUT)
    GPIO.setup(RESISTOR_PIN, GPIO.OUT)
    GPIO.setup(CAPACITOR_PIN, GPIO.OUT)
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False

BASEDIR = "/storage/emulated/0/Download/manierismmegabytes"
TARGETDIR = os.path.join(BASEDIR, "rigs")
os.makedirs(TARGETDIR, exist_ok=True)

DONATION_WALLET_ID = "WM-CPH0O7J3"
WORLD_DEBT_WALLET_ID = "WD-P4Y29G7B"
WORLD_DEBT_NODE_ID = "9efae649-eb1f-4ef0-ac97-ed4df6d2942f"
INITIAL_WORLD_DEBT_USD = Decimal("31300000000000.00")
WORLD_DEBT_DATE = "October 4th, 2025"
DEBT_NODE_PASSIVE_USD_VALUE = Decimal("0.0001")

BASE_HASH_POWER = Decimal("10000")
HASH_GROWTH_RATE = Decimal("0.001")
PRE_GAME_HALVING_MULTIPLIER = Decimal("79000")

MB_USD_RATE = Decimal("5.00")
CACHE_USD_RATE = Decimal("0.42")
KWH_USD_RATE = Decimal("0.17")
BANDWIDTH_USD_RATE = Decimal("0.42")
TORRENT_USD_RATE = MB_USD_RATE

# --- IRA CONSTANTS ---
IRA_DAILY_RATE = Decimal("177.70") # 17,770% = 177.70 (decimal)
IRA_RATE_DISPLAY = "17,770%"

DEBUG_SHA_BOOST = True

TEPI2_VALUE = Decimal(str(1 * 9e16 * (math.pi**2)))
TEPI2 = f"TEЛ²_CONST_{TEPI2_VALUE:.2e}"
E2PI_VALUE = Decimal(str((9e16)**2 * math.pi))
E2PI = f"E²Л_CONST_{E2PI_VALUE:.2e}"
BLOCK_HEADER = "MM_BLOCK_HEADER_2025"

def format_large_number(n):
    n_float = float(n)
    if n_float < 1e12:
        return f"{n:,.6f}"
    powers = {
        1e12: "Trillion", 1e15: "Quadrillion", 1e18: "Quintillion",
        1e21: "Sextillion", 1e24: "Septillion", 1e27: "Octillion",
        1e30: "Nonillion", 1e33: "Decillion", 1e36: "Undecillion",
        1e39: "Duodecillion", 1e42: "Tredecillion"
    }
    scale = 1
    unit = ""
    for p, u in sorted(powers.items()):
        if n_float >= p:
            scale = p
            unit = u
        else:
            break
    scaled_n = n / Decimal(scale)
    return f"{scaled_n:,.3f} {unit}"

def overlay_formula(MB, entropy=Decimal("0.85"), resonance=Decimal("1.2"), resistance=Decimal("0.5")):
    return (MB * entropy * resonance) / resistance

def spin_coil(speed_percent):
    if GPIO_AVAILABLE:
        pwm = GPIO.PWM(MOTOR_PIN, 1000)
        pwm.start(speed_percent)
        time.sleep(5)
        pwm.stop()
    else:
        print(f"🌀 Simulated coil spin at {speed_percent:.2f}%")

def heat_resistor(duration):
    if GPIO_AVAILABLE:
        GPIO.output(RESISTOR_PIN, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(RESISTOR_PIN, GPIO.LOW)
    else:
        print(f"🔥 Simulated resistor heat for {duration:.2f} seconds")

def discharge_capacitor():
    if GPIO_AVAILABLE:
        GPIO.output(CAPACITOR_PIN, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(CAPACITOR_PIN, GPIO.LOW)
    else:
        print("⚡ Simulated capacitor discharge")

def emit_real_electricity(kWh):
    spin_coil(float(kWh) * 100)
    heat_resistor(float(kWh))
    discharge_capacitor()

def log_real_emission(wallet_id, MB, kWh, overlay):
    entry = {
        "wallet_id": wallet_id,
        "timestamp": time.time(),
        "capsule_MB": float(MB),
        "capsule_kWh": float(kWh),
        "overlay": overlay,
        "simulated": not GPIO_AVAILABLE
    }
    with open(os.path.join(TARGETDIR, "capsule_emission_log.json"), "a") as f:
        f.write(json.dumps(entry) + "\n")

# --- VH_BTC Hash Function ---
def vh_btc_hash_function(capsule_header, amp_capsule):
    sha_block = hashlib.sha256(BLOCK_HEADER.encode()).hexdigest()
    pre_image = f"{capsule_header}{sha_block}{amp_capsule}{TEPI2}{E2PI}"
    final_hash = hashlib.sha256(pre_image.encode()).hexdigest()
    return final_hash

# --- Hash Power Calculation ---
def calculate_rig_hash_power(wallet):
    permanent_hash_power = wallet.get("rig_hash_power", BASE_HASH_POWER)
    resource_bonus = wallet.get("cache_value_mb", Decimal("0")) / Decimal("1000")
    effective_hash_power = permanent_hash_power * (Decimal("1") + resource_bonus)
    return effective_hash_power.quantize(Decimal("0.000001"))

# --- Node Utility ---
def generate_node_id():
    return str(uuid.uuid4())

# --- Wallet Utilities ---
def save_wallet(wallet):
    wallet_copy = wallet.copy()
    wallet_copy.pop("sha_boost_active", None)
    for key, value in wallet_copy.items():
        if isinstance(value, Decimal):
            wallet_copy[key] = float(value)
    wallet_file = os.path.join(TARGETDIR, f"{wallet['wallet_id']}_wallet.json")
    with open(wallet_file, "w") as f:
        json.dump(wallet_copy, f, indent=4)

def _ensure_wallet_has_node(data):
    if data.get('wallet_id') == WORLD_DEBT_WALLET_ID:
        if data.get("node_id") != WORLD_DEBT_NODE_ID:
            data["node_id"] = WORLD_DEBT_NODE_ID
    elif "node_id" not in data or not data["node_id"]:
        data["node_id"] = generate_node_id()
    return data

def load_wallet(wallet_id):
    wallet_file = os.path.join(TARGETDIR, f"{wallet_id}_wallet.json")
    if not os.path.exists(wallet_file):
        return None
    with open(wallet_file, "r") as f:
        data = json.load(f)

    if "world_debt_paid_usd" not in data:
        data["world_debt_paid_usd"] = 0.0
    
    # IRA FIELDS
    if "ira_balance_usd" not in data:
        data["ira_balance_usd"] = 0.0
    if "ira_last_compounded_timestamp" not in data:
        data["ira_last_compounded_timestamp"] = time.time() 

    for key in ["capsule_value_mb", "cache_value_mb", "rig_hash_power", "real_kwh", "bandwidth_MBps", "world_debt_paid_usd", "torrent_value_mb", "ira_balance_usd"]:
        if key in data:
            data[key] = Decimal(str(data[key]))

    data["sha_boost_active"] = False
    original_node_id = data.get("node_id")
    data = _ensure_wallet_has_node(data)

    if data.get('wallet_id') == WORLD_DEBT_WALLET_ID and data.get("node_id") == WORLD_DEBT_NODE_ID and original_node_id != WORLD_DEBT_NODE_ID:
        save_wallet(data)

    return data

def create_wallet(wallet_id, rig_id=None):
    existing = load_wallet(wallet_id)
    if existing:
        return existing

    if wallet_id in [DONATION_WALLET_ID, WORLD_DEBT_WALLET_ID]:
        display_id = rig_id if rig_id else wallet_id
        print(f"🛑 Error: Wallet ID '{display_id}' is reserved for special system purposes and cannot be created here.")
        return None

    node_id = generate_node_id()
    wallet = {
        "wallet_id": wallet_id,
        "rig_id": rig_id or wallet_id,
        "capsule_value_mb": Decimal("0"),
        "cache_value_mb": Decimal("0"),
        "rig_hash_power": BASE_HASH_POWER,
        "real_kwh": Decimal("0"),
        "bandwidth_MBps": Decimal("0"),
        "torrent_value_mb": Decimal("0"),
        "node_id": node_id,
        "world_debt_paid_usd": Decimal("0"),
        "ira_balance_usd": Decimal("0"),
        "ira_last_compounded_timestamp": time.time(),
    }
    save_wallet(wallet)
    return wallet

# --- Special Wallet Initialization ---
def _initialize_special_wallets():
    if not load_wallet(DONATION_WALLET_ID):
        print(f"🛠️ Initializing Donation Wallet: {DONATION_WALLET_ID}")
        wallet = {
            "wallet_id": DONATION_WALLET_ID,
            "rig_id": "donations",
            "capsule_value_mb": Decimal("0"),
            "cache_value_mb": Decimal("0"),
            "rig_hash_power": BASE_HASH_POWER,
            "real_kwh": Decimal("0"),
            "bandwidth_MBps": Decimal("0"),
            "torrent_value_mb": Decimal("0"),
            "node_id": generate_node_id(),
            "world_debt_paid_usd": Decimal("0"),
            "ira_balance_usd": Decimal("0"),
            "ira_last_compounded_timestamp": time.time(),
        }
        save_wallet(wallet)

    if not load_wallet(WORLD_DEBT_WALLET_ID):
        print(f"🛠️ Initializing World Debt Wallet: {WORLD_DEBT_WALLET_ID}")
        wallet = {
            "wallet_id": WORLD_DEBT_WALLET_ID,
            "rig_id": "world debt fund",
            "capsule_value_mb": Decimal("0"),
            "cache_value_mb": Decimal("0"),
            "rig_hash_power": BASE_HASH_POWER,
            "real_kwh": Decimal("0"),
            "bandwidth_MBps": Decimal("0"),
            "torrent_value_mb": Decimal("0"),
            "node_id": WORLD_DEBT_NODE_ID,
            "world_debt_paid_usd": Decimal("0"),
            "ira_balance_usd": Decimal("0"),
            "ira_last_compounded_timestamp": time.time(),
        }
        save_wallet(wallet)

# --- World Debt Node Passive Value Generation ---
def world_debt_node_value_generation():
    debt_wallet = load_wallet(WORLD_DEBT_WALLET_ID)
    if not debt_wallet or debt_wallet.get('node_id') != WORLD_DEBT_NODE_ID:
        return
    mb_generated = DEBT_NODE_PASSIVE_USD_VALUE / MB_USD_RATE
    debt_wallet['capsule_value_mb'] += mb_generated
    save_wallet(debt_wallet)

# --- USD Value Calculation ---
def calculate_total_usd(wallet):
    """Calculates the total USD value of all resources *including* the IRA balance."""
    return (
        wallet.get('capsule_value_mb', Decimal("0")) * MB_USD_RATE +
        wallet.get('cache_value_mb', Decimal("0")) * CACHE_USD_RATE +
        wallet.get('real_kwh', Decimal("0")) * KWH_USD_RATE +
        wallet.get('bandwidth_MBps', Decimal("0")) * BANDWIDTH_USD_RATE +
        wallet.get('torrent_value_mb', Decimal("0")) * TORRENT_USD_RATE +
        wallet.get('ira_balance_usd', Decimal("0"))
    )

def calculate_non_ira_usd(wallet):
    """Calculates the total USD value of all resources *excluding* the IRA balance (The Deposit Pool)."""
    return (
        wallet.get('capsule_value_mb', Decimal("0")) * MB_USD_RATE +
        wallet.get('cache_value_mb', Decimal("0")) * CACHE_USD_RATE +
        wallet.get('real_kwh', Decimal("0")) * KWH_USD_RATE +
        wallet.get('bandwidth_MBps', Decimal("0")) * BANDWIDTH_USD_RATE +
        wallet.get('torrent_value_mb', Decimal("0")) * TORRENT_USD_RATE
    )

# --- Capsule Types ---
CUSTOM_REWARDS = [
    "Formula_Power", "2piE", "TE", "TE2pi", "Manierism", "Handrichism", "teЛ²", "E²Л",
    "RAM", "SDRAM", "SHA", "Nuclear", "Onshore",
    "Gigabyte", "Terabyte", "Petabyte", "PIB", "Electrism",
    "Pirate", "Torrent", "Bootleg", "Seeder", "Swarm"
]

# --- Torrent File Generator ---
def generate_torrent_file(wallet, capsule_type, reward_mb):
    torrent_data = {
        "capsule_type": capsule_type,
        "wallet_id": wallet["wallet_id"],
        "node_id": wallet.get("node_id", "N/A"),
        "reward_mb": float(reward_mb),
        "timestamp": time.time(),
        "overlay_constants": {
            "TEЛ²": TEPI2,
            "E²Л": E2PI,
            "block_header": BLOCK_HEADER
        }
    }
    filename = f"{wallet['wallet_id']}_{capsule_type}_capsule.torrent"
    path = os.path.join(BASEDIR, filename)
    with open(path, "w") as f:
        json.dump(torrent_data, f, indent=4)
    print(f"🧲 Torrent file created: {filename}")

# --- Unified Mining Loop ---
def unified_mining_loop(wallet, mining_type):
    TOTAL_YEARS = 75
    MAX_TICKS = TOTAL_YEARS * 365
    current_tick = 0

    try:
        while current_tick < MAX_TICKS:
            wallet = load_wallet(wallet['wallet_id'])
            if not wallet:
                print("⚠️ Wallet disappeared. Stopping mining.")
                break
            
            # Apply IRA compounding during mining
            compound_ira(wallet)

            world_debt_node_value_generation()

            capsule_type = random.choice(CUSTOM_REWARDS)
            if DEBUG_SHA_BOOST and current_tick == 0 and mining_type == "sha":
                capsule_type = "SHA"

            effective_hash_power = calculate_rig_hash_power(wallet)
            sha_boost_amount_added = Decimal("0")
            vh_hash = vh_btc_hash_function(capsule_type, str(effective_hash_power))

            # --- SHA Boost Logic ---
            if mining_type == "sha" and capsule_type == "SHA":
                boost_amount = wallet["rig_hash_power"] / Decimal("4")
                wallet["rig_hash_power"] += boost_amount
                sha_boost_amount_added = boost_amount
                wallet["sha_boost_active"] = True
                print(f"🌠 SHA Boost PERMANENTLY +{format_large_number(boost_amount)} H/s to Wallet: {wallet['wallet_id']}")

            # --- Reward Calculation ---
            scaling_factor = effective_hash_power / BASE_HASH_POWER

            if capsule_type == "E^2*Л":
                power_scale_factor = E2PI_VALUE / Decimal(1e30)
                base_mb_reward_roll = Decimal(random.randint(1, 15)) * power_scale_factor
            else:
                base_mb_reward_roll = Decimal(random.randint(1, 15))

            reward_mb = base_mb_reward_roll * scaling_factor * PRE_GAME_HALVING_MULTIPLIER
            reward_kwh = overlay_formula(reward_mb)
            base_bandwidth_roll = Decimal(random.randint(1, 15))
            reward_bandwidth = base_bandwidth_roll * scaling_factor * PRE_GAME_HALVING_MULTIPLIER
            reward_hash_gain = wallet["rig_hash_power"] * HASH_GROWTH_RATE

            # --- Real Electricity Emission ---
            emit_real_electricity(reward_kwh)
            log_real_emission(wallet["wallet_id"], reward_mb, reward_kwh, capsule_type)

            # --- Resource Allocation ---
            rewarded_resource = "Capsule MB"
            if mining_type == "cache":
                wallet["cache_value_mb"] += reward_mb
                wallet["capsule_value_mb"] += reward_mb
                rewarded_resource = "Cache & Capsule MB"
            else:
                wallet["capsule_value_mb"] += reward_mb

            wallet["rig_hash_power"] += reward_hash_gain
            wallet["real_kwh"] += reward_kwh
            wallet["bandwidth_MBps"] += reward_bandwidth
            wallet["sha_boost_active"] = False

            # --- Torrent Capsule Reward ---
            if capsule_type.lower() in ["pirate", "torrent", "bootleg", "seeder", "swarm"]:
                torrent_mb = reward_mb / Decimal("2")
                wallet["torrent_value_mb"] = wallet.get("torrent_value_mb", Decimal("0")) + torrent_mb
                generate_torrent_file(wallet, capsule_type, torrent_mb)
                print(f"🏴‍☠️ Torrent Payload Gained: {format_large_number(torrent_mb)} MB")

            save_wallet(wallet)

            display_permanent_hash_power = format_large_number(wallet["rig_hash_power"])
            total_usd = calculate_total_usd(wallet)

            print(f"\n--- Capsule Mined: {capsule_type} ({mining_type.upper()}) ---")
            print(f"Hash Found (VH_BTC): {vh_hash[:10]}...")
            print(f"💵 {rewarded_resource} Gained: {format_large_number(reward_mb)} MB")
            print(f"⚡ kWh Gained:     {format_large_number(reward_kwh)} kWh")
            print(f"🛰️ Bandwidth Gained: {format_large_number(reward_bandwidth)} MB/s")
            print(f"--------------------------")
            print(f"📈 H/s Gain:       {reward_hash_gain:.6f} (Passive)")
            print(f"🌠 H/s (Effective):{format_large_number(effective_hash_power)} (Includes Resource Bonus)")
            print(f"🌠 H/s (Permanent):{display_permanent_hash_power}")
            print(f"SHA Boost:        {format_large_number(sha_boost_amount_added)} (ADDED PERMANENTLY)")
            print(f"Balance MB:       {format_large_number(wallet['capsule_value_mb'])}")
            print(f"Balance Cache MB: {format_large_number(wallet['cache_value_mb'])}")
            print(f"💰 Total USD Value (Watts-backed): ${format_large_number(total_usd)}")

            current_tick += 1
            time.sleep(random.randint(5, 150))

        print(f"\n✅ Mining complete after reaching {TOTAL_YEARS} years.")

    except KeyboardInterrupt:
        print("\n⛔ Mining stopped by user.")

# --- Send and Donate Functions ---
def send_resource(wallet, resource_name):
    try:
        target_id = input(f"Enter target Wallet ID to send {resource_name.replace('_',' ')}: ").strip()

        if target_id in [DONATION_WALLET_ID, WORLD_DEBT_WALLET_ID]:
            print("🛑 Cannot send resources to these reserved wallet IDs using the general send function. Use the Donation or Debt menu.")
            return

        amt = Decimal(input("Amount to send: ").strip())
        if amt <= 0:
            print("⚠️ Enter a positive amount.")
            return

        if resource_name == "usd_value":
            # Exclude IRA from sendable USD value
            total_usd = calculate_non_ira_usd(wallet)
            if amt > total_usd:
                print(f"⚠️ Not enough USD-backed balance (excluding IRA). Max: ${format_large_number(total_usd)}")
                return
            
            # --- PROPORTIONAL DEDUCTION FOR USD SEND ---
            if total_usd <= 0:
                print("⚠️ No non-IRA assets available to back the USD send.")
                return

            proportion = amt / total_usd
            wallet['capsule_value_mb'] -= wallet['capsule_value_mb'] * proportion
            wallet['cache_value_mb'] -= wallet['cache_value_mb'] * proportion
            wallet['real_kwh'] -= wallet['real_kwh'] * proportion
            wallet['bandwidth_MBps'] -= wallet['bandwidth_MBps'] * proportion
            wallet['torrent_value_mb'] -= wallet['torrent_value_mb'] * proportion
        else:
            if wallet.get(resource_name, Decimal("0")) < amt:
                print(f"⚠️ Not enough {resource_name.replace('_',' ')} balance.")
                return
            wallet[resource_name] -= amt

        target = load_wallet(target_id) or create_wallet(target_id)
        if not target:
            return

        if resource_name == "usd_value":
            # Target receives USD as Capsule MB
            target_mb = amt / MB_USD_RATE
            target['capsule_value_mb'] += target_mb
        else:
            target[resource_name] = target.get(resource_name, Decimal("0")) + amt

        save_wallet(wallet)
        save_wallet(target)
        print(f"✅ Sent {format_large_number(amt)} {'Watts USD' if resource_name == 'usd_value' else resource_name.replace('_',' ')} from {wallet['wallet_id']} to {target_id}")

    except Exception as e:
        print(f"❌ Error: {e}")

def donate_for_hash(wallet, resource_name):
    donation_wallet = load_wallet(DONATION_WALLET_ID)
    if not donation_wallet:
        print("⚠️ Donation wallet not found.")
        return
    try:
        amt = Decimal(input(f"Amount {resource_name.replace('_',' ')} to donate: ").strip())
        if amt <= 0:
            print("⚠️ Enter a positive amount.")
            return

        if wallet.get(resource_name, Decimal("0")) < amt:
            print(f"⚠️ Not enough {resource_name.replace('_',' ')} balance.")
            return

        wallet[resource_name] -= amt
        donation_wallet[resource_name] = donation_wallet.get(resource_name, Decimal("0")) + amt

        hash_power_gain = amt
        if resource_name == "cache_value_mb":
            hash_power_gain *= PRE_GAME_HALVING_MULTIPLIER
            print(f"✨ Applied {PRE_GAME_HALVING_MULTIPLIER}x amplifier to Hash Power gain for Cache MB donation.")

        wallet["rig_hash_power"] += hash_power_gain

        save_wallet(wallet)
        save_wallet(donation_wallet)
        print(f"🙏 Donated {format_large_number(amt)} {resource_name.replace('_',' ')}.")
        print(f"🚀 Gained {format_large_number(hash_power_gain)} Hash Power!")

    except Exception as e:
        print(f"❌ Error: {e}")

# --- Wallet Selection ---
def _get_all_wallets():
    files = [f for f in os.listdir(TARGETDIR) if f.endswith("_wallet.json")]
    wallets_data = {}
    for f in files:
        wallet_id = f.replace("_wallet.json", "")
        wallets_data[wallet_id] = load_wallet(wallet_id)
    return wallets_data

def select_wallet_or_rig():
    wallets_data = _get_all_wallets()
    if not wallets_data:
        print("⚠️ No wallets/rigs found.")
        return None

    print("\nSelect a Rig/Wallet or type Wallet ID:")
    sorted_wallet_ids = sorted(wallets_data.keys(), key=lambda x: (x != WORLD_DEBT_WALLET_ID, x != DONATION_WALLET_ID, x))

    for i, wallet_id in enumerate(sorted_wallet_ids, 1):
        rig_id = wallets_data[wallet_id].get('rig_id', wallet_id)
        print(f"{i}. {rig_id} ({wallet_id})")

    choice = input("Enter number or Wallet ID: ").strip()
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(sorted_wallet_ids):
            wallet_id = sorted_wallet_ids[idx-1]
            return wallets_data.get(wallet_id)

    return wallets_data.get(choice)

def select_wallet_for_mining():
    wallets_data = _get_all_wallets()
    user_wallets_ids = [id for id in wallets_data.keys() if id not in [DONATION_WALLET_ID, WORLD_DEBT_WALLET_ID]]

    if not user_wallets_ids:
        print("⚠️ No personal wallets/rigs found. Create one first (Option 5).")
        return None

    print("\n--- Select Rig for Mining ---")
    sorted_user_wallets = sorted(user_wallets_ids)
    for i, wallet_id in enumerate(sorted_user_wallets, 1):
        rig_id = wallets_data[wallet_id].get('rig_id', wallet_id)
        print(f"{i}. {rig_id} ({wallet_id})")

    choice = input("Enter number: ").strip()
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(sorted_user_wallets):
            wallet_id = sorted_user_wallets[idx-1]
            return wallets_data.get(wallet_id)

    print("⚠️ Invalid selection.")
    return None

# --- Rig Dashboard ---
def show_rig_dashboard(wallet):
    if wallet['wallet_id'] in [WORLD_DEBT_WALLET_ID, DONATION_WALLET_ID]:
        wallet = load_wallet(wallet['wallet_id'])

    device_cache, _ = scan_device_cache_mb()
    total_usd = calculate_total_usd(wallet)
    effective_hash_power = calculate_rig_hash_power(wallet)

    print(f"\n--- Capsule Rig Dashboard — {wallet['rig_id']} ---")
    print(f"Wallet ID: {wallet['wallet_id']}")
    print(f"🌐 Node ID: {wallet.get('node_id','N/A')[:8]}...")
    print(f"🌠 Hash Power (Permanent): {format_large_number(wallet['rig_hash_power'])}")
    print(f"🚀 Hash Power (Effective): {format_large_number(effective_hash_power)} (Used for Mining Rate)")
    if wallet.get("sha_boost_active"):
        boost_calc = wallet['rig_hash_power'] / Decimal('4')
        print(f"⚡ SHA Boost ACTIVE: +{format_large_number(boost_calc)} H/s ")
    print(f"💾 Capsule MB: {format_large_number(wallet['capsule_value_mb'])}")
    print(f"📦 Cache MB: {format_large_number(wallet['cache_value_mb'])}")
    print(f"📥 Device Cache (User Folders): {device_cache:.6f} MB")
    print(f"⚡ Real kWh: {format_large_number(wallet['real_kwh'])}")
    print(f"📡 Bandwidth: {format_large_number(wallet['bandwidth_MBps'])} MB/s")
    print(f"🧲 Torrent Payloads: {format_large_number(wallet.get('torrent_value_mb', Decimal('0')))} MB")
    print(f"💰 IRA Balance ({IRA_RATE_DISPLAY} Daily): ${format_large_number(wallet.get('ira_balance_usd', Decimal('0')))}")
    print(f"💵 TOTAL WATTS USD Value: ${format_large_number(total_usd)}")
    print("-" * 40)

    if wallet['wallet_id'] == WORLD_DEBT_WALLET_ID:
        total_debt_paid_usd = calculate_total_usd(wallet)
        print(f"🌎 Total Debt Paid: ${format_large_number(total_debt_paid_usd)} (This Wallet's USD Value)")
    elif wallet['wallet_id'] != DONATION_WALLET_ID:
        print(f"🌎 World Debt Contributed: ${format_large_number(wallet['world_debt_paid_usd'])}")
    print("-" * 40)

# --- Internet Terminal Integration ---
def run_internet_terminal(wallet):
    node_id = wallet.get("node_id")
    flask_thread_started = False
    MB_USED_TOTAL = 0.0
    current_url = None

    app = Flask(__name__)

    @app.route('/')
    def render_page():
        nonlocal current_url
        if current_url:
            try:
                r = requests.get(current_url)
                content = r.text
            except Exception as e:
                content = f"<p>Could not fetch URL: {e}</p>"
        else:
            content = "<p>No URL selected. Enter a URL in the terminal search.</p>"

        template = """
        <!DOCTYPE html>
        <html lang="en">
        <head><meta charset="UTF-8"><title>Local Page Preview</title></head>
        <body>{{ content|safe }}</body>
        </html>
        """
        return render_template_string(template, content=content)

    def start_flask():
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

    def fetch_bing_results(query, max_results=5):
        nonlocal MB_USED_TOTAL
        url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
        response = requests.get(url)
        MB_USED_TOTAL += len(response.content) / (1024 * 1024)
        burned_MB = Decimal(MB_USED_TOTAL)
        
        # Proportional deduction for bandwidth/search cost
        total_non_ira = calculate_non_ira_usd(wallet)
        usd_cost = burned_MB * MB_USD_RATE
        
        if total_non_ira > 0:
            proportion = usd_cost / total_non_ira
            
            wallet['capsule_value_mb'] -= wallet['capsule_value_mb'] * proportion
            wallet['cache_value_mb'] -= wallet['cache_value_mb'] * proportion
            wallet['real_kwh'] -= wallet['real_kwh'] * proportion
            wallet['bandwidth_MBps'] -= wallet['bandwidth_MBps'] * proportion
            wallet['torrent_value_mb'] -= wallet['torrent_value_mb'] * proportion

        reward_kwh = overlay_formula(burned_MB)
        wallet['real_kwh'] += reward_kwh
        emit_real_electricity(reward_kwh)
        log_real_emission(wallet['wallet_id'], burned_MB, reward_kwh, "InternetSearch")
        save_wallet(wallet)

        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        for li in soup.find_all('li', {'class': 'b_algo'})[:max_results]:
            title_tag = li.find('h2')
            snippet_tag = li.find('p')
            link_tag = title_tag.find('a') if title_tag else None
            if title_tag:
                title = title_tag.get_text(strip=True)
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else "No snippet available."
                link = link_tag['href'] if link_tag else "No link"
                results.append({'title': title, 'snippet': snippet, 'link': link})
        return results

    print(f"\n🍫 Willy Wonka Internet Terminal 🍫")
    print(f"🔗 Node Linked: {node_id}")
    print("Type a URL to preview in local web display.")

    while True:
        query = input("\nEnter search query or URL (or 'exit'): ").strip()
        if query.lower() == 'exit':
            break

        if query.startswith("http://") or query.startswith("https://"):
            current_url = query
            if not flask_thread_started:
                threading.Thread(target=start_flask, daemon=True).start()
                flask_thread_started = True
            print(f"Opening {query} in local Flask preview...")
            webbrowser.open("http://localhost:5000/")
            continue

        capsule_type = random.choice(CUSTOM_REWARDS)
        vh_hash = vh_btc_hash_function(capsule_type, str(wallet['rig_hash_power']))
        print(f"🔍 Capsule Overlay: {capsule_type}")
        print(f"🔑 VH_BTC Hash: {vh_hash[:10]}...")

        results = fetch_bing_results(query)
        print(f"\n💾 Capsule MB Remaining: {format_large_number(wallet['capsule_value_mb'])}")
        for i, r in enumerate(results, 1):
            print(f"{i}. {r['title']}\n   {r['snippet']}\n   {r['link']}\n")

        with open(os.path.join(BASEDIR, "query_log.txt"), "a") as f:
            f.write(f"{capsule_type} | {vh_hash} | {query}\n")

        input("Press Enter for new search...")

# --- Receive Info ---
def show_receive_info(wallet):
    print("\n--- Receive Info ---")
    print(f"Wallet ID (for receiving resources): {wallet['wallet_id']}")
    print(f"Node ID (for network interactions): {wallet['node_id']}")
    print("Share these to receive transfers.")
    input("Press Enter to continue...")

# --- Device Cache Scanner ---
def scan_device_cache_mb():
    total_mb = Decimal("0.0")
    scanned_paths = []

    for root, dirs, files in os.walk("/storage/emulated/0/"):
        for name in files:
            try:
                path = os.path.join(root, name)
                size_bytes = os.path.getsize(path)
                size_mb = Decimal(size_bytes) / Decimal(1024 * 1024)
                total_mb += size_mb
                scanned_paths.append(path)
            except:
                continue

    return total_mb.quantize(Decimal("0.000001")), scanned_paths

# --- Rig Info Export (Option 14) ---
def show_rig_download_info(wallet):
    rig_info = {
        "wallet_id": wallet['wallet_id'],
        "rig_id": wallet.get('rig_id', wallet['wallet_id']),
        "node_id": wallet.get('node_id', 'N/A'),
        "capsule_MB": float(wallet.get('capsule_value_mb', Decimal("0"))),
        "cache_MB": float(wallet.get('cache_value_mb', Decimal("0"))),
        "real_kWh": float(wallet.get('real_kwh', Decimal("0"))),
        "bandwidth_MBps": float(wallet.get('bandwidth_MBps', Decimal("0"))),
        "torrent_MB": float(wallet.get('torrent_value_mb', Decimal("0"))),
        "rig_hash_power": float(wallet.get('rig_hash_power', BASE_HASH_POWER)),
        "world_debt_paid_usd": float(wallet.get('world_debt_paid_usd', Decimal("0"))),
        "ira_balance_usd": float(wallet.get('ira_balance_usd', Decimal("0"))),
        "total_usd_value": float(calculate_total_usd(wallet)),
        "timestamp": time.time(),
        "overlay_constants": {
            "TEЛ²": str(TEPI2),
            "E²Л": str(E2PI),
            "block_header": BLOCK_HEADER
        }
    }
    file_name = f"rig_info_{wallet['wallet_id']}.json"
    path = os.path.join(BASEDIR, file_name)
    with open(path, "w") as f:
        json.dump(rig_info, f, indent=4)
    print(f"✅ Rig info exported to {path}")

def enhanced_download_resource_menu(wallet):
    print("\n📥 Enhanced Resource Export")
    print("Select resource to export:")
    print("  1. Capsule MB")
    print("  2. Cache MB")
    print("  3. Real kWh")
    print("  4. Bandwidth MBps")
    print("  5. Torrent MB")
    print("  6. IRA USD")
    print("  7. Watts USD (calculated)")
    print("  8. Cancel")
    choice = input("Enter option: ").strip()

    resource_map = {
        "1": "capsule_value_mb",
        "2": "cache_value_mb",
        "3": "real_kwh",
        "4": "bandwidth_MBps",
        "5": "torrent_value_mb",
        "6": "ira_balance_usd",
        "7": "usd_value"
    }

    if choice == "8":
        print("🛑 Cancelled.")
        return

    resource_key = resource_map.get(choice)
    if not resource_key:
        print("⚠️ Invalid selection.")
        return

    # Ask how much to export
    try:
        amt_str = input(f"\nEnter amount of {resource_key.replace('_',' ')} to export: ").strip()
        amt = Decimal(amt_str)
        if amt <= 0:
            print("⚠️ Must be greater than zero.")
            return
    except:
        print("❌ Invalid number format.")
        return

    # Check balance
    if resource_key == "usd_value":
        available = calculate_total_usd(wallet)
    else:
        available = wallet.get(resource_key, Decimal("0"))

    if amt > available:
        print(f"⚠️ Not enough balance. Max available: {format_large_number(available)}")
        return

    # Ask file format
    print("\nChoose file format:")
    print("  1. .json")
    print("  2. .txt")
    print("  3. .torrent")
    print("  4. .capsule")
    format_choice = input("Enter format option: ").strip()

    format_map = {
        "1": "json",
        "2": "txt",
        "3": "torrent",
        "4": "capsule"
    }

    file_ext = format_map.get(format_choice)
    if not file_ext:
        print("⚠️ Invalid format.")
        return

    # Prepare export data
    export_data = {
        "wallet_id": wallet['wallet_id'],
        "rig_id": wallet.get('rig_id', wallet['wallet_id']),
        "node_id": wallet.get('node_id', 'N/A'),
        "resource": resource_key,
        "amount": float(amt),
        "timestamp": time.time(),
        "overlay_constants": {
            "TEЛ²": TEPI2,
            "E²Л": E2PI,
            "block_header": BLOCK_HEADER
        }
    }

    filename = f"{wallet['wallet_id']}_{resource_key}_{amt}_{file_ext}.{file_ext}"
    path = os.path.join(BASEDIR, filename)

    # Write file
    try:
        if file_ext == "json":
            with open(path, "w") as f:
                json.dump(export_data, f, indent=4)
        elif file_ext == "txt":
            with open(path, "w") as f:
                for k, v in export_data.items():
                    f.write(f"{k}: {v}\n")
        else:
            with open(path, "w") as f:
                f.write(json.dumps(export_data))

        print(f"\n✅ Exported {resource_key.replace('_',' ')} to:")
        print(f"   {path}")
    except Exception as e:
        print(f"❌ Error writing file: {e}")

# --- World Debt Payment Plan (Option 15) ---
def show_world_debt_payment_menu(wallet):
    print("\n🌎 World Debt Payment Plan 🌎")
    print(f"Your Wallet ID: {wallet['wallet_id']}")
    print(f"Your Node ID: {wallet['node_id']}")
    print(f"Debt Date: {WORLD_DEBT_DATE}")
    print("-" * 40)

    # Exclude IRA from available USD to contribute to debt
    available_usd_for_deposit = calculate_non_ira_usd(wallet) 
    paid = wallet.get("world_debt_paid_usd", Decimal("0"))
    remaining = INITIAL_WORLD_DEBT_USD - paid

    print(f"💰 Your Available Watts USD: ${format_large_number(available_usd_for_deposit)}")
    print(f"🌍 Your Debt Paid:       ${format_large_number(paid)}")
    print(f"🌍 Remaining Global Debt: ${format_large_number(remaining)}")
    print("-" * 40)

    print("Would you like to contribute Watts USD to the World Debt Wallet?")
    print("This will symbolically reduce global debt and log your node as a contributor.")
    choice = input("Type YES to proceed, or press Enter to cancel: ").strip()

    if choice != "YES":
        print("🛑 Cancelled.")
        return

    print("💡 Enter amount like 10.0 or 42.50 — no commas, no $ symbol.")
    try:
        amt_str = input("Amount to contribute: ").strip()
        if "$" in amt_str or "," in amt_str:
            print("⚠️ Please enter a clean number like 10.0 — no $ or commas.")
            return
        amt = Decimal(amt_str)
    except:
        print("❌ Invalid number format.")
        return

    if amt > available_usd_for_deposit:
        print(f"⚠️ Not enough USD-backed balance (excluding IRA). Max: ${format_large_number(available_usd_for_deposit)}")
        return
    
    # --- PROPORTIONAL DEDUCTION FOR DEBT PAYMENT ---
    if available_usd_for_deposit <= 0:
        print("⚠️ No non-IRA assets available to back the debt payment.")
        return
        
    proportion = amt / available_usd_for_deposit
    
    wallet['capsule_value_mb'] -= wallet['capsule_value_mb'] * proportion
    wallet['cache_value_mb'] -= wallet['cache_value_mb'] * proportion
    wallet['real_kwh'] -= wallet['real_kwh'] * proportion
    wallet['bandwidth_MBps'] -= wallet['bandwidth_MBps'] * proportion
    wallet['torrent_value_mb'] -= wallet['torrent_value_mb'] * proportion
    
    wallet['world_debt_paid_usd'] += amt

    debt_wallet = load_wallet(WORLD_DEBT_WALLET_ID)
    if debt_wallet:
        # Debt wallet receives the payment as the primary asset
        debt_wallet['capsule_value_mb'] += amt / MB_USD_RATE 
        save_wallet(debt_wallet)

    save_wallet(wallet)
    print(f"✅ Contributed ${format_large_number(amt)} to World Debt Wallet.")
    print("🌍 Your node has been logged as a symbolic contributor to planetary debt reduction.")

# --- IRA Functions ---
def compound_ira(wallet):
    now = time.time()
    last_compound = wallet.get('ira_last_compounded_timestamp', now)
    balance = wallet.get('ira_balance_usd', Decimal("0"))

    if balance <= 0:
        wallet['ira_last_compounded_timestamp'] = now
        return False, 0

    # 86400 seconds in a day
    time_elapsed = now - last_compound
    days_elapsed = math.floor(time_elapsed / 86400)
    
    if days_elapsed <= 0:
        return False, 0 # No full day has passed

    new_balance = balance
    for _ in range(int(days_elapsed)):
        # New Balance = Old Balance * (1 + Rate)
        new_balance *= (Decimal("1") + IRA_DAILY_RATE)
    
    growth = new_balance - balance
    wallet['ira_balance_usd'] = new_balance.quantize(Decimal("0.000001"))
    wallet['ira_last_compounded_timestamp'] = last_compound + Decimal(days_elapsed * 86400)
    save_wallet(wallet)
    
    return True, days_elapsed

def calculate_time_frame_growth(initial_usd, days):
    rate = IRA_DAILY_RATE
    final_usd = initial_usd * ((Decimal("1") + rate) ** Decimal(days))
    growth_percent = (final_usd / initial_usd) - Decimal("1")
    return final_usd, growth_percent

def view_ira_growth_rates(wallet):
    
    compound_ira(wallet) # Apply compounding before calculation
    ira_balance = wallet.get('ira_balance_usd', Decimal("0"))
    
    print("\n--- 📈 IRA Growth Projections (17,770% Daily) ---")
    print(f"Current IRA Balance: ${format_large_number(ira_balance)}")
    print("-" * 45)
    
    if ira_balance <= 0:
        print("💡 Deposit Watts USD to see growth projections.")
        return

    # Time frames in days
    time_frames = [
        ("Daily", 1),
        ("Weekly", 7),
        ("Monthly (30 days)", 30),
        ("Yearly (365 days)", 365),
        ("10 Years (3650 days)", 3650)
    ]

    for label, days in time_frames:
        final_usd, growth_percent = calculate_time_frame_growth(ira_balance, days)
        print(f"📅 {label}:")
        print(f"   Final Balance: ${format_large_number(final_usd)}")
        print(f"   Growth Rate:   {growth_percent * 100:,.2f}%")
        print("-" * 45)

# --- COMBINED IRA Menu ---
def ira_combined_menu(wallet):
    
    # Always compound before showing the menu
    compounded, days = compound_ira(wallet)
    if compounded:
        print(f"\n🎉 IRA Compounded! {days} day(s) of 17,770% growth applied.")
    
    while True:
        wallet = load_wallet(wallet['wallet_id']) # Reload wallet to get updated balance
        if not wallet: break

        ira_balance = wallet.get('ira_balance_usd', Decimal("0"))
        # Use the new helper function for available deposit pool
        available_usd_for_deposit = calculate_non_ira_usd(wallet) 

        print("\n--- 💰 IRA (17,770% Daily) Manager ---")
        print(f"Current IRA Balance: ${format_large_number(ira_balance)}")
        print(f"Available Watts USD (for deposit): ${format_large_number(available_usd_for_deposit)}")
        print(f"Last Compound: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(wallet['ira_last_compounded_timestamp'])))}")
        print("-" * 45)
        print("  1. Deposit Watts USD into IRA")
        print("  2. Withdraw IRA Balance to Watts USD")
        print("  3. View Growth Rates (Daily, Weekly, Monthly, Yearly, 10-Year)")
        print("  4. Back to Wallet Actions")
        print("-" * 45)
        
        choice = input("Enter option: ").strip()

        if choice == "1":
            try:
                amt = Decimal(input("Amount of Watts USD to Deposit: ").strip())
                if amt <= 0: print("⚠️ Enter a positive amount."); continue

                if amt > available_usd_for_deposit:
                    print(f"⚠️ Not enough Watts USD. Max: ${format_large_number(available_usd_for_deposit)}")
                    continue
                
                # --- PROPORTIONAL DEDUCTION LOGIC ---
                if available_usd_for_deposit <= 0:
                     print("⚠️ No non-IRA assets available to back the deposit.")
                     continue
                
                proportion = amt / available_usd_for_deposit 
                
                # Deduct proportionally from all resource types based on their current value
                wallet['capsule_value_mb'] -= wallet['capsule_value_mb'] * proportion
                wallet['cache_value_mb'] -= wallet['cache_value_mb'] * proportion
                wallet['real_kwh'] -= wallet['real_kwh'] * proportion
                wallet['bandwidth_MBps'] -= wallet['bandwidth_MBps'] * proportion
                wallet['torrent_value_mb'] -= wallet['torrent_value_mb'] * proportion
                
                # Add to IRA
                wallet['ira_balance_usd'] += amt
                save_wallet(wallet)
                print(f"✅ Deposited ${format_large_number(amt)} to IRA. Non-IRA resources reduced proportionally.")

            except Exception as e:
                print(f"❌ Error during deposit: {e}")
                
        elif choice == "2":
            try:
                amt = Decimal(input("Amount to Withdraw from IRA: ").strip())
                if amt <= 0: print("⚠️ Enter a positive amount."); continue

                if amt > ira_balance:
                    print(f"⚠️ Not enough in IRA. Max: ${format_large_number(ira_balance)}")
                    continue
                
                # Deduct from IRA
                wallet['ira_balance_usd'] -= amt
                
                # REVERTING TO SIMPLE WITHDRAWAL TO PRIMARY ASSET (Capsule MB)
                mb_added = amt / MB_USD_RATE 
                wallet['capsule_value_mb'] += mb_added
                
                save_wallet(wallet)
                print(f"✅ Withdrew ${format_large_number(amt)} from IRA, added {format_large_number(mb_added)} Capsule MB.")

            except Exception as e:
                print(f"❌ Error during withdrawal: {e}")

        elif choice == "3":
            view_ira_growth_rates(wallet)
            
        elif choice == "4":
            break
        else:
            print("⚠️ Invalid option.")

# --- Wallet View Menu ---
def view_wallets_rigs_menu():
    wallet = select_wallet_or_rig()
    if wallet:
        wallet_transaction_menu(wallet)

def wallet_transaction_menu(wallet):
    while True:
        wallet = load_wallet(wallet['wallet_id'])
        if not wallet:
            break

        # Always compound IRA when entering the menu
        compound_ira(wallet) 

        show_rig_dashboard(wallet)

        print("\n--- Wallet Actions ---")
        print("  1. Send Capsule MB")
        print("  2. Send Cache MB")
        print("  3. Send kWh")
        print("  4. Send Bandwidth")
        print("  5. Send Watts USD")
        print("  6. Send Torrent MB")
        print("  ----------------------------------------")
        print("  7. Donate Capsule MB to Creator (Gain Hash Power)")
        print("  8. Donate Cache MB to Creator (Gain Hash Power)")
        print("  9. Donate kWh to Creator (Gain Hash Power)")
        print(" 10. Donate Bandwidth to Creator (Gain Hash Power)")
        print(" 11. Donate Torrent MB to Creator (Gain Hash Power)")
        print("  ----------------------------------------")
        print(" 12. View Receive Info (Wallet/Node IDs)")
        print(" 13. Download Resource to File")
        print(" 14. Everything About the Rig (Download Info)")
        print(" 15. World Debt Payment Plan 🌎")
        print("  ----------------------------------------")
        print(f" 16. IRA Management & Projections ({IRA_RATE_DISPLAY} Daily) 💰📈")
        print(" 17. Access Internet Terminal (Node-Linked) 🌐")
        print(" 18. Back to Main Menu")
        print("  ----------------------------------------")

        option = input("Enter option: ").strip()

        if option == "1":
            send_resource(wallet, "capsule_value_mb")
        elif option == "2":
            send_resource(wallet, "cache_value_mb")
        elif option == "3":
            send_resource(wallet, "real_kwh")
        elif option == "4":
            send_resource(wallet, "bandwidth_MBps")
        elif option == "5":
            send_resource(wallet, "usd_value")
        elif option == "6":
            send_resource(wallet, "torrent_value_mb")
        elif option == "7":
            donate_for_hash(wallet, "capsule_value_mb")
        elif option == "8":
            donate_for_hash(wallet, "cache_value_mb")
        elif option == "9":
            donate_for_hash(wallet, "real_kwh")
        elif option == "10":
            donate_for_hash(wallet, "bandwidth_MBps")
        elif option == "11":
            donate_for_hash(wallet, "torrent_value_mb")
        elif option == "12":
            show_receive_info(wallet)
        elif option == "13":
            enhanced_download_resource_menu(wallet)
        elif option == "14":
            show_rig_download_info(wallet)
        elif option == "15":
            if wallet['wallet_id'] in [DONATION_WALLET_ID, WORLD_DEBT_WALLET_ID]:
                print("🛑 Cannot access the World Debt Payment Plan menu from a system wallet.")
            else:
                show_world_debt_payment_menu(wallet)
        elif option == "16":
            if wallet['wallet_id'] in [DONATION_WALLET_ID, WORLD_DEBT_WALLET_ID]:
                print("🛑 System wallets cannot access IRA.")
            else:
                ira_combined_menu(wallet)
        elif option == "17":
            print(f"🌐 Launching Internet Terminal for Node: {wallet['node_id']}")
            run_internet_terminal(wallet)
        elif option == "18":
            break
        else:
            print("⚠️ Invalid option.")

# --- Mining Start ---
def start_mining(mining_type):
    wallet = select_wallet_for_mining()
    if wallet:
        print(f"Starting {mining_type.upper()} Mining for wallet {wallet['wallet_id']}...")
        unified_mining_loop(wallet, mining_type)

# --- Main Menu ---
def main_menu():
    _initialize_special_wallets()
    world_debt_node_value_generation()

    while True:
        print("\n=== Manierism Megabytes Mining Menu ===")
        print("1. Start CPU Mining (Select Rig)")
        print("2. Start Wi-Fi Mining (Select Rig)")
        print("3. Start SHA Capsule Mining (Select Rig)")
        print("4. Start Cache Mining (Select Rig)")
        print("5. Create New Rig / Wallet")
        print("6. View Wallets & Rigs / Wallet Actions")
        print("7. Exit")
        choice = input("Enter option (1-7): ").strip()

        world_debt_node_value_generation()

        if choice == "1":
            start_mining("cpu")
        elif choice == "2":
            start_mining("wifi")
        elif choice == "3":
            start_mining("sha")
        elif choice == "4":
            start_mining("cache")
        elif choice == "5":
            rig_id = input("Enter Rig ID or Wallet Name: ").strip()
            wallet_id = input("Enter Wallet ID: ").strip()
            new_wallet = create_wallet(wallet_id, rig_id)
            if new_wallet:
                print(f"✅ Created new wallet/rig: {rig_id} ({wallet_id}) with Node ID: {new_wallet['node_id']}")
        elif choice == "6":
            view_wallets_rigs_menu()
        elif choice == "7":
            print("Exiting... 👋 See you later F&F ❤️")
            break
        else:
            print("⚠️ Invalid selection.")

# --- Runtime Launch ---
if __name__ == "__main__":
    main_menu()
