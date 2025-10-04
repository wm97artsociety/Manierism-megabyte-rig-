#!/usr/bin/env python3
import os
import time
import json
import random
import uuid
from decimal import Decimal, getcontext

# High precision
getcontext().prec = 200

# --- Paths & constants ---
BASEDIR = "/storage/emulated/0/Download/manierismmegabytes"
TARGETDIR = os.path.join(BASEDIR, "rigs")
os.makedirs(TARGETDIR, exist_ok=True)

DONATION_WALLET_ID = "WM-CPH0O7J3"
BASE_HASH_POWER = Decimal("10000") 

HASH_GROWTH_RATE = Decimal("0.001")
PRE_GAME_HALVING_MULTIPLIER = Decimal("79000")
DEBUG_SHA_BOOST = True

# --- USD BACKING RATES ---
MB_USD_RATE = Decimal("5.00")       
CACHE_USD_RATE = Decimal("0.42")    
KWH_USD_RATE = Decimal("0.17")      
BANDWIDTH_USD_RATE = Decimal("0.42")
# -------------------------------------

# --- Node Utility ---
def generate_node_id():
    return str(uuid.uuid4())

# --- Wallet Utilities ---
def save_wallet(wallet):
    """Safely saves the wallet data, converting Decimals to floats."""
    wallet_copy = wallet.copy()
    wallet_copy.pop("sha_boost_active", None)
    for key, value in wallet_copy.items():
        if isinstance(value, Decimal):
            wallet_copy[key] = float(value)
    wallet_file = os.path.join(TARGETDIR, f"{wallet['wallet_id']}_wallet.json")
    with open(wallet_file, "w") as f:
        json.dump(wallet_copy, f, indent=4)

def _ensure_wallet_has_node(data):
    """Ensures a wallet has a Node ID. ONLY saves the file if a new one is generated."""
    node_id_changed = False
    
    # Check if a Node ID is missing or empty
    if "node_id" not in data or not data["node_id"]:
        data["node_id"] = generate_node_id()
        node_id_changed = True
        
    # If we had to generate a new ID, save the wallet immediately
    if node_id_changed:
        wallet_file = os.path.join(TARGETDIR, f"{data['wallet_id']}_wallet.json")
        try:
            # Prepare data for saving (Decimal to float)
            save_data = data.copy()
            for key, value in save_data.items():
                if isinstance(value, Decimal):
                    save_data[key] = float(value)
            
            with open(wallet_file, "w") as f:
                json.dump(save_data, f, indent=4)
            print(f"✅ Assigned and saved new Node ID to wallet {data['wallet_id']} (FIXED).")
        except Exception as e:
            print(f"❌ Error saving fixed Node ID for {data['wallet_id']}: {e}")
            
    return data

def load_wallet(wallet_id):
    """Loads wallet data, converts floats to Decimals, and ensures Node ID exists."""
    wallet_file = os.path.join(TARGETDIR, f"{wallet_id}_wallet.json")
    if not os.path.exists(wallet_file):
        return None
    with open(wallet_file, "r") as f:
        data = json.load(f)
    for key in ["capsule_value_mb", "cache_value_mb", "rig_hash_power", "real_kwh", "bandwidth_MBps"]:
        if key in data:
            data[key] = Decimal(str(data[key]))
    data["sha_boost_active"] = False
    # This function only *returns* the data, and only saves if it generated a new Node ID
    data = _ensure_wallet_has_node(data) 
    return data

def create_wallet(wallet_id, rig_id=None):
    existing = load_wallet(wallet_id)
    if existing:
        return existing
    wallet = {
        "wallet_id": wallet_id,
        "rig_id": rig_id or wallet_id,
        "capsule_value_mb": Decimal("0"),
        "cache_value_mb": Decimal("0"),
        "rig_hash_power": BASE_HASH_POWER,
        "real_kwh": Decimal("0"),
        "bandwidth_MBps": Decimal("0"),
        "node_id": generate_node_id(),
    }
    save_wallet(wallet)
    return wallet

