#!/usr/bin/env python3

# --- Imports ---
import os
import time
import json
import random
import uuid
import hashlib
import threading
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template_string
import webbrowser
from decimal import Decimal, getcontext
import math # ADDED for pi and power calculations

# --- Precision ---
getcontext().prec = 200

# --- Paths & Constants ---
BASEDIR = "/storage/emulated/0/Download/manierismmegabytes"
TARGETDIR = os.path.join(BASEDIR, "rigs")
os.makedirs(TARGETDIR, exist_ok=True)

# --- Wallet IDs ---
DONATION_WALLET_ID = "WM-CPH0O7J3"
WORLD_DEBT_WALLET_ID = "WD-P4Y29G7B"

# --- World Debt Constants ---
WORLD_DEBT_NODE_ID = "9efae649-eb1f-4ef0-ac97-ed4df6d2942f"
INITIAL_WORLD_DEBT_USD = Decimal("31300000000000.00")
WORLD_DEBT_DATE = "October 4th, 2025"
DEBT_NODE_PASSIVE_USD_VALUE = Decimal("0.0001")

# --- Hash Power Constants ---
BASE_HASH_POWER = Decimal("10000")
HASH_GROWTH_RATE = Decimal("0.001")
PRE_GAME_HALVING_MULTIPLIER = Decimal("79000")

# --- USD Backing Rates ---
MB_USD_RATE = Decimal("5.00")
CACHE_USD_RATE = Decimal("0.42")
KWH_USD_RATE = Decimal("0.17")
BANDWIDTH_USD_RATE = Decimal("0.42")

# --- Debug Settings ---
DEBUG_SHA_BOOST = True

# --- NEW: Symbolic Power Constants ---
# T = 1 second, E = 9e16 J, Л = pi
# Formula 1: T * E * Л^2 (teЛ²)
TEPI2_VALUE = Decimal(str(1 * 9e16 * (math.pi**2))) # ~8.88264e17 Watts
TEPI2 = f"TEЛ²_CONST_{TEPI2_VALUE:.2e}"

# Formula 2: E^2 * Л (E²Л)
E2PI_VALUE = Decimal(str((9e16)**2 * math.pi)) # ~2.54468e34 Watts (Nonillion Power)
E2PI = f"E²Л_CONST_{E2PI_VALUE:.2e}"

BLOCK_HEADER = "MM_BLOCK_HEADER_2025"

# --- NEW: Large Number Formatting Function ---
def format_large_number(n):
    """Converts a large number (Decimal) into a human-readable string (word math)."""
    n_float = float(n)
    
    if n_float < 1e12: # < Trillion
        return f"{n:,.6f}" # Standard formatting up to billions

    powers = {
        1e12: "Trillion", 1e15: "Quadrillion", 1e18: "Quintillion",
        1e21: "Sextillion", 1e24: "Septillion", 1e27: "Octillion",
        1e30: "Nonillion", 1e33: "Decillion", 1e36: "Undecillion",
        1e39: "Duodecillion", 1e42: "Tredecillion"
    }
    
    # Find the largest scale
    scale = 1
    unit = ""
    for p, u in sorted(powers.items()):
        if n_float >= p:
            scale = p
            unit = u
        else:
            break
            
    # Calculate the scaled number and return
    scaled_n = n / Decimal(scale)
    return f"{scaled_n:,.3f} {unit}"

def vh_btc_hash_function(capsule_header, amp_capsule):
    """
    Symbolic implementation of the VH_BTC hash formula.
    VH_BTC = SHA256(CapsuleHeader || SHA256(BlockHeader) || Amp_capsule || TEPI2 || E2PI)
    """
    sha_block = hashlib.sha256(BLOCK_HEADER.encode()).hexdigest()
    # UPDATED: Includes the symbolic overlays for the formulas
    pre_image = f"{capsule_header}{sha_block}{amp_capsule}{TEPI2}{E2PI}"
    final_hash = hashlib.sha256(pre_image.encode()).hexdigest()
    return final_hash

