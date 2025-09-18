# Manierism-megabyte-rig


🛡️ Manierism Megabyte Capsule Rig

Overview

Manierism Megabyte Capsule Rig is a blockchain-based mining platform that tracks digital rewards in terms of:

📦 Real Megabytes (MB)

📶 Real Bandwidth (MB/s)

⚡ Real Hash Power (hs) 

🔋 Real Energy (kWh)


This system models rigs with real-world parameters, including kilowatt consumption, data throughput, and incremental rig performance. Every rig is assigned a unique wallet ID, and the system is designed to run continuously for decades, modeling long-term mining efficiency.


---

🔑 Encryption Key Setup

To ensure secure capsule minting and wallet integrity, the system uses Fernet encryption. A key is generated and stored locally:

from cryptography.fernet import Fernet
import os

KEYPATH = "/storage/emulated/0/Download/capsulekey.key"

if not os.path.exists(KEYPATH):
    key = Fernet.generate_key()
    with open(KEYPATH, "wb") as f:
        f.write(key)
    print(f"[INFO] Encryption key generated at {KEYPATH}")
else:
    with open(KEYPATH, "rb") as f:
        key = f.read()
    print(f"[INFO] Encryption key loaded from {KEYPATH}")

The key is stored at:
/storage/emulated/0/Download/capsulekey.key

It is used to encrypt wallet files and capsule metadata, ensuring tamper-proof mining logic.


---

🧠 Reward Logic

Capsules are minted using runtime-valid formulas:

E_virtual = H_cpu × t × k_scale
E_real    = E_virtual / k_real

H_cpu: hash rate (hashes/sec)

t: time interval (seconds)

k_scale: scaling constant (e.g., 1/25,000)

k_real: real-world conversion factor


MB Reward System

Starting Reward Range: Each mining cycle yields a random reward between 1–11 MB.

Scaling: Rewards increase as hash power and runtime grow.

Feedback Loop: More MB → more hash power upgrades → faster MB accumulation.


Formula:

MB_reward = random.randint(1, 11) × growth_factor × (H_cpu / scaling_constant)

MB → Hash Power Donation

1 MB donated = 1 H/s added to rig hash power.

Creates direct feedback loop between community contributions and mining strength.



---

🧪 Mining Loop

Mining Rewards and Legacy:

Early rewards are small starting out (1–11 MB), but they grow significantly as rigs scale.

Rigs can be passed down to a loved one or someone you care about, allowing them to inherit your rig and continue earning rewards.


Each capsule prints:

Capsule type

MB reward (1–11 MB starting range)

Hash power added

USD/BTC value

Real kWh used

Bandwidth in MB/s


Hash Power Feedback Loop

1. Mining → earns MB (1–11 MB per tick).


2. MB can be spent to upgrade hash power.


3. MB can also be donated to the creator at 1 MB → 1 H/s.


4. More hash power → more MB → compounding growth.




---

⏳ Rig Lifetime and Max Hash Power

Starting Hash Power: 25,000 H/s

Scaled Max Hash Power (Target HS):


Target_HS = MAX_HASH / 4 ≈ 2.62503205022007E152

Mining Contribution: hash power rises with rewards and donations.

Daily MB Requirement for 75-Year Growth: ~4,566 MB/day



---

💡 Megabytes as a Foundational Technology

Market Value:

Raw MB: $0.10–$1

Processed MB: ~$5 (RAM, CDs, software)


Future Potential:

Run operating systems directly from MB storage

Power devices without traditional kilowatt plugs

Unlock full OS hash power (e.g., U.S. phone: 77 H/s → unlocked bootloader: 220,000 kH/s)




---

📦 Wallet Module

Handles rig provisioning and reward tracking.

Fields:

wallet_id – unique ID

righashpower – current hash power

capsulevaluemb – MB mined

real_kwh – energy usage

totalbandwidthMBps – throughput

manierism_tokens – 1 per 100 MB




---

🖥 Main Menu Interface

Launch rig software:

python rig_main.py

Menu Options:

1. Start CPU Mining


2. Start Wi-Fi Mining


3. Start SHA Capsule Mining


4. Rig Mining Submenu


5. Create New Rig