# Ensure donation wallet exists
if not load_wallet(DONATION_WALLET_ID):
    create_wallet(DONATION_WALLET_ID, "donations")

# --- Device cache scan ---
def scan_device_cache_mb(delete_after=False):
    # Simplified placeholder
    return Decimal("0"), [] 


# --- Mining ---
CUSTOM_REWARDS = [
    "2piE", "TE", "TE2pi", "Manierism", "Handrichism",
    "RAM", "SDRAM", "SHA", "Nuclear", "Onshore",
    "Gigabyte", "Terabyte", "Petabyte", "PIB", "Electrism"
]

def unified_mining_loop(wallet, mining_type):
    TOTAL_YEARS = 75
    MAX_TICKS = TOTAL_YEARS * 365
    current_tick = 0

    try:
        while current_tick < MAX_TICKS:
            # Reload the wallet to get the most recent saved data/fixes
            wallet = load_wallet(wallet['wallet_id']) 
            if not wallet:
                print("⚠️ Wallet disappeared. Stopping mining.")
                break

            capsule_type = random.choice(CUSTOM_REWARDS)
            if DEBUG_SHA_BOOST and current_tick == 0 and mining_type == "sha":
                capsule_type = "SHA"

            current_rig_hash_power = wallet["rig_hash_power"]
            sha_boost_amount_added = Decimal("0")

            # --- SHA BOOST LOGIC (PERMANENTLY SAVED) ---
            if mining_type == "sha" and capsule_type == "SHA":
                # 1. Calculate the boost amount (1/4 of current permanent power)
                boost_amount = wallet["rig_hash_power"] / Decimal("4")
                
                # 2. MAKE THE BOOST PERMANENT: Add the boost directly to the saved rig_hash_power
                wallet["rig_hash_power"] += boost_amount
                
                # 3. Update the variable used for reward calculation in this tick
                current_rig_hash_power = wallet["rig_hash_power"]
                sha_boost_amount_added = boost_amount
                
                # 4. Set active flag for dashboard and notify user
                wallet["sha_boost_active"] = True
                print(f"🌠 SHA Boost PERMANENTLY +{boost_amount:.6f} H/s to Wallet: {wallet['wallet_id']}")
            # --- END SHA BOOST LOGIC ---

            # Scaling factor uses the (potentially boosted) current_rig_hash_power
            scaling_factor = current_rig_hash_power / BASE_HASH_POWER
            base_mb_reward_roll = Decimal(random.randint(1, 15))
            reward_mb = base_mb_reward_roll * scaling_factor * PRE_GAME_HALVING_MULTIPLIER
            reward_kwh = reward_mb
            base_bandwidth_roll = Decimal(random.randint(1, 15))
            reward_bandwidth = base_bandwidth_roll * scaling_factor * PRE_GAME_HALVING_MULTIPLIER
            
            # Passive Hash Power Growth is calculated on the (potentially boosted) rig_hash_power for this tick
            reward_hash_gain = current_rig_hash_power * HASH_GROWTH_RATE

            rewarded_resource = "Capsule MB"
            if mining_type == "cache":
                wallet["cache_value_mb"] += reward_mb
                wallet["capsule_value_mb"] += reward_mb
                rewarded_resource = "Cache & Capsule MB"
            else:
                wallet["capsule_value_mb"] += reward_mb

            # Permanent H/s growth from passive gain is added here.
            wallet["rig_hash_power"] += reward_hash_gain
            wallet["real_kwh"] += reward_kwh
            wallet["bandwidth_MBps"] += reward_bandwidth
            wallet["sha_boost_active"] = False 
            save_wallet(wallet) # Save the new permanent H/s and resource gains

            # Display the new, high permanent hash power
            display_hash_power = wallet["rig_hash_power"]

            # --- PRINT REWARDS INCLUDING USD VALUE ---
            total_usd = calculate_total_usd(wallet)

            print(f"\n--- Capsule Mined: {capsule_type} ({mining_type.upper()}) ---")
            print(f"💵 {rewarded_resource} Gained: {reward_mb:.6f}")
            print(f"⚡ kWh Gained:     {reward_kwh:.6f}")
            print(f"🛰️ Bandwidth Gained: {reward_bandwidth:.6f} MB/s")
            print(f"--------------------------")
            print(f"📈 H/s Gain:       {reward_hash_gain:.6f} (Permanent)")
            print(f"🌠 H/s (Current):  {display_hash_power:.6f}")
            print(f"SHA Boost:        {sha_boost_amount_added:.6f} (ADDED PERMANENTLY)")
            print(f"Balance MB:       {wallet['capsule_value_mb']:.6f}")
            print(f"Balance Cache MB: {wallet['cache_value_mb']:.6f}")
            print(f"💰 Total USD Value (Watts-backed): ${total_usd:,.2f}")

            current_tick += 1
            time.sleep(random.randint(5, 150))

        print(f"\n✅ Mining complete after reaching {TOTAL_YEARS} years.")

    except KeyboardInterrupt:
        print("\n⛔ Mining stopped by user.")

