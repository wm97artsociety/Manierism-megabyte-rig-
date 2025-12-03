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

# The Eginma Multiplier (N = 1 Billion or 10^9) to scale the reward
EGINMA_MULTIPLIER = Decimal("1000000000")

# --- NEW: Fixed Input for 12V Battery Mining (Treating 12V as base MB) ---
FIXED_12V_MB_INPUT = Decimal("12") 
# -------------------------------------------------------------------------

MB_USD_RATE = Decimal("5.00")
CACHE_USD_RATE = Decimal("0.42")
KWH_USD_RATE = Decimal("0.17")
BANDWIDTH_USD_RATE = Decimal("0.42")
TORRENT_USD_RATE = MB_USD_RATE

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
        1e39: "Duodecillion", 1e42: "Tredecillion",
        1e45: "Quattuordecillion", 1e48: "Quindecillion", 1e51: "Sexdecillion",
        1e54: "Septendecillion", 1e57: "Octodecillion", 1e60: "Novemdecillion",
        1e63: "Vigintillion",
        # --- NEW: Added numbers up to Trigintillion (10^93) for extended mining targets ---
        1e66: "Unvigintillion", 1e69: "Duovigintillion", 1e72: "Trevigintillion",
        1e75: "Quattuorvigintillion", 1e78: "Quinvigintillion", 1e81: "Sexvigintillion",
        1e84: "Septenvigintillion", 1e87: "Octovigintillion", 1e90: "Novemvigintillion",
        1e93: "Trigintillion"
        # ---------------------------------------------------------------------------------
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

# --- Blackjack Mini-Game Constants & Utilities ---

CARD_SYMBOLS = {
    'Spades': '♠', 'Hearts': '♥', 'Diamonds': '♦', 'Clubs': '♣'
}
CARD_RANKS = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    'T': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11
}

# CORRECTED CURRENCIES MAPPING based on wallet keys
CURRENCIES = {
    # Key displayed to user: (Display Name, Wallet Key)
    '1': ('Torrents Payloads (MB)', 'torrent_value_mb'),
    '2': ('Capsule Megabytes', 'capsule_value_mb'),
    '3': ('Kilowatts (kWh)', 'real_kwh'),
    '4': ('Cache Megabytes', 'cache_value_mb'),
    '5': ('Bandwidth MB/s', 'bandwidth_MBps'),
}

def create_deck():
    """Creates a standard 52-card deck."""
    deck = []
    suits = list(CARD_SYMBOLS.keys())
    ranks = list(CARD_RANKS.keys())
    for suit in suits:
        for rank in ranks:
            deck.append((rank, suit))
    random.shuffle(deck)
    return deck

def get_hand_value(hand):
    """Calculates the total value of a hand, accounting for Aces."""
    value = sum(CARD_RANKS[card[0]] for card in hand)
    num_aces = sum(1 for card in hand if card[0] == 'A')
    
    # Adjust Aces from 11 to 1 if the total is over 21
    while value > 21 and num_aces > 0:
        value -= 10
        num_aces -= 1
    return value

def get_card_art(card, face_down=False):
    """Generates ASCII art for a card."""
    rank, suit_name = card
    suit_symbol = CARD_SYMBOLS.get(suit_name, ' ')
    
    if face_down:
        lines = [
            "┌───────┐",
            "│░░░░░░░│",
            "│░░░░░░░│",
            "│░░░░░░░│",
            "│░░░░░░░│",
            "│░░░░░░░│",
            "└───────┘"
        ]
    else:
        lines = [
            "┌───────┐",
            f"│ {rank:<2}    │",
            "│       │",
            f"│   {suit_symbol}   │",
            "│       │",
            f"│    {rank:>2} │",
            "└───────┘"
        ]
    return lines

