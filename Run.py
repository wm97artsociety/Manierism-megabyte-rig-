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
BASE_HASH_POWER = Decimal("10000") # The starting hash power for scaling rewards

# --- DEBUG SETTING ---
# Set to True to force the capsule type to "SHA" on the first tick of SHA mining (Option 3) 
# to immediately test the boost logic. Set to False for normal, random operation.
DEBUG_SHA_BOOST = True 
# ---------------------

# --- Node Utility ---
def generate_node_id():
    """Generates a unique ID for a network node."""
    return str(uuid.uuid4())

# --- Wallet Utilities ---
def save_wallet(wallet):
    wallet_copy = wallet.copy()
    # Remove the temporary flags before saving
    wallet_copy.pop("sha_boost_active", None)
    for key, value in wallet_copy.items():
        if isinstance(value, Decimal):
            wallet_copy[key] = float(value)
    wallet_file = os.path.join(TARGETDIR, f"{wallet['wallet_id']}_wallet.json")
    with open(wallet_file, "w") as f:
        json.dump(wallet_copy, f, indent=4)

def _ensure_wallet_has_node(data):
    if "node_id" not in data or not data["node_id"]:
        data["node_id"] = generate_node_id()
        save_wallet(data)
        print(f"✅ Assigned new Node ID to wallet {data['wallet_id']}.")
    return data

def load_wallet(wallet_id):
    wallet_file = os.path.join(TARGETDIR, f"{wallet_id}_wallet.json")
    if not os.path.exists(wallet_file):
        return None
    with open(wallet_file, "r") as f:
        data = json.load(f)
    for key in ["capsule_value_mb", "cache_value_mb", "rig_hash_power", "real_kwh", "bandwidth_MBps"]:
        if key in data:
            data[key] = Decimal(str(data[key]))
    # Add temporary SHA boost state to wallet object, not saved to file
    data["sha_boost_active"] = False 
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

# --- Device cache scan (keeping for completeness) ---
def scan_device_cache_mb(delete_after=False):
    total_cache = Decimal("0")
    all_files = []
    user_paths = [
        os.path.join(BASEDIR, "..", "Download"),
        os.path.join("/storage/emulated/0", "Download"),
        os.path.join("/storage/emulated/0", "Documents"),
        os.path.join("/storage/emulated/0", "Pictures"),
        os.path.join("/storage/emulated/0", "Movies"),
        os.path.join("/storage/emulated/0", "Music"),
    ]
    seen = set()
    for path in user_paths:
        if not os.path.exists(path):
            continue
        for root, dirs, files in os.walk(path):
            for f in files:
                file_path = os.path.join(root, f)
                if file_path in seen:
                    continue
                seen.add(file_path)
                try:
                    size_mb = Decimal(os.path.getsize(file_path)) / Decimal(1024*1024)
                    total_cache += size_mb
                    all_files.append((file_path, size_mb))
                except Exception:
                    continue
    if delete_after:
        for file_path, _ in all_files:
            try:
                os.remove(file_path)
            except Exception:
                continue
    return total_cache, all_files


# --- Mining ---
CUSTOM_REWARDS = [
    "2piE", "TE", "TE2pi", "Manierism", "Handrichism",
    "RAM", "SDRAM", "SHA", "Nuclear", "Onshore",
    "Gigabyte", "Terabyte", "Petabyte", "PIB", "Electrism"
]