def calculate_rig_hash_power(wallet):
    """
    Calculates the rig's effective Hash Power (H/s).
    Hashpower = (Base_Hash_Power + Gains) * (1 + Resource_Bonus)
    """
    permanent_hash_power = wallet.get("rig_hash_power", BASE_HASH_POWER)
    resource_bonus = wallet.get("cache_value_mb", Decimal("0")) / Decimal("1000")
    effective_hash_power = permanent_hash_power * (Decimal("1") + resource_bonus)
    return effective_hash_power.quantize(Decimal("0.000001"))
    
# --- Node Utility ---
def generate_node_id():
    """Generates a unique ID for a network node."""
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

    for key in ["capsule_value_mb", "cache_value_mb", "rig_hash_power", "real_kwh", "bandwidth_MBps", "world_debt_paid_usd"]:
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
        "node_id": node_id,
        "world_debt_paid_usd": Decimal("0"),
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
            "node_id": generate_node_id(),
            "world_debt_paid_usd": Decimal("0"),
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
            "node_id": WORLD_DEBT_NODE_ID,
            "world_debt_paid_usd": Decimal("0"),
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
    return (
        wallet.get('capsule_value_mb', Decimal("0")) * MB_USD_RATE +
        wallet.get('cache_value_mb', Decimal("0")) * CACHE_USD_RATE +
        wallet.get('real_kwh', Decimal("0")) * KWH_USD_RATE +
        wallet.get('bandwidth_MBps', Decimal("0")) * BANDWIDTH_USD_RATE
    )

# --- World Debt Payment Menu ---
def show_world_debt_payment_menu(wallet):
    while True:
        debt_wallet = load_wallet(WORLD_DEBT_WALLET_ID)
        if not debt_wallet:
            print("⚠️ World Debt Wallet not found. Check local files.")
            break

        total_debt_paid_usd = calculate_total_usd(debt_wallet)
        remaining_debt = INITIAL_WORLD_DEBT_USD - total_debt_paid_usd
        if remaining_debt < 0:
            remaining_debt = Decimal("0")

        print("\n--- 🌎 World Debt Payment Plan ---")
        print(f"📊 Global Debt Snapshot (As of {WORLD_DEBT_DATE}):")
        print("-" * 40)
        print(f"  Total Starting Debt: ${format_large_number(INITIAL_WORLD_DEBT_USD)}")
        print(f"  Total Debt Paid:     ${format_large_number(total_debt_paid_usd)} (from all sources)")
        print(f"  Remaining Debt:      ${format_large_number(remaining_debt)}")
        print("-" * 40)
        print(f"💰 Your Total Contribution: ${format_large_number(wallet['world_debt_paid_usd'])}")
        print(f"💵 Your Current Watts USD Balance: ${format_large_number(calculate_total_usd(wallet))}")
        print("-" * 40)
        print("1. Send Watts USD to Pay World Debt")
        print("2. Back to Wallet Actions")

        option = input("Enter option: ").strip()
        if option == "1":
            contribute_to_world_debt(wallet)
        elif option == "2":
            break
        else:
            print("⚠️ Invalid option.")

def contribute_to_world_debt(wallet):
    try:
        debt_wallet = load_wallet(WORLD_DEBT_WALLET_ID)
        if not debt_wallet:
            print("⚠️ World Debt Wallet not found. Aborting contribution.")
            return

        amt = Decimal(input("Amount of Watts USD to contribute: ").strip())
        if amt <= 0:
            print("⚠️ Enter a positive amount.")
            return

        total_usd = calculate_total_usd(wallet)
        if amt > total_usd:
            print(f"⚠️ Not enough Watts USD-backed balance. Max: ${format_large_number(total_usd)}")
            return

        proportion = amt / total_usd
        wallet['capsule_value_mb'] -= wallet['capsule_value_mb'] * proportion
        wallet['cache_value_mb'] -= wallet['cache_value_mb'] * proportion
        wallet['real_kwh'] -= wallet['real_kwh'] * proportion
        wallet['bandwidth_MBps'] -= wallet['bandwidth_MBps'] * proportion

        mb_equivalent = amt / MB_USD_RATE
        debt_wallet['capsule_value_mb'] += mb_equivalent
        wallet['world_debt_paid_usd'] += amt

        save_wallet(wallet)
        save_wallet(debt_wallet)
        print(f"✅ Contributed ${format_large_number(amt)} Watts USD to the World Debt Fund.")

    except Exception as e:
        print(f"❌ Error: {e}")
        
        # --- Device Cache Scan ---
