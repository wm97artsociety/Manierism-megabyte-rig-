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

# --- Node Utility ---
def generate_node_id():
    """Generates a unique ID for a network node."""
    return str(uuid.uuid4())

# --- Wallet Utilities ---
def save_wallet(wallet):
    """Saves the wallet, converting Decimal objects to float for JSON."""
    wallet_copy = wallet.copy()
    for key, value in wallet_copy.items():
        if isinstance(value, Decimal):
            wallet_copy[key] = float(value)
    wallet_file = os.path.join(TARGETDIR, f"{wallet['wallet_id']}_wallet.json")
    with open(wallet_file, "w") as f:
        json.dump(wallet_copy, f, indent=4)

def _ensure_wallet_has_node(data):
    """Checks if a wallet has a 'node_id' and assigns/saves one if missing."""
    if "node_id" not in data or not data["node_id"]:
        data["node_id"] = generate_node_id()
        save_wallet(data)
        print(f"✅ Assigned new Node ID to wallet {data['wallet_id']}.")
    return data

def load_wallet(wallet_id):
    """Loads a wallet, converts fields to Decimal, and ensures Node ID."""
    wallet_file = os.path.join(TARGETDIR, f"{wallet_id}_wallet.json")
    if not os.path.exists(wallet_file):
        return None
    with open(wallet_file, "r") as f:
        data = json.load(f)
    for key in ["capsule_value_mb", "cache_value_mb", "rig_hash_power", "real_kwh", "bandwidth_MBps"]:
        if key in data:
            data[key] = Decimal(str(data[key]))
    data = _ensure_wallet_has_node(data)
    return data

def create_wallet(wallet_id, rig_id=None):
    """Creates a new wallet with initial values and unique Node ID."""
    existing = load_wallet(wallet_id)
    if existing:
        return existing
    wallet = {
        "wallet_id": wallet_id,
        "rig_id": rig_id or wallet_id,
        "capsule_value_mb": Decimal("0"),
        "cache_value_mb": Decimal("0"),
        "rig_hash_power": Decimal("10000"),
        "real_kwh": Decimal("0"),
        "bandwidth_MBps": Decimal("0"),
        "node_id": generate_node_id(),
    }
    save_wallet(wallet)
    return wallet

# Ensure donation wallet exists
if not load_wallet(DONATION_WALLET_ID):
    create_wallet(DONATION_WALLET_ID, "donations")

# --- Scan device cache ---
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
        if os.path.exists(path):
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

# --- Capsule & Mining ---
ENERGY_RATES = {
    "cpu": Decimal("0.02"),
    "sha": Decimal("0.02"),
    "cache": Decimal("0.015"),
    "wifi": Decimal("0.01"),
}

sha_boost_applied = {}

def mint_capsule(wallet, capsule_type, reward_mb, mining_type):
    reward_mb = Decimal(str(reward_mb))
    if capsule_type == "cache":
        wallet["cache_value_mb"] += reward_mb
    else:
        wallet["capsule_value_mb"] += reward_mb

    kwh_rate = ENERGY_RATES.get(mining_type, Decimal("0.02"))
    wallet["real_kwh"] += reward_mb * kwh_rate
    wallet["bandwidth_MBps"] += reward_mb * Decimal("0.01")
    wallet["rig_hash_power"] += reward_mb * Decimal("0.01")

    sha_boost = Decimal("0")
    if mining_type == "sha" and capsule_type == "sha":
        if wallet["wallet_id"] not in sha_boost_applied:
            sha_boost = wallet["rig_hash_power"] / Decimal("4")
            wallet["rig_hash_power"] += sha_boost
            sha_boost_applied[wallet["wallet_id"]] = True
            print(f"🌠 SHA Boost applied! +{sha_boost:.6f} H/s")

    save_wallet(wallet)
    metadata = {
        "capsuletype": capsule_type,
        "reward_mb": float(reward_mb),
        "real_kwh": float(wallet["real_kwh"]),
        "sha_boost": float(sha_boost)
    }
    return metadata