def display_hands(player_hand, dealer_hand, hide_dealer_card=True):
    """Prints the player and dealer hands side-by-side in the terminal."""
    
    # Configure which of the dealer's cards to display
    dealer_display = []
    if hide_dealer_card:
        # Hide the dealer's second card
        dealer_cards = [dealer_hand[0], ('?', 'Down')] + dealer_hand[2:]
    else:
        dealer_cards = dealer_hand

    # Get card art for both hands
    player_art = [get_card_art(c, False) for c in player_hand]
    dealer_art = [get_card_art(c, c[0] == '?') for c in dealer_cards]

    print("\n" + "="*50)
    
    # Print Dealer Hand
    print("DEALER'S HAND:")
    # Transpose the card art lines to print them horizontally
    for i in range(len(dealer_art[0])):
        line = "    ".join(card[i] for card in dealer_art)
        print(line)
    
    if not hide_dealer_card:
        print(f"Value: {get_hand_value(dealer_hand)}")
        
    print("\n" + "-"*50)
    
    # Print Player Hand
    print("YOUR HAND:")
    for i in range(len(player_art[0])):
        line = "    ".join(card[i] for card in player_art)
        print(line)
    print(f"Value: {get_hand_value(player_hand)}")
    print("="*50)


def blackjack_game(wallet):
    
    # Load the latest wallet data
    wallet = load_wallet(wallet['wallet_id'])
    
    print(f"\n⚡ Blackjack - Choose Your Betting Currency ⚡")
    print("1. Torrents Payloads (MB)")
    print("2. Capsule Megabytes")
    print("3. Kilowatts (real_kwh)")
    print("4. Cache Megabytes")
    print("5. Bandwidth MB/s")
    
    # --- 1. Get Currency Choice ---
    while True:
        choice = input("Enter choice (1-5): ").strip()
        if choice in CURRENCIES:
            currency_name, currency_key = CURRENCIES[choice]
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")
            
    current_balance = wallet.get(currency_key, Decimal("0"))
    
    if current_balance <= 0:
        print(f"❌ You have no {currency_name} to bet! Go mining to earn some.")
        return

    print(f"Current Balance in {currency_name}: {format_large_number(current_balance)}")

    # --- 2. Get Bet ---
    while True:
        bet_input = input(f"Enter your bet in {currency_name}: ").strip()
        try:
            bet = Decimal(bet_input)
            if bet <= 0:
                print("Bet must be a positive number.")
            elif bet > current_balance:
                print(f"You can't bet more than your current balance of {format_large_number(current_balance)}.")
            else:
                break
        except:
            print("Invalid input. Please enter a number.")

    # Deduct the bet and save the wallet (Bet is removed immediately upon starting the hand)
    wallet[currency_key] -= bet
    save_wallet(wallet)
    print(f"Bet placed: {format_large_number(bet)} {currency_name}. New balance: {format_large_number(wallet[currency_key])} {currency_name}.")

    # --- 3. Setup Game ---
    deck = create_deck()
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]

    # Check for immediate Blackjacks
    player_blackjack = get_hand_value(player_hand) == 21
    
    # --- 4. Player's Turn ---
    player_busted = False
    if not player_blackjack:
        
        while True:
            display_hands(player_hand, dealer_hand, hide_dealer_card=True)
            p_value = get_hand_value(player_hand)
            
            # Options available: Hit, Stand, Double Down (only on first move)
            has_enough_for_double = bet <= wallet.get(currency_key, Decimal("0"))
            
            if len(player_hand) == 2 and has_enough_for_double:
                 action = input("Action (H)it, (S)tand, (D)ouble Down: ").strip().lower()
            else:
                 action = input("Action (H)it or (S)tand: ").strip().lower()

            if action == 'h':
                player_hand.append(deck.pop())
                p_value = get_hand_value(player_hand)
                if p_value > 21:
                    player_busted = True
                    display_hands(player_hand, dealer_hand, hide_dealer_card=True)
                    print("BUST! You went over 21. Funds were already deducted.")
                    break
            elif action == 's':
                break
            elif action == 'd' and len(player_hand) == 2 and has_enough_for_double:
                # Double Down logic: double bet, deduct second bet, take one card, then stand
                wallet[currency_key] -= bet # Deduct the second bet amount
                bet *= 2 # Total bet is now doubled
                save_wallet(wallet)
                print(f"Double Down! New total bet: {format_large_number(bet)} {currency_name}.")
                player_hand.append(deck.pop())
                p_value = get_hand_value(player_hand)
                if p_value > 21:
                    player_busted = True
                    display_hands(player_hand, dealer_hand, hide_dealer_card=True)
                    print("BUST on Double Down! Funds were already deducted.")
                break
            else:
                print("Invalid action.")
    
    # --- 5. Dealer's Turn (only if player didn't bust) ---
    d_value = get_hand_value(dealer_hand)
    dealer_blackjack = d_value == 21 and len(dealer_hand) == 2
    d_busted = False
    
    if not player_busted and not (player_blackjack and dealer_blackjack):
        
        print("\n--- Dealer's Turn ---")
        display_hands(player_hand, dealer_hand, hide_dealer_card=False) # Show both dealer cards
        
        # Dealer must hit on soft 17 or less
        while d_value < 17:
            print("Dealer hits...")
            time.sleep(1) # Pause for terminal display effect
            dealer_hand.append(deck.pop())
            d_value = get_hand_value(dealer_hand)
            display_hands(player_hand, dealer_hand, hide_dealer_card=False)
            
        if d_value > 21:
            print("DEALER BUSTS!")
            d_busted = True
        else:
            print("Dealer stands.")
            
    # --- 6. Determine Winner and Payout ---
    print("\n=== Game Result ===")
    display_hands(player_hand, dealer_hand, hide_dealer_card=False)
    
    p_value = get_hand_value(player_hand)
    d_value = get_hand_value(dealer_hand)
    
    payout = Decimal("0") # This will be the total amount returned (Bet + Winnings)
    
    if player_busted:
        # Player Busted: Bet was already deducted. Total return is 0.
        print(f"You lose {format_large_number(bet)} {currency_name}.")
    elif player_blackjack and not dealer_blackjack:
        # Player Blackjack: 1.5x profit (reward) + 1x bet returned = 2.5x total return
        payout = bet * Decimal("2.5")
        print(f"👑 BLACKJACK! You win 1.5 times your bet! Total return (Bet + Reward): {format_large_number(payout)} {currency_name}.")
    elif d_busted:
        # Dealer busts: 1x profit (reward) + 1x bet returned = 2x total return
        payout = bet * Decimal("2")
        print(f"🎉 Dealer Busts! You win 1 time your bet! Total return (Bet + Reward): {format_large_number(payout)} {currency_name}.")
    elif p_value > d_value:
        # Regular win: 1x profit (reward) + 1x bet returned = 2x total return
        payout = bet * Decimal("2")
        print(f"✅ You Win! Your {p_value} beats the dealer's {d_value}. Total return (Bet + Reward): {format_large_number(payout)} {currency_name}.")
    elif p_value == d_value:
        # Push: bet is returned (1x total return)
        payout = bet
        print(f"🤝 Push. It's a tie, your bet of {format_large_number(payout)} {currency_name} is returned.")
    else:
        # Loss: Total return is 0.
        print(f"❌ You Lose. Dealer's {d_value} beats your {p_value}.")

    # Add total return (payout) to the wallet
    wallet[currency_key] += payout
    save_wallet(wallet)
    print(f"Final Balance in {currency_name}: {format_large_number(wallet[currency_key])}")


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

    for key in ["capsule_value_mb", "cache_value_mb", "rig_hash_power", "real_kwh", "bandwidth_MBps", "world_debt_paid_usd", "torrent_value_mb"]:  
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
        wallet.get('bandwidth_MBps', Decimal("0")) * BANDWIDTH_USD_RATE +
        wallet.get('torrent_value_mb', Decimal("0")) * TORRENT_USD_RATE
    )