def scan_device_cache_mb(delete_after=False):
    """Simplified placeholder for scanning device cache."""
    return Decimal("0"), []

# --- Capsule Types (UPDATED) ---
CUSTOM_REWARDS = [
    "Formula_Power", "2piE", "TE", "TE2pi", "Manierism", "Handrichism", "teЛ²", "E²Л"
    "RAM",  "SDRAM", "SHA", "Nuclear", "Onshore",
    "Gigabyte", "Terabyte", "Petabyte", "PIB", "Electrism"
]

# --- Unified Mining Loop (UPDATED) ---
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

            # --- Reward Calculation (UPDATED for Formula_Power) ---
            scaling_factor = effective_hash_power / BASE_HASH_POWER
            
            # Base Reward Roll
            if capsule_type == "Formula_Power":
                # Scale the E^2*Л power (2.54e34 W) down to a symbolic MB reward.
                # Using 1e30 (Nonillion) as the base scale.
                power_scale_factor = E2PI_VALUE / Decimal(1e30) 
                base_mb_reward_roll = Decimal(random.randint(1, 15)) * power_scale_factor 
            else:
                base_mb_reward_roll = Decimal(random.randint(1, 15))
            
            reward_mb = base_mb_reward_roll * scaling_factor * PRE_GAME_HALVING_MULTIPLIER
            reward_kwh = reward_mb
            
            base_bandwidth_roll = Decimal(random.randint(1, 15))
            reward_bandwidth = base_bandwidth_roll * scaling_factor * PRE_GAME_HALVING_MULTIPLIER
            
            reward_hash_gain = wallet["rig_hash_power"] * HASH_GROWTH_RATE

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
            save_wallet(wallet)

            display_permanent_hash_power = format_large_number(wallet["rig_hash_power"])
            total_usd = calculate_total_usd(wallet)

            print(f"\n--- Capsule Mined: {capsule_type} ({mining_type.upper()}) ---")
            print(f"Hash Found (VH_BTC): {vh_hash[:10]}...")
            # UPDATED: Use format_large_number for all large displays
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
        
# --- Send and Donate Functions (UPDATED to use format_large_number in prompts) ---
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
            total_usd = calculate_total_usd(wallet)
            if amt > total_usd:
                print(f"⚠️ Not enough USD-backed balance. Max: ${format_large_number(total_usd)}")
                return
            proportion = amt / total_usd
            wallet['capsule_value_mb'] -= wallet['capsule_value_mb'] * proportion
            wallet['cache_value_mb'] -= wallet['cache_value_mb'] * proportion
            wallet['real_kwh'] -= wallet['real_kwh'] * proportion
            wallet['bandwidth_MBps'] -= wallet['bandwidth_MBps'] * proportion
        else:
            if wallet.get(resource_name, Decimal("0")) < amt:
                print(f"⚠️ Not enough {resource_name.replace('_',' ')} balance.")
                return
            wallet[resource_name] -= amt

        target = load_wallet(target_id) or create_wallet(target_id)
        if not target:
            return

        if resource_name == "usd_value":
            total_usd_target = calculate_total_usd(target)
            if total_usd_target > 0:
                factor = (total_usd_target + amt) / total_usd_target
                target['capsule_value_mb'] *= factor
                target['cache_value_mb'] *= factor
                target['real_kwh'] *= factor
                target['bandwidth_MBps'] *= factor
            else:
                target['capsule_value_mb'] += amt / MB_USD_RATE
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

