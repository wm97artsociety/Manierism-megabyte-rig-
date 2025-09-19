#!/usr/bin/env python3
import os
import time
import json
import random
from decimal import Decimal, getcontext

# High precision
getcontext().prec = 200

# --- Paths & constants ---
BASEDIR = "/storage/emulated/0"
TARGETDIR = os.path.join(BASEDIR, "Download/manierismmegabytes/rigs")
os.makedirs(TARGETDIR, exist_ok=True)

DONATION_WALLET_ID = "WM-CPH0O7J3"

# --- SHA boost tracking ---
sha_boost_applied = {}

# --- Wallet Utilities ---
def save_wallet(wallet):
    wallet_copy = wallet.copy()
    for key, value in wallet_copy.items():
        if isinstance(value, Decimal):
            wallet_copy[key] = float(value)
    wallet_file = os.path.join(TARGETDIR, f"{wallet['wallet_id']}_wallet.json")
    with open(wallet_file, "w") as f:
        json.dump(wallet_copy, f, indent=4)

def load_wallet(wallet_id):
    wallet_file = os.path.join(TARGETDIR, f"{wallet_id}_wallet.json")
    if not os.path.exists(wallet_file):
        return None
    with open(wallet_file, "r") as f:
        data = json.load(f)
    for key in ["capsule_value_mb", "cache_value_mb", "rig_hash_power", "real_kwh", "bandwidth_MBps"]:
        if key in data:
            data[key] = Decimal(data[key])
    return data

def create_wallet(wallet_id, rig_id=None):
    wallet = {
        "wallet_id": wallet_id,
        "rig_id": rig_id or wallet_id,
        "capsule_value_mb": Decimal("0"),
        "cache_value_mb": Decimal("0"),
        "rig_hash_power": Decimal("10000"),  # baseline
        "real_kwh": Decimal("0"),
        "bandwidth_MBps": Decimal("0"),
    }
    save_wallet(wallet)
    return wallet

# Ensure donation wallet exists
if not load_wallet(DONATION_WALLET_ID):
    create_wallet(DONATION_WALLET_ID, "donations")

# --- Energy rates per MB ---
ENERGY_RATES = {
    "nuclear": Decimal("0.01"),
    "solar": Decimal("0.005"),
    "onshore": Decimal("0.002"),
    "TE": Decimal("3.875"),
    "TE2π": Decimal("3.75"),
    "2πE": Decimal("3.875"),
}

# --- Capsule & Mining ---
def mint_capsule(wallet, capsule_type, reward_mb, mining_type):
    global sha_boost_applied
    reward_mb = Decimal(reward_mb)
    if capsule_type == "cache":
        wallet["cache_value_mb"] += reward_mb
    else:
        wallet["capsule_value_mb"] += reward_mb

    kwh_rate = ENERGY_RATES.get(capsule_type, Decimal("0.02"))
    added_kwh = reward_mb * kwh_rate
    wallet["real_kwh"] += added_kwh
    wallet["bandwidth_MBps"] += reward_mb * Decimal("0.01")

    hash_gain = reward_mb * Decimal("0.01")
    wallet["rig_hash_power"] += hash_gain

    sha_boost = Decimal("0")
    if mining_type == "sha" and capsule_type == "sha":
        if wallet["wallet_id"] not in sha_boost_applied:
            sha_boost = wallet["rig_hash_power"] / Decimal("4")
            wallet["rig_hash_power"] += sha_boost
            sha_boost_applied[wallet["wallet_id"]] = True
            print(f"🌠 SHA Boost applied! +{sha_boost:.6f} H/s")

    if hash_gain > 0:
        print(f"🌠 Hash Power increased by mining: +{hash_gain:.6f} H/s")

    save_wallet(wallet)
    metadata = {
        "capsuletype": capsule_type,
        "reward_mb": float(reward_mb),
        "real_kwh": float(wallet["real_kwh"]),
        "sha_boost": float(sha_boost)
    }
    return metadata