def unified_mining_loop(wallet, mining_type):
    capsule_types = [
        "sha","bandwidth","electrism","manierism","handrichism",
        "gigabyte","terabyte","pib","petabyte","sdram","ram"
    ]
    try:
        while True:
            wallet = load_wallet(wallet['wallet_id'])
            if not wallet:
                print("⚠️ Wallet disappeared. Stopping mining.")
                break

            if mining_type == "cache":
                device_cache, _ = scan_device_cache_mb()
                reward_mb = Decimal(random.uniform(5, 20))
                capsule_type = "cache"
            elif mining_type == "sha":
                reward_mb = Decimal(random.uniform(2, 15))
                capsule_type = "sha"
            elif mining_type == "wifi":
                reward_mb = Decimal(random.uniform(1, 12))
                capsule_type = "bandwidth"
            else:
                reward_mb = Decimal(random.uniform(1, 10))
                capsule_type = random.choice(capsule_types)

            metadata = mint_capsule(wallet, capsule_type, reward_mb, mining_type)
            print(f"🚀 Minted Capsule: {capsule_type} | 💾 MB: {reward_mb:.6f} | "
                  f"🌠 H/s: {wallet['rig_hash_power']:.6f} | ⚡ kWh: {metadata['real_kwh']:.6f} | "
                  f"📡 Bandwidth: {wallet['bandwidth_MBps']:.6f} MB/s\n")
            time.sleep(random.randint(5, 150))
    except KeyboardInterrupt:
        print("\n⛔ Mining stopped.")

# --- Wallet Actions ---
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
        print("5. Donate Capsule MB (Gain Hash)")
        print("6. Donate Cache MB (Gain Hash)")
        print("7. Donate kWh (Gain Hash)")
        print("8. Donate Bandwidth (Gain Hash)")
        print("9. View Receive Info")
        print("10. Help / Instructions")
        print("11. Download Resource File")
        print("12. Back to Main Menu")
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
            show_help()
        elif option == "11":
            download_resource_file(wallet)
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
        if wallet.get(resource_name, 0) >= amt:
            wallet[resource_name] -= amt
            target = load_wallet(target_id)
            if not target:
                target = create_wallet(target_id)
            if resource_name not in target:
                target[resource_name] = Decimal("0")
            target[resource_name] += amt
            save_wallet(wallet)
            save_wallet(target)
            print(f"✅ Sent {amt} {resource_name.replace('_',' ')} to {target_id}")
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
        if wallet.get(resource_name, 0) >= amt:
            wallet[resource_name] -= amt
            if resource_name not in donation_wallet:
                donation_wallet[resource_name] = Decimal("0")
            donation_wallet[resource_name] += amt
            wallet["rig_hash_power"] += amt
            save_wallet(wallet)
            save_wallet(donation_wallet)
            print(f"🙏 Donated {amt}. Hash power added to your rig!")
        else:
            print(f"⚠️ Not enough {resource_name.replace('_',' ')} balance.")
    except Exception as e:
        print(f"❌ Error: {e}")

def show_receive_info(wallet):
    print("\n--- Receive Information ---")
    print(f"📥 Wallet ID: {wallet['wallet_id']}")
    print(f"🌐 Node ID: {wallet['node_id']}")
    print(f"💾 Capsule MB: {wallet['capsule_value_mb']:.6f}")
    print(f"📦 Cache MB: {wallet['cache_value_mb']:.6f}")
    print(f"⚡ Real kWh: {wallet['real_kwh']:.6f}")
    print(f"📡 Bandwidth: {wallet['bandwidth_MBps']:.6f} MB/s")