def unified_mining_loop(wallet, mining_type):
    """Mining loop with Hash Power scaling and TEMPORARY SHA boost logic."""
    
    TOTAL_YEARS = 75
    MAX_TICKS = TOTAL_YEARS * 365 
    current_tick = 0
    
    # Base reward multipliers 
    BASE_HASH_GAIN_PER_MB = Decimal("0.1")

    try:
        while current_tick < MAX_TICKS:
            # Re-load wallet state to get the latest permanent hash power
            wallet = load_wallet(wallet['wallet_id'])
            if not wallet:
                print("⚠️ Wallet disappeared. Stopping mining.")
                break

            capsule_type = random.choice(CUSTOM_REWARDS)

            # --- DEBUG BLOCK: Forces SHA on first tick for easy testing ---
            if DEBUG_SHA_BOOST and current_tick == 0 and mining_type == "sha":
                capsule_type = "SHA"
            # ---------------------------------------------------------------
            
            # Start with the permanent hash power from the wallet
            current_rig_hash_power = wallet["rig_hash_power"]
            sha_boost_amount_added = Decimal("0")
            
            # --- SHA Capsule Mining TEMPORARY Boost Logic (Option 3) ---
            if mining_type == "sha" and capsule_type == "SHA":
                
                # Calculate the temporary boost amount (1/4th of the current PERMANENT hash power)
                boost_amount = wallet["rig_hash_power"] / Decimal("4")
                
                # *** IMPORTANT CHANGE: DO NOT add to wallet["rig_hash_power"] permanently ***
                # *** The base permanent rig_hash_power remains unchanged. ***
                
                # Use the boosted hash power for the CURRENT tick's reward calculation
                current_rig_hash_power += boost_amount
                sha_boost_amount_added = boost_amount
                
                # Set temporary flag for display logic (cleared before save)
                wallet["sha_boost_active"] = True
                print(f"🌠 SHA Boost +{boost_amount:.6f} H/s to Wallet: {wallet['wallet_id']}") 
            
            # --- Dynamic Rewards based on Hash Power (Using the potentially temporarily boosted H/s) ---
            
            # Scaling factor: (Current H/s / Base H/s)
            scaling_factor = current_rig_hash_power / BASE_HASH_POWER
            
            # --- REWARD CALCULATION (ALL 1-15 BASE ROLL * SCALING FACTOR) ---
            
            # 1. Capsule MB Reward: Random base (1-15) * Scaling Factor
            base_mb_reward_roll = Decimal(random.randint(1, 15))
            reward_mb = base_mb_reward_roll * scaling_factor
            
            # 2. kWh Reward: Independent Random base (1-15) * Scaling Factor
            base_kwh_roll = Decimal(random.randint(1, 15))
            reward_kwh = base_kwh_roll * scaling_factor
            
            # 3. Bandwidth Reward: Independent Random base (1-15) * Scaling Factor
            base_bandwidth_roll = Decimal(random.randint(1, 15))
            reward_bandwidth = base_bandwidth_roll * scaling_factor
            
            # Permanent Hash gain (This is the slow, permanent growth)
            reward_hash_gain = reward_mb * BASE_HASH_GAIN_PER_MB 

            # --- Apply Rewards to Permanent Wallet Balance ---
            # NOTE: Only the small, MB-derived hash gain is PERMANENTLY applied here.
            wallet["capsule_value_mb"] += reward_mb
            wallet["rig_hash_power"] += reward_hash_gain 
            wallet["real_kwh"] += reward_kwh
            wallet["bandwidth_MBps"] += reward_bandwidth
            
            # Clear temporary flag immediately after use to maintain "temporary" nature
            wallet["sha_boost_active"] = False 
            
            save_wallet(wallet)
            
            # Determine the H/s value to display (which is the boosted value)
            display_hash_power = current_rig_hash_power
            
            # PRINTING THE NEWLY EARNED REWARDS, NOT THE BALANCE
            print(f"🚀 Mined: {capsule_type} | "
                  f"💵 MB Gained: {reward_mb:.6f} | ⚡ kWh Gained: {reward_kwh:.6f} | 🛰️ Bandwidth Gained: {reward_bandwidth:.6f} MB/s | "
                  f"🌠 H/s (Current): {display_hash_power:.6f} | SHA Boost: {sha_boost_amount_added:.6f} "
                  f"| Balance MB: {wallet['capsule_value_mb']:.6f}")

            current_tick += 1
            time.sleep(random.randint(5, 150))
            
        print(f"\n✅ Mining complete after reaching {TOTAL_YEARS} years.")
        
    except KeyboardInterrupt:
        print("\n⛔ Mining stopped by user.")