def scan_device_cache_mb(delete_after=False):
    """Scan and optionally delete cache files for hash power"""
    total_cache = Decimal("0")
    paths_to_scan = [
        os.path.join(BASEDIR, "Download"),
        os.path.join(BASEDIR, "Android/data"),
    ]
    all_files = []
    for path in paths_to_scan:
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                for f in files:
                    file_path = os.path.join(root, f)
                    if os.access(file_path, os.W_OK):
                        try:
                            size_mb = Decimal(os.path.getsize(file_path)) / Decimal(1024*1024)
                            total_cache += size_mb
                            all_files.append((file_path, size_mb))
                        except Exception:
                            continue
    if delete_after:
        for file_path, size_mb in all_files:
            try:
                os.remove(file_path)
            except Exception:
                continue
    return total_cache, all_files

def unified_mining_loop(wallet, mining_type):
    capsule_types = [
        "sha","bandwidth","electrism","manierism","handrichism",
        "gigabyte","terabyte","pib","petabyte","sdram","ram",
        "nuclear","solar","onshore","TE","TE2π","2πE","cache"
    ]
    try:
        while True:
            if mining_type == "cache":
                reward_mb, _ = scan_device_cache_mb()
                capsule_type = "cache"
            else:
                capsule_type = random.choice([c for c in capsule_types if c != "cache"])
                reward_mb = Decimal(random.uniform(1,11))

            metadata = mint_capsule(wallet, capsule_type, reward_mb, mining_type)
            print(f"🚀 Minted Capsule: {capsule_type} | 💾 MB: {reward_mb:.6f} | "
                  f"🌠 H/s: {wallet['rig_hash_power']:.6f} | ⚡ kWh: {metadata['real_kwh']:.6f} | "
                  f"📡 Bandwidth: {wallet['bandwidth_MBps']:.6f} MB/s\n")
            time.sleep(random.randint(5,150))
    except KeyboardInterrupt:
        print("\n🚪 Exiting mining mode.\n")

# --- Wallet Transactions ---
def wallet_transaction_menu(wallet):
    while True:
        show_rig_dashboard(wallet)
        print("\n1. Send MB / Hash Power")
        print("2. Receive MB / Hash Power")
        print("3. Send Cache / Receive Cache / Add Hash")
        print("4. Back to Main Menu")
        option = input("Enter option: ").strip()

        if option == "1":
            target_id = input("Enter target Wallet ID: ").strip()
            amt = Decimal(input("Amount MB to send: ").strip())
            if wallet["capsule_value_mb"] >= amt:
                wallet["capsule_value_mb"] -= amt
                target = load_wallet(target_id)
                if not target:
                    target = create_wallet(target_id)
                target["capsule_value_mb"] += amt
                save_wallet(wallet)
                save_wallet(target)
                print(f"✅ Sent {amt} MB from {wallet['wallet_id']} to {target_id}")
            else:
                print("⚠️ Not enough MB balance.")

        elif option == "2":
            print(f"📥 Your Wallet ID: {wallet['wallet_id']}")

        elif option == "3":
            device_cache, files = scan_device_cache_mb()
            total_spendable = wallet["cache_value_mb"] + device_cache
            print(f"📦 Total Spendable Cache MB (Wallet + Device): {total_spendable:.6f}")
            subopt = input("Enter 'send', 'receive', or 'addhash': ").strip().lower()
            if subopt == "send":
                target_id = input("Target Wallet ID: ").strip()
                amt = Decimal(input("Amount Cache MB to send: ").strip())
                if wallet["cache_value_mb"] >= amt:
                    wallet["cache_value_mb"] -= amt
                    target = load_wallet(target_id)
                    if not target:
                        target = create_wallet(target_id)
                    target["cache_value_mb"] += amt
                    wallet["rig_hash_power"] += amt  # hash proportional
                    save_wallet(wallet)
                    save_wallet(target)
                    print(f"✅ Sent {amt} Cache MB (+{amt} H/s) to {target_id}")
                else:
                    print("⚠️ Not enough Cache MB.")
            elif subopt == "receive":
                print(f"📥 Your Cache MB: {wallet['cache_value_mb']:.6f}")
                print("Share your Wallet ID to receive cache MB.")
            elif subopt == "addhash":
                if total_spendable == 0:
                    print("⚠️ No cache MB available to add hash power.")
                    continue
                # Use all device cache for hash
                added_hash = Decimal("0")
                for file_path, size_mb in files:
                    try:
                        os.remove(file_path)
                        added_hash += size_mb
                    except Exception:
                        continue
                wallet["rig_hash_power"] += added_hash
                print(f"🌟 Added {added_hash:.6f} H/s using device cache MB!")
                save_wallet(wallet)
            else:
                print("⚠️ Invalid option.")

        elif option == "4":
            break
        else:
            print("⚠️ Invalid option.")