6. View Worker Rigs


7. View Wallet File


8. Exit




---

📦 Installation

Python 3.9+

pip install cryptography requests



---

📊 Capsule Flow Diagram

Hash Power (H_cpu) → Virtual Energy → Real Energy (kWh) → USD Value
Hash Power (H_cpu) → Bandwidth (MB/s) → Capsule Metadata

Feedback:
MB (1–11 per tick) → MB spent/donated → Hash power ↑ → MB ↑


---

🧬 Runtime Sovereignty

This system respects sovereign valuation laws, allowing symbolic overlays when remixing capsule tiers. All reward logic is runtime-auditable, with finite metrics for MB, kWh, USD, and BTC.

config.py (settings & constants)

wallet.py (wallet class for balance, deposits, withdrawals, and MB→HS donations)

wallet.json (an initialized wallet file that the software will use)


----

Imports

import os
import time
import json
import random
from decimal import Decimal, getcontext
from cryptography.fernet import Fernet


------

run.py

#!/usr/bin/env python3
import os
import time
import json
import random
from decimal import Decimal, getcontext

# High precision
getcontext().prec = 200

# --- Paths & constants ---
BASEDIR = "/storage/emulated/0/Download/manierismmegabytes"
TARGETDIR = os.path.join(BASEDIR, "rigs")
os.makedirs(TARGETDIR, exist_ok=True)

DONATION_WALLET_ID = "WM-CPH0O7J3"

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
    # Convert back to Decimal
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
    }
    save_wallet(wallet)
    return wallet

# Ensure donation wallet exists
if not load_wallet(DONATION_WALLET_ID):
    create_wallet(DONATION_WALLET_ID, "donations")

# --- Capsule & Mining ---
def mint_capsule(wallet, capsule_type, reward_mb):
    wallet["capsule_value_mb"] += reward_mb
    wallet["rig_hash_power"] += reward_mb * Decimal("0.1")
    wallet["real_kwh"] += reward_mb * Decimal("0.02")
    wallet["bandwidth_MBps"] += reward_mb * Decimal("0.0001")
    save_wallet(wallet)
    metadata = {
        "capsuletype": capsule_type,
        "reward_mb": float(reward_mb),
        "real_kwh": float(wallet["real_kwh"])
    }
    return metadata

