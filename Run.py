#!/usr/bin/env python3

import os
import time
import json
import random
from decimal import Decimal, getcontext
import math

getcontext().prec = 200  # high precision

# --- Paths & Constants ---
BASEDIR = "/storage/emulated/0/Download/manierismmegabytes"
TARGETDIR = os.path.join(BASEDIR, "rigs")
os.makedirs(TARGETDIR, exist_ok=True)

DONATION_WALLET_ID = "WM-CPH0O7J3"
SHA_HASH_BOOST_FRACTION = Decimal("0.25")

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
    for key in ["capsule_value_mb", "rig_hash_power", "real_kwh", "bandwidth_MBps"]:
        if key in data:
            data[key] = Decimal(data[key])
    return data

def create_wallet(wallet_id, rig_id=None):
    wallet = {
        "wallet_id": wallet_id,
        "rig_id": rig_id or wallet_id,
        "capsule_value_mb": Decimal("0"),
        "rig_hash_power": Decimal("10000"),
        "real_kwh": Decimal("0"),
        "bandwidth_MBps": Decimal("0"),
        "sha_boosted": False  # track if SHA already applied
    }
    save_wallet(wallet)
    return wallet

# Ensure donation wallet exists
if not load_wallet(DONATION_WALLET_ID):
    create_wallet(DONATION_WALLET_ID, "donations")

# --- Conversion Rates ---
KWH_RATES = {
    "nuclear": Decimal("0.01"),
    "solar_pv": Decimal("0.005"),
    "onshore": Decimal("0.002"),
    "TE": Decimal("3"),
    "2piE^2": Decimal("3"),
    "TE2pi^2": Decimal("3.875")
}

# --- Capsule & Mining Logic ---
def mb_to_kwh(capsule_type, mb_amount):
    gamma = KWH_RATES.get(capsule_type.lower(), Decimal("0.001"))
    return mb_amount * gamma

def mint_capsule(wallet, capsule_type, reward_mb):
    # SHA mining 1/4 boost applied once
    if capsule_type.lower() == "sha" and not wallet.get("sha_boosted", False):
        wallet["rig_hash_power"] += wallet["rig_hash_power"] * SHA_HASH_BOOST_FRACTION
        wallet["sha_boosted"] = True

    wallet["capsule_value_mb"] += reward_mb
    wallet["rig_hash_power"] += reward_mb * Decimal("0.1")  # baseline scaling
    kwh_reward = mb_to_kwh(capsule_type, reward_mb)
    wallet["real_kwh"] += kwh_reward
    wallet["bandwidth_MBps"] += reward_mb * Decimal("0.0001")
    save_wallet(wallet)
    return {
        "capsuletype": capsule_type,
        "reward_mb": float(reward_mb),
        "real_kwh": float(wallet["real_kwh"])
    }

def unified_mining_loop(wallet):
    capsule_types = [
        "sha","bandwidth","electrism","manierism","handrichism",
        "gigabyte","terabyte","pib","petabyte","sdram","ram",
        "nuclear","solar_pv","onshore",
        "TE","2piE^2","TE2pi^2"
    ]
    try:
        while True:
            capsule_type = random.choice(capsule_types)
            reward_mb = Decimal(random.uniform(1,11))
            metadata = mint_capsule(wallet, capsule_type, reward_mb)
            print(f"Minted Capsule: {capsule_type} | MB: {reward_mb:.6f} | "
                  f"H/s: {wallet['rig_hash_power']:.6f} | kWh: {metadata['real_kwh']:.6f} | "
                  f"Bandwidth: {wallet['bandwidth_MBps']:.6f} MB/s")
            time.sleep(random.randint(5,150))
    except KeyboardInterrupt:
        print("\n⛔ Mining stopped.")

# --- Wallet Transactions ---
def wallet_transaction_menu(wallet):
    while True:
        show_rig_dashboard(wallet)
        print("\n1. Send MB / Hash Power")
        print("2. Receive MB / Hash Power")
        print("3. Donate MB to Creator / Add Hash")
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
                save_wallet(target)
                save_wallet(wallet)
                print(f"✅ Sent {amt} MB from {wallet['wallet_id']} to {target_id}")
            else:
                print("⚠️ Not enough MB balance.")
        elif option == "2":
            print(f"📥 Your Wallet ID: {wallet['wallet_id']}")
            print("Share this ID to receive MB / Hash Power.")
        elif option == "3":
            amt = Decimal(input("Amount MB to donate: ").strip())
            donation_wallet = load_wallet(DONATION_WALLET_ID)
            if wallet["capsule_value_mb"] >= amt and donation_wallet:
                wallet["capsule_value_mb"] -= amt
                donation_wallet["capsule_value_mb"] += amt
                wallet["rig_hash_power"] += amt * Decimal("0.1")
                wallet["real_kwh"] += amt * Decimal("0.02")
                wallet["bandwidth_MBps"] += amt * Decimal("0.0001")
                save_wallet(wallet)
                save_wallet(donation_wallet)
                print(f"🙏 Donated {amt} MB to Creator. Hash power increased by {amt*Decimal('0.1'):.6f}")
            else:
                print("⚠️ Not enough MB or donation wallet missing.")
        elif option == "4":
            break
        else:
            print("⚠️ Invalid option.")

# --- Wallet Selection ---
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
    print(f"Hash Power: {wallet['rig_hash_power']:.6f}")
    print(f"Capsule MB: {wallet['capsule_value_mb']:.6f}")
    print(f"Real kWh: {wallet['real_kwh']:.6f}")
    print(f"USD Value: ${float(wallet['capsule_value_mb'])*0.05:.2f}")
    print(f"Bandwidth: {wallet['bandwidth_MBps']:.6f} MB/s")
    print(f"Bandwidth USD: ${float(wallet['bandwidth_MBps'])*0.00027:.6f}")

# --- Mining Submenus ---
def rig_mining_submenu():
    wallet = select_wallet_or_rig()
    if wallet:
        unified_mining_loop(wallet)

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
        print("4. Create New Rig / Wallet")
        print("5. View Wallets & Rigs")
        print("6. Exit")
        choice = input("Enter option (1-6): ").strip()
        if choice == "1":
            print("Starting CPU Mining...")
            rig_mining_submenu()
        elif choice == "2":
            print("Starting Wi-Fi Mining...")
            rig_mining_submenu()
        elif choice == "3":
            print("Starting SHA Capsule Mining...")
            rig_mining_submenu()
        elif choice == "4":
            rig_id = input("Enter Rig ID or Wallet Name: ").strip()
            wallet_id = input("Enter Wallet ID: ").strip()
            create_wallet(wallet_id, rig_id)
            print(f"Created new wallet/rig: {rig_id} ({wallet_id})")
        elif choice == "5":
            view_wallets_rigs_menu()
        elif choice == "6":
            print("Exiting...")
            break
        else:
            print("⚠️ Invalid selection.")

# --- Entry Point ---
if __name__ == "__main__":
    main_menu()
