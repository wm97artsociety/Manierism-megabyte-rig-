#!/usr/bin/env python3
"""
Capsule Blockchain Builder — Sovereign Runtime Edition
- Works on Termux / Android
- Pure JSON wallet, no cryptography
- Supports MB balance, hashpower, donations, and capsule overlays
"""

import os
import json
import time
import uuid
import random
import math
from decimal import Decimal, getcontext

# High precision for MB, π, overlay math, and hashpower
getcontext().prec = 200

# --- Directory Setup ---
BASEDIR = "/storage/emulated/0/Download/manierismmegabytes"
RIGS_DIR = os.path.join(BASEDIR, "rigs")
BUILD_DIR = "/storage/emulated/0/Download/blockchain_builds"
os.makedirs(RIGS_DIR, exist_ok=True)
os.makedirs(BUILD_DIR, exist_ok=True)

# --- Constants ---
MB_USD_RATE = Decimal("5.00")
REQUIRED_MB_TO_CREATE_CHAIN = Decimal("1000000")
DONATION_RATE_MB_TO_HS = Decimal("0.1")
BASE_HASH_POWER = Decimal("10000")
HASH_GROWTH_RATE = Decimal("0.001")
PRE_GAME_HALVING_MULTIPLIER = Decimal("79000")

SOURCE_RUNPY = "source_run.py"  # Required boilerplate for patching

capsule_type_options = [
    "Яπ", "Яπ2", "E²Л", "TEЛ²", "Капсула", "Энергия", "Резонанс", "Свет", "Тьма", "Волна"
]

capsule_formula_profiles = {
    "Яπ": {"energy": (1.0, 0.85), "bandwidth": (1.0, 0.85), "hash_modifier": 1.0},
    "Яπ2": {"energy": (1.1, 0.9), "bandwidth": (1.1, 0.9), "hash_modifier": 1.1},
    "E²Л": {"energy": (1.2, 0.9), "bandwidth": (1.2, 0.9), "hash_modifier": 1.2},
    "TEЛ²": {"energy": (1.5, 0.95), "bandwidth": (1.5, 0.95), "hash_modifier": 1.5},
    "Энергия": {"energy": (2.0, 1.0), "bandwidth": (2.0, 1.0), "hash_modifier": 2.0}
}

class Wallet:
    def __init__(self, path):
        self.path = path
        self.data = {}
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self.data = loaded
                    else:
                        print(f"⚠️ Invalid wallet format (expected dict): {self.path}")
                        self.data = {}
            except Exception as e:
                print(f"⚠️ Error loading wallet: {e}")
        self.data.setdefault("address", f"rig_wallet_{os.path.basename(path).split('.')[0]}")
        self.data.setdefault("balance_mb", self.data.get("capsule_value_mb", "0"))
        self.data.setdefault("hashpower", "0")
        self.data.setdefault("donation_mb", "0")
        self.data.setdefault("fallback_keys", [])

    def get_balance(self):
        raw = self.data.get("balance_mb") or self.data.get("capsule_value_mb") or "0"
        try:
            return Decimal(str(raw).replace(",", "").strip())
        except:
            return Decimal("0")

    def get_hashpower(self):
        raw = self.data.get("hashpower", "0")
        try:
            return Decimal(str(raw).replace(",", "").strip())
        except:
            return Decimal("0")

    def get_donation(self):
        raw = self.data.get("donation_mb", "0")
        try:
            return Decimal(str(raw).replace(",", "").strip())
        except:
            return Decimal("0")

    def get_fallback_keys(self):
        keys = self.data.get("fallback_keys", [])
        return keys if isinstance(keys, list) else []