def unified_mining_loop(wallet):
    capsule_types = [
        "sha","bandwidth","electrism","manierism","handrichism",
        "gigabyte","terabyte","pib","petabyte","sdram","ram"
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
                    # Create wallet if it doesn't exist yet
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
            if wallet["capsule_value_mb"] >= amt:
                donate_mb_for_hash(wallet, amt)
            else:
                print("⚠️ Not enough MB balance.")

        elif option == "4":
            break
        else:
            print("⚠️ Invalid option.")

def donate_mb_for_hash(sender_wallet, amount_mb):
    donation_wallet = load_wallet(DONATION_WALLET_ID)
    if not donation_wallet:
        print("⚠️ Donation wallet not found.")
        return
    sender_wallet["capsule_value_mb"] -= amount_mb
    donation_wallet["capsule_value_mb"] += amount_mb
    sender_wallet["rig_hash_power"] += int(amount_mb)  # Add hash to sender
    save_wallet(donation_wallet)
    save_wallet(sender_wallet)
    print(f"🙏 Donated {amount_mb} MB. Hash power added to your wallet/rig.")

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
    print(f"Hash Power: {wallet['rig_hash_power']:.6f}")
    print(f"Capsule MB: {wallet['capsule_value_mb']:.6f}")
    print(f"Real kWh: {wallet['real_kwh']:.6f}")
    print(f"USD Value: ${float(wallet['capsule_value_mb'])*0.05:.2f}")
    print(f"Bandwidth: {wallet['bandwidth_MBps']:.6f} MB/s")
    print(f"Bandwidth USD: ${float(wallet['bandwidth_MBps'])*0.00027:.6f}")

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

---

config.py

# --- Config file for rig mining software ---

# Paths
WALLET_FILE = "wallet.json"
ENCRYPTION_KEY_FILE = "wallet.key"

# Starting values
START_HASHPOWER = 25000        # Initial hash power
DONATION_RATE_MB_TO_HS = 1     # 1 MB donation = 1 HS gained
MAX_HASHPOWER_TARGET = 2.62503205022007e152  # 1/4 MAX_HASH (cap reached in ~75 years)

# Rewards
BASE_REWARD_MB = 0.001         # Small early reward in MB
REWARD_GROWTH_FACTOR = 1.0001  # Growth multiplier over time

# Mining loop
MINING_INTERVAL = 10           # seconds between reward ticks

# Logging
ENABLE_LOGGING = True
LOG_FILE = "rig_mining.log"


---

wallet.py

import json
import os
from decimal import Decimal, getcontext
from cryptography.fernet import Fernet

from config import WALLET_FILE, ENCRYPTION_KEY_FILE, DONATION_RATE_MB_TO_HS

# high precision math for huge numbers
getcontext().prec = 200


class Wallet:
    def __init__(self):
        self.key = None
        self.fernet = None
        self.data = None

        self._load_key()
        self._load_wallet()

    def _load_key(self):
        if not os.path.exists(ENCRYPTION_KEY_FILE):
            self.key = Fernet.generate_key()
            with open(ENCRYPTION_KEY_FILE, "wb") as f:
                f.write(self.key)
        else:
            with open(ENCRYPTION_KEY_FILE, "rb") as f:
                self.key = f.read()
        self.fernet = Fernet(self.key)

    def _load_wallet(self):
        if not os.path.exists(WALLET_FILE):
            # create new wallet
            self.data = {
                "address": "rig_wallet",
                "balance_mb": str(Decimal("0")),
                "hashpower": str(Decimal("25000")),  # starting hashpower
                "donated_mb": str(Decimal("0"))
            }
            self._save_wallet()
        else:
            with open(WALLET_FILE, "rb") as f:
                encrypted = f.read()
                decrypted = self.fernet.decrypt(encrypted)
                self.data = json.loads(decrypted.decode())

    def _save_wallet(self):
        raw = json.dumps(self.data).encode()
        encrypted = self.fernet.encrypt(raw)
        with open(WALLET_FILE, "wb") as f:
            f.write(encrypted)

    def get_balance(self):
        return Decimal(self.data["balance_mb"])

    def get_hashpower(self):
        return Decimal(self.data["hashpower"])

    def deposit(self, amount_mb: Decimal):
        bal = self.get_balance() + amount_mb
        self.data["balance_mb"] = str(bal)
        self._save_wallet()

    def withdraw(self, amount_mb: Decimal):
        bal = self.get_balance()
        if amount_mb > bal:
            raise ValueError("Insufficient balance")
        bal -= amount_mb
        self.data["balance_mb"] = str(bal)
        self._save_wallet()

    def donate_mb_for_hashpower(self, amount_mb: Decimal):
        """Donate MB to permanently increase hash power"""
        bal = self.get_balance()
        if amount_mb > bal:
            raise ValueError("Insufficient balance to donate")
        # subtract MB
        bal -= amount_mb
        self.data["balance_mb"] = str(bal)

        # increase hashpower
        hs = self.get_hashpower() + (amount_mb * DONATION_RATE_MB_TO_HS)
        self.data["hashpower"] = str(hs)

        # track total donations
        donated = Decimal(self.data["donated_mb"]) + amount_mb
        self.data["donated_mb"] = str(donated)

        self._save_wallet()


---

wallet.json

> ⚠️ This is stored encrypted on first run by wallet.py.
Here’s what the unencrypted structure looks like before encryption:

No need to install



{
  "address": "rig_wallet",
  "balance_mb": "0",
  "hashpower": "25000",
  "donated_mb": "0"
}

When you first run the wallet, it generates an encryption key (wallet.key) and encrypts this JSON for secure storage.


Altering or tampering with software is not allowed and will not be tolerated or accepted as currency on the rig 


------

Updates coming to the blockchain 


 p2p pool for megabytes, hashpower, bandwidth, kilowatts, manierism tokens 

Nft marketplace 

Blockchain explorer 

Future road map 

a ui/ux web display the rig mining with cool features and software 

Cell phone and internet signal through bandwidth 

Electricity produced from run.py to run power to power banks 




