# --- Capsule Types ---

CUSTOM_REWARDS = [
    "Formula_Power", "Y7K DOLLAR", "bricks dollar", "2piE", "TE", "TE2pi", "Manierism", "Handrichism", 
    "teЛ²", "E²Л",
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
  
                # Apply Eginma Multiplier (10^9) for enhanced reward rate
                base_mb_reward_roll *= EGINMA_MULTIPLIER
            else:  
                # Use the fixed 12V input as the base capsule MB for mining, as per Igma overlay
                base_mb_reward_roll = FIXED_12V_MB_INPUT  

         
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
            if capsule_type == "E^2*Л":
                print("⚡ ENHANCED REWARD RATE: Eginma Multiplier (10^9) APPLIED!")
            # Add a message to confirm the fixed 12V input is used for other capsules
            elif capsule_type != "E^2*Л":
                print(f"🔋 FIXED 12V INPUT: Using {FIXED_12V_MB_INPUT} as base capsule MB for Igma overlay.")
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
            total_usd = calculate_total_usd(wallet)  
            if amt > total_usd:  
                print(f"⚠️ Not enough USD-backed balance. Max: ${format_large_number(total_usd)}")  
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
            total_usd_target = calculate_total_usd(target)  
            if total_usd_target > 0:  
                factor = (total_usd_target + amt) / total_usd_target  
                target['capsule_value_mb'] *= factor  
                target['cache_value_mb'] *= factor  
                target['real_kwh'] *= factor  
                target['bandwidth_MBps'] *= factor  
                target['torrent_value_mb'] *= factor  
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
    for i, wallet_id in enumerate(sorted(wallets_data.keys(), key=lambda x: (x != WORLD_DEBT_WALLET_ID, x != DONATION_WALLET_ID, x)), 1):
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
        print("⚠️ No personal wallets/rigs found. Create one first (Option 6 in main menu).")
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
        print(f"⚡ SHA Boost ACTIVE: +{format_large_number(boost_calc)} H/s (Currently applied for this tick)")

    print("-" * 40)
    print("Capsule Resources:")
    print(f" MB:               {format_large_number(wallet['capsule_value_mb'])}")
    print(f" Cache MB:         {format_large_number(wallet['cache_value_mb'])}")
    print(f" Real kWh:         {format_large_number(wallet['real_kwh'])}")
    print(f" Bandwidth MB/s:   {format_large_number(wallet['bandwidth_MBps'])}")
    print(f" Torrent MB:       {format_large_number(wallet['torrent_value_mb'])}")
    print(f"💰 Total USD Value: ${format_large_number(total_usd)}")
    print(f"📦 Device Cache:   {format_large_number(device_cache)} MB (System)")
    print("-" * 40)
    
    if wallet['wallet_id'] == WORLD_DEBT_WALLET_ID:
        paid = wallet.get("world_debt_paid_usd", Decimal("0"))
        remaining = INITIAL_WORLD_DEBT_USD - paid
        print(f"🌍 Global Debt Progress:")
        print(f" Total Paid:       ${format_large_number(paid)}")
        print(f" Remaining:        ${format_large_number(remaining)}")
    else:
        paid = wallet.get("world_debt_paid_usd", Decimal("0"))
        remaining = INITIAL_WORLD_DEBT_USD - paid
        print(f"🌍 Your Debt Contribution: ${format_large_number(paid)}")
        print(f"🌍 Remaining Global Debt: ${format_large_number(remaining)}")


# --- Internet Terminal (Option 17) ---
MB_USED_TOTAL = Decimal("0.0")
flask_thread_started = False
current_url = None
app = Flask(__name__)

@app.route('/')
def render_page():
    global current_url
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
    global MB_USED_TOTAL
    url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
    response = requests.get(url)
    
    MB_USED_TOTAL += len(response.content) / (1024 * 1024)
    burned_MB = Decimal(MB_USED_TOTAL)
    
    wallet['capsule_value_mb'] -= burned_MB
    if wallet['capsule_value_mb'] < 0:
        wallet['capsule_value_mb'] = Decimal("0")
        
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

def internet_terminal(wallet):
    global current_url, flask_thread_started
    wallet = load_wallet(wallet['wallet_id'])
    node_id = wallet.get('node_id', 'N/A')
    
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
            print(f"\n--- Result {i} ---")
            print(f"Title:   {r['title']}")
            print(f"Link:    {r['link']}")
            print(f"Snippet: {r['snippet']}")
        print("\n" + "="*50)


# --- Rig Info Export (Option 12) ---

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
    print(" 1. Capsule MB")
    print(" 2. Cache MB")
    print(" 3. Real kWh")
    print(" 4. Bandwidth MBps")
    print(" 5. Torrent MB")
    print(" 6. Watts USD (calculated)")
    print(" 7. Cancel")
    
    choice = input("Enter option: ").strip()
    
    resource_map = {
        "1": "capsule_value_mb",
        "2": "cache_value_mb",
        "3": "real_kwh",
        "4": "bandwidth_MBps",
        "5": "torrent_value_mb",
        "6": "usd_value"
    }

    if choice == "7":
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
    print(" 1. .json")
    print(" 2. .txt")
    print(" 3. .torrent")
    print(" 4. .csv (advanced)")
    
    file_choice = input("Enter option: ").strip()
    
    if file_choice == "1":
        file_ext = "json"
    elif file_choice == "2":
        file_ext = "txt"
    elif file_choice == "3":
        if resource_key not in ["capsule_value_mb", "torrent_value_mb"]:
            print("⚠️ .torrent format is only valid for Capsule MB or Torrent MB.")
            return
        file_ext = "torrent"
    elif file_choice == "4":
        file_ext = "csv"
    else:
        print("⚠️ Invalid file format selection.")
        return
        
    # Process Export Logic
    
    # Placeholder for file export logic (requires actual export implementation)
    
    # If not exporting USD, deduct the resource amount from the wallet
    if resource_key != "usd_value":
        wallet[resource_key] -= amt
    else:
        # If exporting USD, deduct a proportional amount of all resources
        proportion = amt / available
        wallet['capsule_value_mb'] -= wallet['capsule_value_mb'] * proportion
        wallet['cache_value_mb'] -= wallet['cache_value_mb'] * proportion
        wallet['real_kwh'] -= wallet['real_kwh'] * proportion
        wallet['bandwidth_MBps'] -= wallet['bandwidth_MBps'] * proportion
        wallet['torrent_value_mb'] -= wallet['torrent_value_mb'] * proportion
    
    save_wallet(wallet)
    
    file_name = f"export_{resource_key.replace('_','-')}_{wallet['wallet_id']}.{file_ext}"
    print(f"✅ Simulated export of {format_large_number(amt)} {resource_key.replace('_',' ')} to {file_name}")
    print(f"⚠️ Note: Resource deducted from balance.")


# --- World Debt Payment Plan (Option 15) ---

def show_world_debt_payment_menu(wallet):
    print("\n🌎 World Debt Payment Plan 🌎")
    print(f"Your Wallet ID: {wallet['wallet_id']}")
    print(f"Your Node ID: {wallet['node_id']}")
    print(f"Debt Date: {WORLD_DEBT_DATE}")
    print("-" * 40)
    
    total_usd = calculate_total_usd(wallet)
    paid = wallet.get("world_debt_paid_usd", Decimal("0"))
    remaining = INITIAL_WORLD_DEBT_USD - paid
    
    print(f"💰 Your Total USD Value: ${format_large_number(total_usd)}")
    print(f"🌍 Your Debt Paid: ${format_large_number(paid)}")
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

    available = calculate_total_usd(wallet)
    if amt > available:
        print(f"⚠️ Not enough USD-backed balance. Max: ${format_large_number(available)}")
        return
        
    proportion = amt / available
    wallet['capsule_value_mb'] -= wallet['capsule_value_mb'] * proportion
    wallet['cache_value_mb'] -= wallet['cache_value_mb'] * proportion
    wallet['real_kwh'] -= wallet['real_kwh'] * proportion
    wallet['bandwidth_MBps'] -= wallet['bandwidth_MBps'] * proportion
    wallet['torrent_value_mb'] -= wallet['torrent_value_mb'] * proportion
    
    wallet['world_debt_paid_usd'] += amt
    
    debt_wallet = load_wallet(WORLD_DEBT_WALLET_ID)
    if debt_wallet:
        debt_wallet['capsule_value_mb'] += amt / MB_USD_RATE
        debt_wallet['torrent_value_mb'] += amt / MB_USD_RATE
        save_wallet(debt_wallet)
        
    save_wallet(wallet)
    
    print(f"✅ Contributed ${format_large_number(amt)} to World Debt Wallet.")
    print("🌍 Your node has been logged as a symbolic contributor to planetary debt reduction.")

def wallet_transaction_menu(wallet):
    while True:
        wallet = load_wallet(wallet['wallet_id'])
        if not wallet:
            break
            
        show_rig_dashboard(wallet)
        
        print("\n--- Wallet Actions ---")
        print(" 1. Send Capsule MB")
        print(" 2. Send Cache MB")
        print(" 3. Send kWh")
        print(" 4. Send Bandwidth")
        print(" 5. Send Watts USD")
        print(" 6. Send Torrent MB")
        print("--- Donations (Hash Power) ---")
        print(" 7. Donate Capsule MB (Passive Hash Gain)")
        print(" 8. Donate Cache MB (Amplified Hash Gain)")
        print(" 9. Donate kWh (Passive Hash Gain)")
        print(" 10. Donate Bandwidth (Passive Hash Gain)")
        print(" 11. Donate Torrent MB (Passive Hash Gain)")
        print("--- Rig/Node Functions ---")
        print(" 12. Show/Receive Info")
        print(" 13. Enhanced Resource Export")
        print(" 14. Export Rig Info (.json)")
        print(" 15. World Debt Payment Plan 🌎")
        print(" 16. Back to Main Menu")
        print(" 17. Access Internet Terminal (Node-Linked)")
        print(" ----------------------------------------")
        
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
            break
        elif option == "17":
            internet_terminal(wallet)
        else:
            print("⚠️ Invalid option.")

# --- Main Menu and Helper Functions ---

def scan_device_cache_mb():
    # Placeholder for OS-level cache scan, returning a random dummy value for simulation
    # In a real environment, this would read actual cache/temp file size
    simulated_cache = Decimal(random.randint(100, 1000)) + Decimal(random.random())
    return simulated_cache.quantize(Decimal("0.01")), "Simulated Device Cache"

def start_mining(mining_type):
    wallet = select_wallet_for_mining()
    if wallet:
        print(f"\n🚀 Starting {mining_type.upper()} mining for Rig: {wallet['rig_id']}...")
        unified_mining_loop(wallet, mining_type)
        
def view_wallets_rigs_menu():
    while True:
        wallet = select_wallet_or_rig()
        if not wallet:
            break
        wallet_transaction_menu(wallet)
        
def show_receive_info(wallet):
    print("\n--- Receive Info ---")
    print(f"Wallet ID: {wallet['wallet_id']}")
    print(f"Rig ID: {wallet.get('rig_id', wallet['wallet_id'])}")
    print(f"Node ID: {wallet.get('node_id', 'N/A')}")
    print("--------------------")
    print("Senders can use your Wallet ID to transfer resources.")
    print("Your Node ID can be used for advanced overlay connections.")
    
def main_menu():
    _initialize_special_wallets()
    while True:
        print("\n--- Manierism Megabytes Rig Console ---")
        print(" 1. Start Kinetic Mining")
        print(" 2. Start WiFi Mining")
        print(" 3. Start SHA Mining boost")
        print(" 4. Start Cache Mining")
        print(" 5. Play Blackjack (Use Wallet Resources)")
        print(" 6. Create New Rig/Wallet")
        print(" 7. View Wallets/Rigs (Transactions/Dashboard)")
        print(" 8. Exit")
        print("-" * 40)
        
        choice = input("Enter option: ").strip()
        
        # Passive value generation for the World Debt Node
        world_debt_node_value_generation()
        
        if choice == "1":
            start_mining("kinetic")
        elif choice == "2":
            start_mining("wifi")
        elif choice == "3":
            start_mining("sha")
        elif choice == "4":
            start_mining("cache")
        elif choice == "5": # New Blackjack option
            # Need to select a wallet/rig to use for betting
            rig_id = input("Enter Rig ID (Wallet Name) to use for betting: ").strip()
            # Attempt to load the wallet by ID or by the file path pattern
            wallet_to_use = load_wallet(rig_id) or load_wallet(f"{rig_id}")
            if not wallet_to_use:
                print(f"⚠️ Wallet/Rig '{rig_id}' not found.")
            else:
                blackjack_game(wallet_to_use) # Call the game with the selected wallet
        elif choice == "6":
            rig_id = input("Enter Rig ID or Wallet Name: ").strip()
            wallet_id = input("Enter Wallet ID: ").strip()
            new_wallet = create_wallet(wallet_id, rig_id)
            if new_wallet:
                print(f"✅ Created new wallet/rig: {rig_id} ({wallet_id}) with Node ID: {new_wallet['node_id']}")
        elif choice == "7":
            view_wallets_rigs_menu()
        elif choice == "8":
            print("Exiting... 👋 See you later F&F ❤️")
            break
        else:
            print("⚠️ Invalid option.")

if __name__ == "__main__":
    main_menu()