def show_help():
    print("\n--- Instructions ---")
    print("• Mining increases resources over time.")
    print("• Send/Donate options move resources and can increase hash power.")
    print("• Use Wallet ID & Node ID to receive resources.")
    print("• Download Resource File to create MB, kWh, bandwidth, or cache files.")
    print("-" * 40)

# --- Download Resource ---
def download_resource_file(wallet):
    print("\n--- Download Resource File ---")
    print("1. Capsule MB (Bin)")
    print("2. Kilowatts (JSON)")
    print("3. Bandwidth (JSON)")
    print("4. Cache (JSON)")
    print("5. Back")
    choice = input("Select resource to download: ").strip()

    resource_map = {
        "1": ("capsule_value_mb", ".bin"),
        "2": ("real_kwh", ".json"),
        "3": ("bandwidth_MBps", ".json"),
        "4": ("cache_value_mb", ".json")
    }

    if choice not in resource_map:
        return

    resource_name, ext = resource_map[choice]
    current_value = wallet.get(resource_name, Decimal("0"))

    try:
        amt = Decimal(input(f"Enter amount to download (MB, min 1): ").strip())
        if amt < 1:
            print("⚠️ Minimum download is 1 MB.")
            return
        if amt > current_value:
            print(f"⚠️ Not enough {resource_name.replace('_',' ')} in wallet.")
            return
        filename = input("Enter the name of the file to save: ").strip()
        if not filename:
            filename = f"{resource_name}_download"

        filepath = os.path.join(BASEDIR, f"{filename}{ext}")

        if ext == ".bin":
            with open(filepath, "wb") as f:
                f.write(b'\0' * int(amt * 1024 * 1024))
        else:
            data = {resource_name: float(amt)}
            with open(filepath, "w") as f:
                json.dump(data, f, indent=4)

        wallet[resource_name] -= amt
        save_wallet(wallet)
        print(f"✅ Saved {amt} MB of {resource_name.replace('_',' ')} as {filename}{ext} in {BASEDIR}")

    except Exception as e:
        print(f"❌ Error during download: {e}")

# --- Wallet / Rig Selection ---
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
            wallet_id = files[idx - 1].replace("_wallet.json", "")
            return load_wallet(wallet_id)
    return load_wallet(choice)

# --- Dashboard ---
def show_rig_dashboard(wallet):
    device_cache, _ = scan_device_cache_mb()
    print(f"\n--- Capsule Rig Dashboard — {wallet['rig_id']} ---")
    print(f"Wallet ID: {wallet['wallet_id']}")
    print(f"🌐 Node ID: {wallet.get('node_id','N/A')[:8]}...")
    print(f"🌠 Hash Power: {wallet['rig_hash_power']:.6f}")
    print(f"💾 Capsule MB: {wallet['capsule_value_mb']:.6f}")
    print(f"📦 Cache MB: {wallet['cache_value_mb']:.6f}")
    print(f"📥 Device Cache (User Folders): {device_cache:.6f} MB")
    print(f"⚡ Real kWh: {wallet['real_kwh']:.6f}")
    print(f"📡 Bandwidth: {wallet['bandwidth_MBps']:.6f} MB/s")
    print(f"💰 USD Value: ${(float(wallet['capsule_value_mb'])*0.05 + float(wallet['cache_value_mb'])*0.03):.2f}")

# --- Mining Flow ---
def start_mining(mining_type):
    wallet_id = input("Enter Wallet ID to start mining: ").strip()
    wallet = load_wallet(wallet_id)
    if wallet:
        print(f"Starting {mining_type.upper()} Mining for wallet {wallet['wallet_id']}...\n")
        unified_mining_loop(wallet, mining_type)
    else:
        print("⚠️ Wallet not found. Aborting mining.")

# --- Wallet / Rig Menu ---
def view_wallets_rigs_menu():
    wallet = select_wallet_or_rig()
    if wallet:
        wallet_transaction_menu(wallet)

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

# --- Entry Point ---
if __name__ == "__main__":
    main_menu()