# --- Wallet Selection (NO CHANGE) ---
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
    
    # --- Rig Dashboard (UPDATED to use format_large_number) ---
def show_rig_dashboard(wallet):
    if wallet['wallet_id'] in [WORLD_DEBT_WALLET_ID, DONATION_WALLET_ID]:
        wallet = load_wallet(wallet['wallet_id'])

    device_cache, _ = scan_device_cache_mb()
    total_usd = calculate_total_usd(wallet)
    effective_hash_power = calculate_rig_hash_power(wallet)

    print(f"\n--- Capsule Rig Dashboard — {wallet['rig_id']} ---")
    print(f"Wallet ID: {wallet['wallet_id']}")
    print(f"🌐 Node ID: {wallet.get('node_id','N/A')[:8]}...")
    # UPDATED: Use format_large_number
    print(f"🌠 Hash Power (Permanent): {format_large_number(wallet['rig_hash_power'])}")
    print(f"🚀 Hash Power (Effective): {format_large_number(effective_hash_power)} (Used for Mining Rate)")
    if wallet.get("sha_boost_active"):
        boost_calc = wallet['rig_hash_power'] / Decimal('4')
        print(f"⚡ SHA Boost ACTIVE: +{format_large_number(boost_calc)} H/s ")
    # UPDATED: Use format_large_number
    print(f"💾 Capsule MB: {format_large_number(wallet['capsule_value_mb'])}")
    print(f"📦 Cache MB: {format_large_number(wallet['cache_value_mb'])}")
    print(f"📥 Device Cache (User Folders): {device_cache:.6f} MB")
    print(f"⚡ Real kWh: {format_large_number(wallet['real_kwh'])}")
    print(f"📡 Bandwidth: {format_large_number(wallet['bandwidth_MBps'])} MB/s")
    print(f"💵 WATTS USD Value: ${format_large_number(total_usd)}")
    print("-" * 40)

    if wallet['wallet_id'] == WORLD_DEBT_WALLET_ID:
        total_debt_paid_usd = calculate_total_usd(wallet)
        print(f"🌎 Total Debt Paid: ${format_large_number(total_debt_paid_usd)} (This Wallet's USD Value)")
    elif wallet['wallet_id'] != DONATION_WALLET_ID:
        print(f"🌎 World Debt Contributed: ${format_large_number(wallet['world_debt_paid_usd'])}")
    print("-" * 40)

# --- Download Menu (UPDATED to use format_large_number) ---
def download_resource_menu(wallet):
    print("\n--- Download Resource to File ---")
    print("1. Capsule MB (.bin)")
    print("2. Cache MB (.bin)")
    print("3. kWh (.json)")
    print("4. Bandwidth (.json)")
    option = input("Select resource type to download: ").strip()

    resource_map = {
        "1": ("capsule_value_mb", "bin", "MB"),
        "2": ("cache_value_mb", "bin", "MB"),
        "3": ("real_kwh", "json", "kWh"),
        "4": ("bandwidth_MBps", "json", "MB/s")
    }

    if option not in resource_map:
        print("⚠️ Invalid option.")
        return

    resource_name, ext, unit_name = resource_map[option]
    current_value = wallet.get(resource_name, Decimal("0"))

    print(f"Available {resource_name.replace('_',' ')}: {format_large_number(current_value)} {unit_name}")
    amt = Decimal(input(f"Enter amount to download (min 1 {unit_name}): ").strip())

    if amt < 1 or amt > current_value:
        print(f"⚠️ Invalid amount. Please enter a value between 1 and {format_large_number(current_value)} {unit_name}.")
        return

    file_name = input("Enter file name (without extension): ").strip()
    full_path = os.path.join(BASEDIR, f"{file_name}.{ext}")

    wallet[resource_name] -= amt
    save_wallet(wallet)

    try:
        if ext == "bin":
            with open(full_path, "wb") as f:
                write_size = min(int(amt * 1024 * 1024), 1024 * 1024 * 1024)
                f.write(os.urandom(write_size))
        else:
            with open(full_path, "w") as f:
                json.dump({resource_name: float(amt)}, f, indent=4)

        print(f"✅ Downloaded {format_large_number(amt)} {resource_name.replace('_',' ')} to {full_path}")

    except Exception as e:
        print(f"❌ Failed to download: {e}")