def load_valid_wallets():
    wallets = []
    for fname in os.listdir(RIGS_DIR):
        if not fname.endswith("_wallet.json"):
            continue
        path = os.path.join(RIGS_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and ("balance_mb" in data or "capsule_value_mb" in data):
                    wallets.append(Wallet(path))
                else:
                    print(f"⚠️ Skipped (missing keys): {fname}")
        except Exception as e:
            print(f"⚠️ Skipped (decode error): {fname} → {e}")
    return wallets

def select_wallet():
    valid_wallets = load_valid_wallets()
    if not valid_wallets:
        print("⚠️ No valid wallets found.")
        return None

    print("\n📦 Available Rig Wallets:")
    for i, wallet in enumerate(valid_wallets, 1):
        mb = wallet.get_balance()
        hs = wallet.get_hashpower()
        mb_display = format_large_number(mb)
        hs_display = format_large_number(hs)
        print(f"{i}. {os.path.basename(wallet.path)} | MB: {mb_display} | H/s: {hs_display}")

    choice = input("Select wallet number: ").strip()
    try:
        index = int(choice)
        if 1 <= index <= len(valid_wallets):
            return valid_wallets[index - 1]
    except:
        print("❌ Invalid selection.")
        return None

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

def patch_fallback_keys(wallet):
    keys = wallet.get_fallback_keys()
    if not keys:
        print("\n🔑 No fallback keys found.")
        return
    print("\n🔑 Fallback Keys:")
    for i, key in enumerate(keys, 1):
        print(f"{i}. {key}")
    confirm = input("Patch fallback keys into runtime? (yes/NO): ").strip().lower()
    if confirm == "yes":
        print("✅ Fallback keys patched.")
    else:
        print("⛔ Skipped fallback patching.")

def donate_mb(wallet):
    print("\n🎁 Optional Donation:")
    print("Donate MB to increase hashpower and unlock remix rights.")
    print("1. 0 MB (skip)")
    print("2. 1000 MB")
    print("3. 5000 MB")
    print("4. 10000 MB")
    choice = input("Select donation amount: ").strip()
    donation_map = {"1": "0", "2": "1000", "3": "5000", "4": "10000"}
    donation_str = donation_map.get(choice, "0")
    donation = Decimal(donation_str)
    bal = wallet.get_balance()
    if donation > bal:
        print("❌ Insufficient MB for donation.")
        return
    new_bal = bal - donation
    wallet.data["balance_mb"] = str(new_bal)
    wallet.data["donation_mb"] = str(donation)
    with open(wallet.path, "w", encoding="utf-8") as f:
        json.dump(wallet.data, f, indent=2)
    print(f"✅ Donation confirmed: {format_large_number(donation)} MB")
    print(f"💾 New balance: {format_large_number(new_bal)} MB")

def show_crypto_payment_menu():
    print("\n💸 Blockchain Payment Options:")
    print("1. MB (Megabytes)")
    print("2. BTC (Bitcoin)")
    print("3. XMR (Monero)")
    print("4. DOGE (Dogecoin)")
    print("5. Cancel")
    choice = input("Select payment method: ").strip()
    if choice == "1":
        return "MB"
    elif choice == "2":
        print("⚡ BTC Address: 1CapsuleBTCAddressXYZ")
        return "BTC"
    elif choice == "3":
        print("⚡ XMR Address: 4CapsuleXMRAddressXYZ")
        return "XMR"
    elif choice == "4":
        print("⚡ DOGE Address: DCapsuleDOGEAddressXYZ")
        return "DOGE"
    else:
        print("❌ Payment cancelled.")
        return None

def select_entropy():
    print("\n🎛️ Select Entropy Level:")
    print("1. Stable (0.0)")
    print("2. Low (0.3)")
    print("3. Medium (0.6)")
    print("4. High (0.85)")
    print("5. Full Chaos (1.0)")
    return {"1": "0.0", "2": "0.3", "3": "0.6", "4": "0.85", "5": "1.0"}.get(input("Pick entropy level: ").strip(), "0.85")

def select_resonance():
    print("\n🎛️ Select Resonance Level:")
    print("1. Weak (0.3)")
    print("2. Moderate (0.7)")
    print("3. Strong (1.2)")
    print("4. Max Fusion (1.5+)")
    return {"1": "0.3", "2": "0.7", "3": "1.2", "4": "1.5"}.get(input("Pick resonance level: ").strip(), "1.2")

def select_resistance():
    print("\n🎛️ Select Resistance Level:")
    print("1. None (0.0)")
    print("2. Low (0.3)")
    print("3. Medium (0.6)")
    print("4. High (1.0)")
    return {"1": "0.0", "2": "0.3", "3": "0.6", "4": "1.0"}.get(input("Pick resistance level: ").strip(), "0.5")

def select_amplifier():
    print("\n⚡ Choose your hashpower amplifier:")
    print("1. Korean π (8000×)")
    print("2. Cyrillic Яπ2 (12000×)")
    print("3. NASA E²Л (16000×)")
    return {"1": "8000", "2": "12000", "3": "16000"}.get(input("Pick amplifier: ").strip(), "8000")

def select_capsule_types():
    print("\n📦 Select Capsule Types:")
    for i, name in enumerate(capsule_type_options, 1):
        print(f"{i}. {name}")
    print("0. Select ALL")
    selected = input("Enter numbers separated by commas: ").strip()
    if selected == "0":
        return ",".join(capsule_type_options)
    try:
        indices = [int(i) for i in selected.split(",") if i.strip().isdigit()]
        chosen = [capsule_type_options[i-1] for i in indices if 0 < i <= len(capsule_type_options)]
        return ",".join(chosen)
    except Exception:
        print("⚠️ Invalid selection. Using default capsule set.")
        return ",".join(capsule_type_options)

def select_virtual_cores():
    print("\n🧠 Select Virtual Core Count:")
    print("1. Single Core")
    print("2. Dual Core")
    print("3. Quad Core")
    print("4. Octa Core")
    return {"1": "1", "2": "2", "3": "4", "4": "8"}.get(input("Pick core count: ").strip(), "1")

def select_dollar_type():
    print("\n💵 Select Dollar Type:")
    print("1. USD")
    print("2. Capsule USD")
    print("3. Remix USD")
    return {"1": "USD", "2": "CapsuleUSD", "3": "RemixUSD"}.get(input("Pick dollar type: ").strip(), "CapsuleUSD")

def select_backing_scope():
    print("\n🔒 Select Backing Scope:")
    print("1. Local")
    print("2. Regional")
    print("3. Planetary")
    return {"1": "Local", "2": "Regional", "3": "Planetary"}.get(input("Pick backing scope: ").strip(), "Planetary")

def translate_energy_profile(capsule_type):
    profile = capsule_formula_profiles.get(capsule_type, {})
    return profile.get("energy", (1.0, 1.0))

def translate_bandwidth_profile(capsule_type):
    profile = capsule_formula_profiles.get(capsule_type, {})
    return profile.get("bandwidth", (1.0, 1.0))

def generate_worth_file(wallet, capsule_name, entropy, resonance, resistance, pi_boost, tick_count):
    worth_path = os.path.join(BUILD_DIR, f"{capsule_name}.worth")
    with open(worth_path, "w", encoding="utf-8") as f:
        f.write(
            f"Capsule Name: {capsule_name}\n"
            f"Wallet ID: {wallet.data.get('address')}\n"
            f"Entropy: {entropy}\n"
            f"Resonance: {resonance}\n"
            f"Resistance: {resistance}\n"
            f"π Boost: {pi_boost}\n"
            f"Tick Count: {tick_count}\n"
            f"Timestamp: {time.ctime()}\n"
        )
    print(f"📦 Metadata (.worth) created: {worth_path}")

def patch_runpy_with_settings(capsule_name, entropy, resonance, resistance, pi_boost, capsule_types, tick_count):
    if not os.path.exists(SOURCE_RUNPY):
        print(f"❌ Missing {SOURCE_RUNPY} — cannot patch.")
        return
    try:
        with open(SOURCE_RUNPY, "r", encoding="utf-8") as f:
            lines = f.readlines()
        patched_lines = []
        for line in lines:
            if "CAPSULE_NAME =" in line:
                line = f'CAPSULE_NAME = "{capsule_name}"\n'
            elif "ENTROPY =" in line:
                line = f'ENTROPY = {entropy}\n'
            elif "RESONANCE =" in line:
                line = f'RESONANCE = {resonance}\n'
            elif "RESISTANCE =" in line:
                line = f'RESISTANCE = {resistance}\n'
            elif "PI_BOOST =" in line:
                line = f'PI_BOOST = {pi_boost}\n'
            elif "CAPSULE_TYPES =" in line:
                line = f'CAPSULE_TYPES = {capsule_types}\n'
            elif "TICK_COUNT =" in line:
                line = f'TICK_COUNT = {tick_count}\n'
            patched_lines.append(line)
        patched_path = os.path.join(BUILD_DIR, f"{capsule_name}_patched_run.py")
        with open(patched_path, "w", encoding="utf-8") as f:
            f.writelines(patched_lines)
        print(f"🧬 Patched source_run.py → {patched_path}")
    except Exception as e:
        print(f"⚠️ Error patching run.py: {e}")

def patch_overlay_formula(entropy, resonance, resistance):
    def overlay_formula(MB):
        return (MB * Decimal(entropy) * Decimal(resonance)) / Decimal(resistance)
    return overlay_formula

def patch_amplifier(pi_boost):
    π = Decimal("3.1415926535")
    return Decimal(pi_boost) * π

def patch_capsule_types(capsule_types_str):
    return [t.strip() for t in capsule_types_str.split(",") if t.strip()]

def patch_tick_count(tick_str):
    try:
        return int(tick_str)
    except:
        return 50

def score_rig(entropy, resonance, resistance, pi_boost, ticks):
    entropy_score = 1 - float(entropy)
    resonance_score = float(resonance) / 2
    resistance_score = 1 - float(resistance)
    pi_score = float(pi_boost) / 10000
    tick_score = 1 / max(1, float(ticks))
    return round(entropy_score + resonance_score + resistance_score + pi_score + tick_score, 3)

def emit_capsules(wallet, overlay_formula, capsule_types, pi_boost):
    print("\n🚀 Starting Capsule Emission Loop (Ctrl+C to stop)")
    hashpower = wallet.get_hashpower()
    tick = 0
    try:
        while True:
            capsule = random.choice(capsule_types)
            base_mb = Decimal(random.randint(1, 15))
            reward_mb = base_mb * Decimal(pi_boost) * Decimal("0.01")
            reward_kwh = overlay_formula(reward_mb)

            print(f"\n🔁 Tick {tick+1}")
            print(f"📦 Capsule: {capsule}")
            print(f"💾 MB Emitted: {format_large_number(reward_mb)}")
            print(f"⚡ kWh Emitted: {reward_kwh:.6f}")
            tick += 1
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⛔ Emission loop stopped by user.")

def enforce_mb_payment(wallet):
    bal = wallet.get_balance()
    print(f"\n💰 Wallet MB balance: {format_large_number(bal)}")
    if bal < REQUIRED_MB_TO_CREATE_CHAIN:
        raise SystemExit(f"❌ Insufficient MB. Need {format_large_number(REQUIRED_MB_TO_CREATE_CHAIN)} to create blockchain.")
    
    confirm = input(f"Confirm payment of {format_large_number(REQUIRED_MB_TO_CREATE_CHAIN)} MB to proceed? (yes/NO): ").strip().lower()
    if confirm == "yes":
        new_bal = bal - REQUIRED_MB_TO_CREATE_CHAIN
        wallet.data["balance_mb"] = str(new_bal)
        with open(wallet.path, "w", encoding="utf-8") as f:
            json.dump(wallet.data, f, indent=2)
        print(f"✅ Payment confirmed. New balance: {format_large_number(new_bal)} MB")
        return True
    else:
        raise SystemExit("❌ Payment cancelled by user.")

def export_capsule_summary(capsule_name, entropy, resonance, resistance, pi_boost, capsule_types, dollar_type, backing_scope):
    summary_path = os.path.join(BUILD_DIR, f"{capsule_name}_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("🔒 Capsule Blockchain Summary\n")
        f.write(f"Name: {capsule_name}\n")
        f.write(f"Entropy: {entropy}\n")
        f.write(f"Resonance: {resonance}\n")
        f.write(f"Resistance: {resistance}\n")
        f.write(f"π Boost: {pi_boost}\n")
        f.write(f"Capsule Types: {', '.join(capsule_types)}\n")
        f.write(f"Dollar Type: {dollar_type}\n")
        f.write(f"Backing Scope: {backing_scope}\n")
        f.write(f"Timestamp: {time.ctime()}\n")
    print(f"📝 Summary exported: {summary_path}")

def cleanup_runtime():
    print("\n🧹 Runtime cleanup complete.")
    print("🔒 All overlays injected.")
    print("📦 All files stored in:", BUILD_DIR)
    print("🧠 Remix rights preserved.")
    print("✅ Sovereign runtime terminated.")

def main():
    wallet = select_wallet()
    if not wallet:
        raise SystemExit("❌ No wallet selected.")

    print("\n🚀 Capsule Blockchain Builder")
    print("🔒 Sovereign Runtime Initialized")
    print(f"Wallet: {wallet.data.get('address')}")
    print(f"MB Balance: {format_large_number(wallet.get_balance())}")
    print(f"Hashpower: {format_large_number(wallet.get_hashpower())}")

    patch_fallback_keys(wallet)
    donate_mb(wallet)

    method = show_crypto_payment_menu()
    if method != "MB":
        print("💡 External payment selected. Please confirm manually before proceeding.")
        input("Press Enter to continue after payment...")

    enforce_mb_payment(wallet)

    blockchain_name = input("\n📛 Blockchain Name: ").strip() or "UnnamedChain"
    entropy = select_entropy()
    resonance = select_resonance()
    resistance = select_resistance()
    pi_boost = select_amplifier()
    capsule_types_str = select_capsule_types()
    tick_str = "∞"  # Infinite loop override
    cores = select_virtual_cores()
    dollar_type = select_dollar_type()
    backing_scope = select_backing_scope()

    capsule_name = "_".join(capsule_types_str.split(","))
    capsule_types = patch_capsule_types(capsule_types_str)
    amplifier_value = patch_amplifier(pi_boost)
    overlay_formula = patch_overlay_formula(entropy, resonance, resistance)

    generate_worth_file(wallet, capsule_name, entropy, resonance, resistance, pi_boost, tick_str)
    patch_runpy_with_settings(capsule_name, entropy, resonance, resistance, pi_boost, capsule_types, tick_str)

    print(f"\n🧠 Sovereign Rig Score: {score_rig(entropy, resonance, resistance, pi_boost, 50)}")
    emit_capsules(wallet, overlay_formula, capsule_types, pi_boost)

    print("\n✅ Done — files are in:", BUILD_DIR)
    print(f"Rig files stored in: {RIGS_DIR}")

if __name__ == "__main__":
    main()