# --- Wallet / Rig Selection ---
def select_wallet_or_rig():
    files = [f for f in os.listdir(TARGETDIR) if f.endswith("_wallet.json")]
    if not files:
        print("⚠️ No wallets/rigs found.")
        return None
    print("\nSelect a Rig/Wallet or type Wallet ID:")
    for i, f in enumerate(files, 1):
        wallet_id = f.replace("_wallet.json","")
        print(f"{i}. {wallet_id}")
    choice = input("Enter number or Wallet ID: ").strip()
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(files):
            wallet_id = files[idx-1].replace("_wallet.json","")
            return load_wallet(wallet_id)
    return load_wallet(choice)

def show_rig_dashboard(wallet):
    print(f"\n--- Capsule Rig Dashboard — {wallet['rig_id']} ---")
    print(f"Wallet ID: {wallet['wallet_id']}")
    print(f"🌠 Hash Power: {wallet['rig_hash_power']:.6f}")
    print(f"💾 Capsule MB: {wallet['capsule_value_mb']:.6f}")
    print(f"📦 Cache MB: {wallet['cache_value_mb']:.6f}")
    device_cache, _ = scan_device_cache_mb()
    print(f"📥 Device Cache (Deep Scan): {device_cache:.6f} MB")
    print(f"⚡ Real kWh: {wallet['real_kwh']:.6f}")
    print(f"USD Value: ${float(wallet['capsule_value_mb'])*0.05:.2f}")
    print(f"📡 Bandwidth: {wallet['bandwidth_MBps']:.6f} MB/s")
    print(f"Bandwidth USD: ${float(wallet['bandwidth_MBps'])*0.00027:.6f}")

# --- Submenus ---
def rig_mining_submenu(mining_type):
    wallet = select_wallet_or_rig()
    if wallet:
        unified_mining_loop(wallet, mining_type)

def view_wallets_rigs_menu():
    wallet = select_wallet_or_rig()
    if wallet:
        wallet_transaction_menu(wallet)

# --- Main Menu ---
def main_menu():
    while True:
        print("\n1. Start CPU Mining")
        print("2. Start Wi-Fi Mining")
        print("3. Start SHA Capsule Mining")
        print("4. Start Cache Mining")
        print("5. Create New Rig / Wallet")
        print("6. View Wallets & Rigs / Dashboard")
        print("7. Exit")
        choice = input("Enter option (1-7): ").strip()
        if choice == "1":
            rig_mining_submenu("cpu")
        elif choice == "2":
            rig_mining_submenu("wifi")
        elif choice == "3":
            rig_mining_submenu("sha")
        elif choice == "4":
            rig_mining_submenu("cache")
        elif choice == "5":
            rig_id = input("Enter Rig ID or Wallet Name: ").strip()
            wallet_id = input("Enter Wallet ID: ").strip()
            create_wallet(wallet_id, rig_id)
            print(f"✅ Created new wallet/rig: {rig_id} ({wallet_id})")
        elif choice == "6":
            view_wallets_rigs_menu()
        elif choice == "7":
            print("🚪 Exiting program...")
            break
        else:
            print("⚠️ Invalid selection.")

# --- Entry Point ---
if __name__ == "__main__":
    main_menu()