# --- Receive Info ---
def show_receive_info(wallet):
    print("\n--- Receive Info ---")
    print(f"Wallet ID (for receiving resources): {wallet['wallet_id']}")
    print(f"Node ID (for network interactions): {wallet['node_id']}")
    print("Share these to receive transfers.")
    input("Press Enter to continue...")

# --- Internet Terminal Integration (UPDATED to use format_large_number) ---
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
        wallet['capsule_value_mb'] -= Decimal(MB_USED_TOTAL)
        if wallet['capsule_value_mb'] < 0:
            wallet['capsule_value_mb'] = Decimal("0")
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
        
# --- Wallet Transaction Menu (NO CHANGE in logic, just display updates in sub-functions) ---
def wallet_transaction_menu(wallet):
    while True:
        wallet = load_wallet(wallet['wallet_id'])
        if not wallet:
            break

        show_rig_dashboard(wallet)
        print("\n--- Wallet Actions ---")
        print("1. Send Capsule MB")
        print("2. Send Cache MB")
        print("3. Send kWh")
        print("4. Send Bandwidth")
        print("5. Send Watts USD")
        print("-" * 40)
        print("6. Donate Capsule MB to Creator (Gain Hash Power)")
        print("7. Donate Cache MB to Creator (Gain Hash Power)")
        print("8. Donate kWh to Creator (Gain Hash Power)")
        print("9. Donate Bandwidth to Creator (Gain Hash Power)")
        print("-" * 40)
        print("10. View Receive Info (Wallet/Node IDs)")
        print("11. Download Resource to File")
        print("12. Everything About the Rig (Download Info)")
        print("13. World Debt Payment Plan 🌎")
        print("14. Back to Main Menu")
        print("15. Access Internet Terminal (Node-Linked)")
        print("-" * 40)
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
            donate_for_hash(wallet, "capsule_value_mb")
        elif option == "7":
            donate_for_hash(wallet, "cache_value_mb")
        elif option == "8":
            donate_for_hash(wallet, "real_kwh")
        elif option == "9":
            donate_for_hash(wallet, "bandwidth_MBps")
        elif option == "10":
            show_receive_info(wallet)
        elif option == "11":
            download_resource_menu(wallet)
        elif option == "12":
             # Assuming you have a show_rig_download_info function, if not, this will error.
             # I'll include a placeholder for it since it was in your menu but not defined.
             print("🚨 Placeholder: Rig download info not yet implemented.")
             # show_rig_download_info(wallet)
        elif option == "13":
            if wallet['wallet_id'] in [DONATION_WALLET_ID, WORLD_DEBT_WALLET_ID]:
                print("🛑 Cannot access the World Debt Payment Plan menu from a system wallet.")
            else:
                show_world_debt_payment_menu(wallet)
        elif option == "14":
            break
        elif option == "15":
            print(f"🌐 Launching Internet Terminal for Node: {wallet['node_id']}")
            run_internet_terminal(wallet)
        else:
            print("⚠️ Invalid option.")

# --- Mining Start ---
def start_mining(mining_type):
    wallet = select_wallet_for_mining()
    if wallet:
        print(f"Starting {mining_type.upper()} Mining for wallet {wallet['wallet_id']}...")
        unified_mining_loop(wallet, mining_type)

# --- Wallet View Menu ---
def view_wallets_rigs_menu():
    wallet = select_wallet_or_rig()
    if wallet:
        wallet_transaction_menu(wallet)

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