# --- Wallet Transactions & Donations ---

def show_rig_download_info(wallet):
    """Displays comprehensive download and location information for the rig."""
    wallet_file_path = os.path.join(TARGETDIR, f"{wallet['wallet_id']}_wallet.json")
    
    print("\n--- 💾 Everything About the Rig: Download & Location Info ---")
    print(f"🚀 Rig/Wallet ID:   {wallet['rig_id']} / {wallet['wallet_id']}")
    print(f"🌐 Node ID:         {wallet.get('node_id', 'N/A')[:8]}...")
    print("-" * 55)
    print("📜 Rig Configuration File Location:")
    print(f"Path: {wallet_file_path}")
    
    try:
        file_size_kb = os.path.getsize(wallet_file_path) / 1024
        print(f"Size: {file_size_kb:.2f} KB (Current State)")
    except OSError:
        print("Size: File not accessible (Check permissions/existence)")

    print("-" * 55)
    print("📦 Base Download Directory (Manierism Megabytes):")
    print(f"Path: {BASEDIR}")
    print("-" * 55)
    print("💾 Wallet/Rig Data Directory:")
    print(f"Path: {TARGETDIR}")
    print("Note: This directory contains ALL wallet files. Keep it secure!")
    print("-" * 55)
    print("💡 Download Instructions:")
    print("To **transfer** your rig, you must copy the entire 'manierismmegabytes' folder.")
    print("-" * 55)
    input("Press Enter to continue...")

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
        print("6. Donate Capsule MB to Creator (Gain Hash Power)")
        print("7. Donate Cache MB to Creator (Gain Hash Power)")
        print("8. Donate kWh to Creator (Gain Hash Power)")
        print("9. Donate Bandwidth to Creator (Gain Hash Power)")
        print("10. View Receive Info (Wallet/Node IDs)")
        print("11. Download Resource to File")
        print("12. Everything About the Rig (Download Info)") 
        print("13. Back to Main Menu") 
        print("-"*40)
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
            show_rig_download_info(wallet)
        elif option == "13": 
            break
        else:
            print("⚠️ Invalid option.")


def send_resource(wallet, resource_name):
    try:
        target_id = input(f"Enter target Wallet ID to send {resource_name.replace('_',' ')}: ").strip()
        amt = Decimal(input("Amount to send: ").strip())
        if amt <= 0:
            print("⚠️ Enter a positive amount.")
            return

        if resource_name == "usd_value":
            total_usd = calculate_total_usd(wallet)
            if amt > total_usd:
                print(f"⚠️ Not enough USD-backed balance. Max: ${total_usd:,.2f}")
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
            # Revert sender's resources if target failed to load/create
            print("🛑 Target wallet failed to load/create. Reverting transfer.")
            if resource_name == "usd_value":
                # Proportional reversion is complex, simple error report is better than faulty math.
                pass 
            else:
                 wallet[resource_name] += amt
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
        print(f"✅ Sent {amt} {'Watts USD' if resource_name == 'usd_value' else resource_name.replace('_',' ')} from {wallet['wallet_id']} to {target_id}")
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
        print(f"🙏 Donated {amt} {resource_name.replace('_',' ')}.")
        print(f"🚀 Gained {hash_power_gain:.6f} Hash Power!")
    except Exception as e:
        print(f"❌ Error: {e}")