# --- Wallet Transactions & Donations ---
def wallet_transaction_menu(wallet):
    while True:
        wallet = load_wallet(wallet['wallet_id'])
        if not wallet:
            break

        # Pass the wallet state to the dashboard
        show_rig_dashboard(wallet)
        print("\n--- Wallet Actions ---")
        print("1. Send Capsule MB to another Wallet")
        print("2. Send Cache MB to another Wallet")
        print("3. Send kWh to another Wallet")
        print("4. Send Bandwidth to another Wallet")
        print("5. Donate Capsule MB to Creator (Gain Hash Power)")
        print("6. Donate Cache MB to Creator (Gain Hash Power)")
        print("7. Donate kWh to Creator (Gain Hash Power)")
        print("8. Donate Bandwidth to Creator (Gain Hash Power)")
        print("9. View Receive Info (Wallet/Node IDs)")
        print("10. Download Resource to File")
        print("11. Help / Instructions")
        print("12. Back to Main Menu")
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
            donate_for_hash(wallet, "capsule_value_mb")
        elif option == "6":
            donate_for_hash(wallet, "cache_value_mb")
        elif option == "7":
            donate_for_hash(wallet, "real_kwh")
        elif option == "8":
            donate_for_hash(wallet, "bandwidth_MBps")
        elif option == "9":
            show_receive_info(wallet)
        elif option == "10":
            download_resource_menu(wallet)
        elif option == "11":
            show_help()
        elif option == "12":
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
        if wallet.get(resource_name, Decimal("0")) >= amt:
            wallet[resource_name] -= amt
            target = load_wallet(target_id) or create_wallet(target_id)
            target[resource_name] = target.get(resource_name, Decimal("0")) + amt
            save_wallet(wallet)
            save_wallet(target)
            print(f"✅ Sent {amt} {resource_name.replace('_',' ')} from {wallet['wallet_id']} to {target_id}")
        else:
            print(f"⚠️ Not enough {resource_name.replace('_',' ')} balance.")
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
        if wallet.get(resource_name, Decimal("0")) >= amt:
            wallet[resource_name] -= amt
            donation_wallet[resource_name] = donation_wallet.get(resource_name, Decimal("0")) + amt
            wallet["rig_hash_power"] += amt
            save_wallet(wallet)
            save_wallet(donation_wallet)
            print(f"🙏 Donated {amt} {resource_name.replace('_',' ')}. Hash power added!")
        else:
            print(f"⚠️ Not enough {resource_name.replace('_',' ')} balance.")
    except Exception as e:
        print(f"❌ Error: {e}")

def show_receive_info(wallet):
    print("\n--- Receive Info ---")
    print(f"📥 Wallet ID: {wallet['wallet_id']}")
    print(f"🌐 Node ID: {wallet['node_id']}")
    print(f"💾 Capsule MB: {wallet['capsule_value_mb']:.6f}")
    print(f"📦 Cache MB: {wallet['cache_value_mb']:.6f}")
    print(f"⚡ kWh: {wallet['real_kwh']:.6f}")
    print(f"📡 Bandwidth: {wallet['bandwidth_MBps']:.6f} MB/s")
    print("Share Wallet/Node IDs to receive resources.")

def show_help():
    print("\n--- Node & Wallet Instructions ---")
    print("• Send/Donate Capsule MB, Cache MB, kWh, or Bandwidth between wallets.")
    print("• Donations add Hash Power to your rig.")
    print("• Mining rewards (MB, kWh, Bandwidth) scale with your rig's hash power.")
    print("• **SHA capsules (Option 3 mining) trigger a 1/4th hash power boost.**")
    print("• Download resource to file for local storage.")
    print("-"*40)