def calculate_total_usd(wallet):
    return (
        wallet.get('capsule_value_mb', Decimal("0")) * MB_USD_RATE +
        wallet.get('cache_value_mb', Decimal("0")) * CACHE_USD_RATE +
        wallet.get('real_kwh', Decimal("0")) * KWH_USD_RATE +
        wallet.get('bandwidth_MBps', Decimal("0")) * BANDWIDTH_USD_RATE
    )

# --- Wallet & Rig Selection ---
def select_wallet_or_rig():
    files = [f for f in os.listdir(TARGETDIR) if f.endswith("_wallet.json")]
    if not files:
        print("⚠️ No wallets/rigs found.")
        return None
    
    wallets_data = {}
    for f in files:
        wallet_id = f.replace("_wallet.json", "")
        wallets_data[wallet_id] = load_wallet(wallet_id)

    print("\nSelect a Rig/Wallet or type Wallet ID:")
    
    sorted_wallet_ids = sorted(wallets_data.keys())

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


# --- Rig & Wallet Dashboard ---
def show_rig_dashboard(wallet):
    device_cache, _ = scan_device_cache_mb()

    total_usd = calculate_total_usd(wallet)

    print(f"\n--- Capsule Rig Dashboard — {wallet['rig_id']} ---")
    print(f"Wallet ID: {wallet['wallet_id']}")
    print(f"🌐 Node ID: {wallet.get('node_id','N/A')[:8]}...")
    print(f"🌠 Hash Power (Permanent): {wallet['rig_hash_power']:.6f}") 
    print(f"💾 Capsule MB: {wallet['capsule_value_mb']:.6f}")
    print(f"📦 Cache MB: {wallet['cache_value_mb']:.6f}")
    print(f"📥 Device Cache (User Folders): {device_cache:.6f} MB")
    print(f"⚡ Real kWh: {wallet['real_kwh']:.6f}")
    print(f"📡 Bandwidth: {wallet['bandwidth_MBps']:.6f} MB/s")
    print(f"💵 WATTS USD Value: ${total_usd:,.2f}")  
    print("-"*40)


# --- Mining Start Flow ---
def start_mining(mining_type):
    wallet_id = input("Enter Wallet ID to start mining: ").strip()
    wallet = load_wallet(wallet_id) or create_wallet(wallet_id)
    if wallet:
        print(f"Starting {mining_type.upper()} Mining for wallet {wallet['wallet_id']}...")
        unified_mining_loop(wallet, mining_type)
    else:
        print("⚠️ Wallet not found. Aborting mining.")


def view_wallets_rigs_menu():
    wallet = select_wallet_or_rig()
    if wallet:
        wallet_transaction_menu(wallet)

# --- Placeholders ---
def show_receive_info(wallet):
    print("\n--- Receive Info ---")
    print(f"Wallet ID (for receiving resources): {wallet['wallet_id']}")
    print(f"Node ID (for network interactions): {wallet['node_id']}")
    print("Share these to receive transfers.")
    input("Press Enter to continue...")

def download_resource_menu(wallet):
    print("\n--- Download Resource to File ---")
    print("Functionality not fully implemented.")
    input("Press Enter to continue...")
# --------------------


# --- Main Menu ---
def main_menu():
    create_wallet(DONATION_WALLET_ID, "donations")
    while True:
        print("\n=== Manierism Megabytes Mining Menu ===")
        print("1. Start CPU Mining")
        print("2. Start Wi-Fi Mining")
        print("3. Start SHA Capsule Mining")
        print("4. Start Cache Mining")
        print("5. Create New Rig / Wallet")
        print("6. View Wallets & Rigs / Wallet Actions")
        print("7. Exit")
        choice = input("Enter option (1-7): ").strip()

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
            print("Exiting... 👋")
            break
        else:
            print("⚠️ Invalid selection.")


# --- Run Application ---
if __name__ == "__main__":
    main_menu()