def download_resource_menu(wallet):
    print("\n--- Download Resource ---")
    print("1. Capsule MB (.bin)")
    print("2. Cache MB (.bin)")
    print("3. kWh (.json)")
    print("4. Bandwidth (.json)")
    option = input("Select resource type to download: ").strip()

    resource_map = {
        "1": ("capsule_value_mb", "bin"),
        "2": ("cache_value_mb", "bin"),
        "3": ("real_kwh", "json"),
        "4": ("bandwidth_MBps", "json")
    }
    if option not in resource_map:
        print("⚠️ Invalid option.")
        return

    resource_name, ext = resource_map[option]
    current_value = wallet.get(resource_name, Decimal("0"))
    print(f"Available {resource_name.replace('_',' ')}: {current_value:.6f}")

    amt = Decimal(input(f"Enter amount to download (min 1 MB/unit): ").strip())
    if amt < 1 or amt > current_value:
        print("⚠️ Invalid amount.")
        return

    file_name = input("Enter file name (without extension): ").strip()
    full_path = os.path.join(BASEDIR, f"{file_name}.{ext}")

    # Deduct from wallet
    wallet[resource_name] -= amt
    save_wallet(wallet)

    # Create file
    try:
        if ext == "bin":
            with open(full_path, "wb") as f:
                f.write(os.urandom(int(amt*1024*1024)))  # exact MB
        else:
            with open(full_path, "w") as f:
                json.dump({resource_name: float(amt)}, f, indent=4)
        print(f"✅ Downloaded {amt} {resource_name.replace('_',' ')} to {full_path}")
    except Exception as e:
        print(f"❌ Failed to download: {e}")

def select_wallet_or_rig():
    files = [f for f in os.listdir(TARGETDIR) if f.endswith("_wallet.json")]
    if not files:
        print("⚠️ No wallets/rigs found.")
        return None
    print("\nSelect a Rig/Wallet or type Wallet ID:")
    for i, f in enumerate(files, 1):
        wallet_id = f.replace("_wallet.json", "")
        print(f"{i}. {wallet_id}")
    choice = input("Enter number or Wallet ID: ").strip()
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(files):
            wallet_id = files[idx-1].replace("_wallet.json", "")
            return load_wallet(wallet_id)
    return load_wallet(choice)

def show_rig_dashboard(wallet):
    device_cache, _ = scan_device_cache_mb()

    # --- UPDATED USD VALUE CALCULATION ---
    capsule_val = float(wallet['capsule_value_mb']) * 5.00
    cache_val = float(wallet['cache_value_mb']) * 0.42
    kwh_val = float(wallet['real_kwh']) * 0.17
    bandwidth_val = float(wallet['bandwidth_MBps']) * 0.42
    total_usd = capsule_val + cache_val + kwh_val + bandwidth_val
    # -------------------------------------

    print(f"\n--- Capsule Rig Dashboard — {wallet['rig_id']} ---")
    print(f"Wallet ID: {wallet['wallet_id']}")
    print(f"🌐 Node ID: {wallet.get('node_id','N/A')[:8]}...")
    print(f"🌠 Hash Power (Permanent): {wallet['rig_hash_power']:.6f}")
    if wallet.get("sha_boost_active"):
        # Calculate what 1/4th of the permanent H/s is
        # Note: This displays the *temporary* boost applied to the last mining tick
        boost_calc = wallet['rig_hash_power'] / Decimal('4') 
        print(f"⚡ SHA Boost ACTIVE: +{boost_calc:.6f} H/s ") 
    print(f"💾 Capsule MB: {wallet['capsule_value_mb']:.6f}")
    print(f"📦 Cache MB: {wallet['cache_value_mb']:.6f}")
    print(f"📥 Device Cache (User Folders): {device_cache:.6f} MB")
    print(f"⚡ Real kWh: {wallet['real_kwh']:.6f}")
    print(f"📡 Bandwidth: {wallet['bandwidth_MBps']:.6f} MB/s")
    # Display the new total USD value
    print(f"💰 USD Value: ${total_usd:.2f}")


# --- Mining Start Flow ---
def start_mining(mining_type):
    wallet_id = input("Enter Wallet ID to start mining: ").strip()
    # Attempt to load the wallet, if it doesn't exist, create it.
    wallet = load_wallet(wallet_id)
    if not wallet:
        wallet = create_wallet(wallet_id)
        
    # Start mining immediately as requested
    if wallet:
        print(f"Starting {mining_type.upper()} Mining for wallet {wallet['wallet_id']}...")
        unified_mining_loop(wallet, mining_type)
    else:
        print("⚠️ Wallet not found. Aborting mining.")

def view_wallets_rigs_menu():
    wallet = select_wallet_or_rig()
    if wallet:
        wallet_transaction_menu(wallet)
        
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

if __name__ == "__main__":
    main_menu()
