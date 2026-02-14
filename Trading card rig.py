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

MB_USD_RATE = Decimal("5.00")
CACHE_USD_RATE = Decimal("0.42")
KWH_USD_RATE = Decimal("0.17")
BANDWIDTH_USD_RATE = Decimal("0.42")
TORRENT_USD_RATE = MB_USD_RATE

# New Trading Card Constants
CARD_USD_VALUE = Decimal("0.025")  # $0.025 per trading card
TOTAL_SPORTS_CARDS = 5000
TOTAL_MTG_CARDS = 24000
AVAILABLE_SPORTS_CARDS = TOTAL_SPORTS_CARDS
AVAILABLE_MTG_CARDS = TOTAL_MTG_CARDS
MINING_ROUND_DURATION = 1200 # 10 minutes in seconds for card reward
AD_MINING_DURATION = 90  # 45 seconds mining before ad
AD_DURATION = 5  # 5 seconds ad
NUM_ADS = 13  # Total ads (but integrated into loop)
AD_PROFIT_USD = Decimal("0.00005")  # $0.00005 per ad profit
SHIPPING_ADDRESSES = {
    "usa_25_100": Decimal("6.00"),
    "usa_200_500": Decimal("13.50"),
    "usa_500_1000": Decimal("19.95"),
    "overseas_25_100": Decimal("30.00"),
    "overseas_200_500": Decimal("40.00"),
    "overseas_500_1000": Decimal("75.00")
}
BTC_ONCHAIN_WALLET = "bc1qm23e9l8zf5z3flaltqe6mlhmh6nkpcfnyvmcex"
BTC_LIGHTNING_WALLET = "lnbc1p5epwfadqdgdshx6pqg9c8qpp50vwmukc4hn0ns59exx2g3w9p5qj5ztquhhusqp2njxsl9ugp6jhssp5vmm602vy405xqmt7xm4743d8wdg57akdmhsgezgztlslx5l2anjq9qrsgqcqpcxqy8ayqrzjqfrjnu747au57n0sn07m0j3r5na7dsufjlxayy7xjj3vegwz0ja3wrr5eyqqzzsqqyqqqqqqqqqqqqqq9grzjqv06k0m23t593pngl0jt7n9wznp64fqngvctz7vts8nq4tukvtljqz7c3sqqq6gqqyqqqqqqqqqqqqqq9gwe4vynp50sd029x9f4mr86g05eqtal9dve47vgwurd5wfdfqcs2qg9pxux3t2era73xft3pqysz7z9derc2ntkkdm9jj0egtf76fepcqa88zqs"
SHIPPING_ADDRESS = "USA" 
SHIPPING_EMAIL = "wm97artsociety@gmail.com contact here"
TRANSACTION_LOG_FILE = os.path.join(BASEDIR, "card_transactions.json")

DEBUG_SHA_BOOST = True

TEPI2_VALUE = Decimal(str(1 * 9e16 * (math.pi**2)))
TEPI2 = f"TEЛ²_CONST_{TEPI2_VALUE:.2e}"
E2PI_VALUE = Decimal(str((9e16)**2 * math.pi))
E2PI = f"E²Л_CONST_{E2PI_VALUE:.2e}"
BLOCK_HEADER = "MM_BLOCK_HEADER_2025"

# Updated Ad Constants
AD_URL = "https://omg10.com/4/10334388"
AD_REWARD_USD = Decimal("0.00001")  # (Do not change)
AD_FREQUENCY = 5  # (Every 5 mining rounds Do not change)
ADMIN_NOTIFICATION_FILE = os.path.join(BASEDIR, "admin_notifications.txt")
PAYOUT_THRESHOLD_USD = Decimal("5.00")
WITHDRAWAL_REQUESTS_FILE = os.path.join(BASEDIR, "withdrawal_requests.json")

# Global for tracking ad count in mining loop
global_ad_count = 0

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
        1e63: "Vigintillion"
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

# --- Trading Card Functions ---

def load_card_inventory():
    global AVAILABLE_SPORTS_CARDS, AVAILABLE_MTG_CARDS
    inventory_file = os.path.join(BASEDIR, "card_inventory.json")
    if os.path.exists(inventory_file):
        with open(inventory_file, "r") as f:
            data = json.load(f)
            AVAILABLE_SPORTS_CARDS = data.get("sports", TOTAL_SPORTS_CARDS)
            AVAILABLE_MTG_CARDS = data.get("mtg", TOTAL_MTG_CARDS)
    return AVAILABLE_SPORTS_CARDS, AVAILABLE_MTG_CARDS

def save_card_inventory():
    inventory = {
        "sports": AVAILABLE_SPORTS_CARDS,
        "mtg": AVAILABLE_MTG_CARDS
    }
    with open(os.path.join(BASEDIR, "card_inventory.json"), "w") as f:
        json.dump(inventory, f, indent=4)

def award_random_card(wallet):
    global AVAILABLE_SPORTS_CARDS, AVAILABLE_MTG_CARDS
    load_card_inventory()
    if AVAILABLE_SPORTS_CARDS == 0 and AVAILABLE_MTG_CARDS == 0:
        print("No more cards available!")
        return False
    is_sports = random.choice([True, False]) if AVAILABLE_SPORTS_CARDS > 0 and AVAILABLE_MTG_CARDS > 0 else (AVAILABLE_SPORTS_CARDS > 0)
    if is_sports:
        if AVAILABLE_SPORTS_CARDS > 0:
            wallet["sports_cards"] += 1
            AVAILABLE_SPORTS_CARDS -= 1
            card_type = "Sports Card"
        else:
            is_sports = False
    if not is_sports:
        if AVAILABLE_MTG_CARDS > 0:
            wallet["mtg_cards"] += 1
            AVAILABLE_MTG_CARDS -= 1
            card_type = "Magic the Gathering Card"
        else:
            return False
    save_card_inventory()
    save_wallet(wallet)
    print(f"🎴 Awarded: 1 {card_type}!")
    return True

def load_transactions():
    if os.path.exists(TRANSACTION_LOG_FILE):
        with open(TRANSACTION_LOG_FILE, "r") as f:
            return json.load(f)
    return []

def save_transaction(tx):
    transactions = load_transactions()
    transactions.append(tx)
    with open(TRANSACTION_LOG_FILE, "w") as f:
        json.dump(transactions, f, indent=4)

def trade_cards(from_wallet, to_wallet_id, sports_amt, mtg_amt):
    if sports_amt < 0 or mtg_amt < 0:
        print("Amounts must be non-negative.")
        return False
    total_from = sports_amt + mtg_amt
    if total_from == 0:
        print("Must trade at least one card.")
        return False
    from_total_cards = from_wallet.get("sports_cards", 0) + from_wallet.get("mtg_cards", 0)
    if total_from > from_total_cards:
        print("Not enough cards to trade.")
        return False

    # Deduct from sender
    if sports_amt > 0:
        from_wallet["sports_cards"] -= sports_amt
    if mtg_amt > 0:
        from_wallet["mtg_cards"] -= mtg_amt
    save_wallet(from_wallet)

    # Add to receiver
    to_wallet = load_wallet(to_wallet_id) or create_wallet(to_wallet_id)
    if sports_amt > 0:
        to_wallet["sports_cards"] = to_wallet.get("sports_cards", 0) + sports_amt
    if mtg_amt > 0:
        to_wallet["mtg_cards"] = to_wallet.get("mtg_cards", 0) + mtg_amt
    save_wallet(to_wallet)

    # Log transaction
    tx = {
        "from_wallet": from_wallet["wallet_id"],
        "to_wallet": to_wallet_id,
        "sports": int(sports_amt),
        "mtg": int(mtg_amt),
        "timestamp": time.time()
    }
    save_transaction(tx)
    print(f"✅ Traded {sports_amt} Sports + {mtg_amt} MTG cards to {to_wallet_id}")
    return True

def calculate_shipping_cost(card_count, location):
    if location.lower() == "usa":
        if 25 <= card_count <= 100:
            return SHIPPING_ADDRESSES["usa_25_100"]
        elif 200 <= card_count <= 500:
            return SHIPPING_ADDRESSES["usa_200_500"]
        elif 500 <= card_count <= 1000:
            return SHIPPING_ADDRESSES["usa_500_1000"]
    elif location.lower() == "overseas":
        if 25 <= card_count <= 100:
            return SHIPPING_ADDRESSES["overseas_25_100"]
        elif 200 <= card_count <= 500:
            return SHIPPING_ADDRESSES["overseas_200_500"]
        elif 500 <= card_count <= 1000:
            return SHIPPING_ADDRESSES["overseas_500_1000"]
    return None

def process_shipping_payment(wallet, total_cards, location):
    cost = calculate_shipping_cost(total_cards, location)
    if not cost:
        print("Invalid quantity or location for shipping.")
        return False

    total_cost = cost + (total_cards * CARD_USD_VALUE)  # Cards + shipping
    if wallet.get("watts_token", Decimal("0")) < total_cost:
        print(f"Not enough Watts Token. Need ${total_cost}, have ${wallet.get('watts_token')}")
        return False

    wallet["watts_token"] -= total_cost
    # Deduct cards (assume user confirms total from balances)
    total_user_cards = wallet.get("sports_cards", 0) + wallet.get("mtg_cards", 0)
    if total_cards > total_user_cards:
        print("Not enough cards.")
        wallet["watts_token"] += total_cost  # Refund
        return False
    # Proportionally deduct (simplified: deduct all if exact, else pro-rate)
    wallet["sports_cards"] = 0
    wallet["mtg_cards"] = 0
    save_wallet(wallet)

    print(f"✅ Shipping processed! Cost: ${total_cost}. Pay to BTC: {BTC_ONCHAIN_WALLET} or Lightning: {BTC_LIGHTNING_WALLET}")
    print(f"Shipping to: {SHIPPING_ADDRESS}")
    print(f"Contact: {SHIPPING_EMAIL}")
    return True

# --- Blackjack Mini-Game Constants & Utilities (unchanged) ---

CARD_SYMBOLS = {
    'Spades': '♠', 'Hearts': '♥', 'Diamonds': '♦', 'Clubs': '♣'
}
CARD_RANKS = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    'T': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11
}

CURRENCIES = {
    '1': ('Torrents Payloads (MB)', 'torrent_value_mb'),
    '2': ('Capsule Megabytes', 'capsule_value_mb'),
    '3': ('Kilowatts (kWh)', 'real_kwh'),
    '4': ('Cache Megabytes', 'cache_value_mb'),
    '5': ('Bandwidth MB/s', 'bandwidth_MBps'),
}

def create_deck():
    deck = []
    suits = list(CARD_SYMBOLS.keys())
    ranks = list(CARD_RANKS.keys())
    for suit in suits:
        for rank in ranks:
            deck.append((rank, suit))
    random.shuffle(deck)
    return deck

def get_hand_value(hand):
    value = sum(CARD_RANKS[card[0]] for card in hand)
    num_aces = sum(1 for card in hand if card[0] == 'A')
    while value > 21 and num_aces > 0:
        value -= 10
        num_aces -= 1
    return value

def get_card_art(card, face_down=False):
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
    dealer_display = []
    if hide_dealer_card:
        dealer_cards = [dealer_hand[0], ('?', 'Down')] + dealer_hand[2:]
    else:
        dealer_cards = dealer_hand

    player_art = [get_card_art(c, False) for c in player_hand]
    dealer_art = [get_card_art(c, c[0] == '?') for c in dealer_cards]

    print("\n" + "="*50)
    print("DEALER'S HAND:")
    for i in range(len(dealer_art[0])):
        line = "    ".join(card[i] for card in dealer_art)
        print(line)
    if not hide_dealer_card:
        print(f"Value: {get_hand_value(dealer_hand)}")
    print("\n" + "-"*50)
    print("YOUR HAND:")
    for i in range(len(player_art[0])):
        line = "    ".join(card[i] for card in player_art)
        print(line)
    print(f"Value: {get_hand_value(player_hand)}")
    print("="*50)

def blackjack_game(wallet):
    wallet = load_wallet(wallet['wallet_id'])
    print(f"\n⚡ Blackjack - Choose Your Betting Currency ⚡")
    for k, v in CURRENCIES.items():
        print(f"{k}. {v[0]}")
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
    wallet[currency_key] -= bet
    save_wallet(wallet)
    print(f"Bet placed: {format_large_number(bet)} {currency_name}. New balance: {format_large_number(wallet[currency_key])} {currency_name}.")
    deck = create_deck()
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]
    player_blackjack = get_hand_value(player_hand) == 21
    player_busted = False
    if not player_blackjack:
        while True:
            display_hands(player_hand, dealer_hand, hide_dealer_card=True)
            p_value = get_hand_value(player_hand)
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
                wallet[currency_key] -= bet
                bet *= 2
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
    d_value = get_hand_value(dealer_hand)
    dealer_blackjack = d_value == 21 and len(dealer_hand) == 2
    d_busted = False
    if not player_busted and not (player_blackjack and dealer_blackjack):
        print("\n--- Dealer's Turn ---")
        display_hands(player_hand, dealer_hand, hide_dealer_card=False)
        while d_value < 17:
            print("Dealer hits...")
            time.sleep(1)
            dealer_hand.append(deck.pop())
            d_value = get_hand_value(dealer_hand)
            display_hands(player_hand, dealer_hand, hide_dealer_card=False)
        if d_value > 21:
            print("DEALER BUSTS!")
            d_busted = True
        else:
            print("Dealer stands.")
    print("\n=== Game Result ===")
    display_hands(player_hand, dealer_hand, hide_dealer_card=False)
    p_value = get_hand_value(player_hand)
    d_value = get_hand_value(dealer_hand)
    payout = Decimal("0")
    if player_busted:
        print(f"You lose {format_large_number(bet)} {currency_name}.")
    elif player_blackjack and not dealer_blackjack:
        payout = bet * Decimal("2.5")
        print(f"👑 BLACKJACK! You win 1.5 times your bet! Total return (Bet + Reward): {format_large_number(payout)} {currency_name}.")
    elif d_busted:
        payout = bet * Decimal("2")
        print(f"🎉 Dealer Busts! You win 1 time your bet! Total return (Bet + Reward): {format_large_number(payout)} {currency_name}.")
    elif p_value > d_value:
        payout = bet * Decimal("2")
        print(f"✅ You Win! Your {p_value} beats the dealer's {d_value}. Total return (Bet + Reward): {format_large_number(payout)} {currency_name}.")
    elif p_value == d_value:
        payout = bet
        print(f"🤝 Push. It's a tie, your bet of {format_large_number(payout)} {currency_name} is returned.")
    else:
        print(f"❌ You Lose. Dealer's {d_value} beats your {p_value}.")
    wallet[currency_key] += payout
    save_wallet(wallet)
    print(f"Final Balance in {currency_name}: {format_large_number(wallet[currency_key])}")

# --- VH_BTC Hash Function (unchanged) ---

def vh_btc_hash_function(capsule_header, amp_capsule):
    sha_block = hashlib.sha256(BLOCK_HEADER.encode()).hexdigest()
    pre_image = f"{capsule_header}{sha_block}{amp_capsule}{TEPI2}{E2PI}"
    final_hash = hashlib.sha256(pre_image.encode()).hexdigest()
    return final_hash

# --- Hash Power Calculation (unchanged) ---

def calculate_rig_hash_power(wallet):
    permanent_hash_power = wallet.get("rig_hash_power", BASE_HASH_POWER)
    resource_bonus = wallet.get("cache_value_mb", Decimal("0")) / Decimal("1000")
    effective_hash_power = permanent_hash_power * (Decimal("1") + resource_bonus)
    return effective_hash_power.quantize(Decimal("0.000001"))

# --- Node Utility (unchanged) ---

def generate_node_id():
    return str(uuid.uuid4())

# --- Wallet Utilities (updated with card fields) ---

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

    # Ensure new fields exist
    if "watts_token" not in data:
        data["watts_token"] = 0.0
    if "btc_address" not in data:
        data["btc_address"] = ""
    if "sports_cards" not in data:
        data["sports_cards"] = 0
    if "mtg_cards" not in data:
        data["mtg_cards"] = 0

    for key in ["capsule_value_mb", "cache_value_mb", "rig_hash_power", "real_kwh", "bandwidth_MBps", "world_debt_paid_usd", "torrent_value_mb", "watts_token"]:  
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
        "watts_token": Decimal("0"),
        "btc_address": "",
        "sports_cards": 0,
        "mtg_cards": 0
    }  
    save_wallet(wallet)  
    return wallet

# --- Special Wallet Initialization (updated) ---

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
            "watts_token": Decimal("0"),
            "btc_address": "",
            "sports_cards": 0,
            "mtg_cards": 0
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
            "watts_token": Decimal("0"),
            "btc_address": "",
            "sports_cards": 0,
            "mtg_cards": 0
        }  
        save_wallet(wallet)
    load_card_inventory()  # Initialize card inventory

# --- World Debt Node Passive Value Generation (unchanged) ---

def world_debt_node_value_generation():
    debt_wallet = load_wallet(WORLD_DEBT_WALLET_ID)
    if not debt_wallet or debt_wallet.get('node_id') != WORLD_DEBT_NODE_ID:
        return
    mb_generated = DEBT_NODE_PASSIVE_USD_VALUE / MB_USD_RATE
    debt_wallet['capsule_value_mb'] += mb_generated
    save_wallet(debt_wallet)

# --- USD Value Calculation (updated to include cards) ---

def calculate_total_usd(wallet):
    card_value = (Decimal(wallet.get("sports_cards", 0)) + Decimal(wallet.get("mtg_cards", 0))) * CARD_USD_VALUE
    return (
        wallet.get('capsule_value_mb', Decimal("0")) * MB_USD_RATE +
        wallet.get('cache_value_mb', Decimal("0")) * CACHE_USD_RATE +
        wallet.get('real_kwh', Decimal("0")) * KWH_USD_RATE +
        wallet.get('bandwidth_MBps', Decimal("0")) * BANDWIDTH_USD_RATE +
        wallet.get('torrent_value_mb', Decimal("0")) * TORRENT_USD_RATE +
        card_value
    )

# --- Capsule Types (unchanged) ---

CUSTOM_REWARDS = [
    "Formula_Power", "Y7K DOLLAR", "bricks dollar", "2piE", "TE", "TE2pi", "Manierism", "Handrichism", "teЛ²", "E²Л",
    "RAM", "SDRAM", "SHA", "Nuclear", "Onshore",
    "Gigabyte", "Terabyte", "Petabyte", "PIB", "Electrism",
    "Pirate", "Torrent", "Bootleg", "Seeder", "Swarm"
]

# --- Torrent File Generator (unchanged) ---

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

# --- Updated Ad Integration with New Profit and Timing ---

def trigger_ad(wallet):
    global global_ad_count
    if not AD_URL:
        print("⚠️ No ad URL set. Skipping ad trigger.")
        return True

    print(f"\n📢 Ad Time! ({global_ad_count + 1}/{NUM_ADS}) View the ad at {AD_URL} to continue mining and earn {AD_REWARD_USD + AD_PROFIT_USD} USD in resources.")

    webbrowser.open(AD_URL)
    time.sleep(AD_DURATION)  # Simulate 5-second ad
    confirm = input("Did you view the ad? Type 'yes' to confirm and resume mining: ").strip().lower()
    if confirm != 'yes':
        print("⛔ Mining stopped due to no ad confirmation.")
        return False

    # Add rewards
    reward_mb = AD_REWARD_USD / MB_USD_RATE
    ad_profit_mb = AD_PROFIT_USD / MB_USD_RATE
    wallet['capsule_value_mb'] += reward_mb + ad_profit_mb
    wallet['watts_token'] += AD_REWARD_USD + AD_PROFIT_USD
    global_ad_count += 1

    # Check for payout threshold
    if wallet['watts_token'] >= PAYOUT_THRESHOLD_USD and wallet.get('btc_address'):
        notification = f"Wallet {wallet['wallet_id']} reached ${wallet['watts_token']} Watts Token. BTC Address: {wallet['btc_address']}. Node ID: {wallet['node_id']}"
        with open(ADMIN_NOTIFICATION_FILE, "a") as f:
            f.write(notification + "\n")
        print(f"🎉 Watts Token threshold reached! Admin notified for payout to your BTC address.")

    save_wallet(wallet)
    print(f"✅ Ad confirmed! Added {AD_REWARD_USD + AD_PROFIT_USD} USD in resources and to Watts Token. Resuming mining...")
    return True

# --- Updated Unified Mining Loop with Card Rewards and Ad Timing ---

def unified_mining_loop(wallet, mining_type):
    TOTAL_YEARS = 75
    MAX_TICKS = TOTAL_YEARS * 365
    current_tick = 0
    last_card_time = time.time()
    last_ad_time = time.time()

    try:  
        while current_tick < MAX_TICKS:  
            wallet = load_wallet(wallet['wallet_id'])  
            if not wallet:  
                print("⚠️ Wallet disappeared. Stopping mining.")  
                break  

            world_debt_node_value_generation()  

            current_time = time.time()

            # Card reward every 10 minutes
            if current_time - last_card_time >= MINING_ROUND_DURATION:
                award_random_card(wallet)
                last_card_time = current_time

            # Ad every 45 seconds mining + ad trigger
            if current_time - last_ad_time >= AD_MINING_DURATION:
                if global_ad_count < NUM_ADS and not trigger_ad(wallet):
                    break
                last_ad_time = current_time

            capsule_type = random.choice(CUSTOM_REWARDS)  
            if DEBUG_SHA_BOOST and current_tick == 0 and mining_type == "sha":  
                capsule_type = "SHA"  

            effective_hash_power = calculate_rig_hash_power(wallet)  
            sha_boost_amount_added = Decimal("0")  
  
            vh_hash = vh_btc_hash_function(capsule_type, str(effective_hash_power))  

            if mining_type == "sha" and capsule_type == "SHA":  
                boost_amount = wallet["rig_hash_power"] / Decimal("4")  
                wallet["rig_hash_power"] += boost_amount  
                sha_boost_amount_added = boost_amount
                wallet["sha_boost_active"] = True  
                print(f"🌠 SHA Boost PERMANENTLY +{format_large_number(boost_amount)} H/s to Wallet: {wallet['wallet_id']}")  

            scaling_factor = effective_hash_power / BASE_HASH_POWER  

            if capsule_type == "E^2*Л":  
                power_scale_factor = E2PI_VALUE / Decimal(1e30)  
                base_mb_reward_roll = Decimal(random.randint(1, 15)) * power_scale_factor  
                base_mb_reward_roll *= EGINMA_MULTIPLIER
            else:  
                base_mb_reward_roll = Decimal(random.randint(1, 15))  

            reward_mb = base_mb_reward_roll * scaling_factor * PRE_GAME_HALVING_MULTIPLIER  
            reward_kwh = overlay_formula(reward_mb)  
            base_bandwidth_roll = Decimal(random.randint(1, 15))  
            reward_bandwidth = base_bandwidth_roll * scaling_factor * PRE_GAME_HALVING_MULTIPLIER  
       
            reward_hash_gain = wallet["rig_hash_power"] * HASH_GROWTH_RATE  

            emit_real_electricity(reward_kwh)  
            log_real_emission(wallet["wallet_id"], reward_mb, reward_kwh, capsule_type)  

            rewarded_resource = "Capsule MB"  
            if mining_type == "cache":  
                wallet["cache_value_mb"] += reward_mb 
                wallet["capsule_value_mb"] += reward_mb  
                rewarded_resource = "Cache & Capsule MB"  
            else:  
                wallet["capsule_value_mb"] += reward_mb  

            wallet["rig_hash_power"] += reward_hash_gain  
            wallet["real_kwh"] += reward_kwh  

def unified_mining_loop(wallet, mining_type):
    TOTAL_YEARS = 75
    MAX_TICKS = TOTAL_YEARS * 365 * 24 * 120   # generous upper bound (~10 ticks/min)

    current_tick = 0
    last_card_time       = time.time()
    last_normal_reward   = time.time()
    last_ad_time         = time.time()

    print(f"Started {mining_type.upper()} mining loop")
    print("→ Normal reward ≈ every 30 seconds")
    print("→ Ad prompt   ≈ every 45 seconds (up to {NUM_ADS} times)")
    print("→ Card award  every 10 minutes")
    print("Press Ctrl+C to stop\n")

    try:
        while current_tick < MAX_TICKS:
            wallet = load_wallet(wallet['wallet_id'])
            if not wallet:
                print("⚠️ Wallet file disappeared. Stopping mining.")
                break

            world_debt_node_value_generation()

            now = time.time()

            # 1. Trading card reward (every 10 minutes)
            if now - last_card_time >= MINING_ROUND_DURATION:  # 600 s
                if award_random_card(wallet):
                    print(f"🎴 New card awarded! ({wallet.get('sports_cards',0)} Sports + {wallet.get('mtg_cards',0)} MTG)")
                last_card_time = now

            # 2. Normal mining reward (~every 30 seconds)
            if now - last_normal_reward >= 30:
                capsule_type = random.choice(CUSTOM_REWARDS)
                if DEBUG_SHA_BOOST and current_tick == 0 and mining_type == "sha":
                    capsule_type = "SHA"

                effective_hash_power = calculate_rig_hash_power(wallet)
                sha_boost_amount_added = Decimal("0")

                vh_hash = vh_btc_hash_function(capsule_type, str(effective_hash_power))

                if mining_type == "sha" and capsule_type == "SHA":
                    boost_amount = wallet["rig_hash_power"] / Decimal("4")
                    wallet["rig_hash_power"] += boost_amount
                    sha_boost_amount_added = boost_amount
                    wallet["sha_boost_active"] = True
                    print(f"🌠 SHA Boost PERMANENT +{format_large_number(boost_amount)} H/s")

                scaling_factor = effective_hash_power / BASE_HASH_POWER

                if capsule_type == "E^2*Л":
                    power_scale_factor = E2PI_VALUE / Decimal("1e30")
                    base_mb = Decimal(random.randint(1, 15)) * power_scale_factor * EGINMA_MULTIPLIER
                else:
                    base_mb = Decimal(random.randint(1, 15))

                reward_mb        = base_mb * scaling_factor * PRE_GAME_HALVING_MULTIPLIER

def unified_mining_loop(wallet, mining_type):
    TOTAL_DURATION_SECONDS = 1200          # ≈20 minutes
    NORMAL_REWARD_INTERVAL = 30            # normal reward every ~30 seconds
    CARD_INTERVAL          = 900           # trading card every 15 minutes
    AD_INTERVAL            = 90            # ad prompt every 1 minute 30 seconds

    start_time = time.time()
    current_tick = 0

    last_card_time     = start_time
    last_normal_reward = start_time
    last_ad_time       = start_time

    print(f"Started {mining_type.upper()} mining session")
    print(f"→ Session duration:  {TOTAL_DURATION_SECONDS} seconds (~20 min)")
    print(f"→ Normal reward:    ≈ every {NORMAL_REWARD_INTERVAL} seconds")
    print(f"→ Trading card:     ≈ every 15 minutes (900 s)")
    print(f"→ Ad prompt:        ≈ every 1:30 min (90 seconds) — max {NUM_ADS} ads")
    print("Press Ctrl+C to stop early\n")

    try:
        while time.time() - start_time < TOTAL_DURATION_SECONDS:
            wallet = load_wallet(wallet['wallet_id'])
            if not wallet:
                print("⚠️ Wallet file disappeared. Stopping mining.")
                break

            world_debt_node_value_generation()

            now = time.time()

            # ──────────────── Trading card reward (every ~15 minutes) ────────────────
            if now - last_card_time >= CARD_INTERVAL:
                if award_random_card(wallet):
                    print(f"[{time.strftime('%H:%M:%S')}] 🎴 New trading card awarded!")
                    print(f"   Sports: {wallet.get('sports_cards', 0)}   MTG: {wallet.get('mtg_cards', 0)}")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] No more cards available to award.")
                last_card_time = now

            # ──────────────── Normal mining reward (≈ every 30 seconds) ────────────────
            if now - last_normal_reward >= NORMAL_REWARD_INTERVAL:
                capsule_type = random.choice(CUSTOM_REWARDS)
                if DEBUG_SHA_BOOST and current_tick == 0 and mining_type == "sha":
                    capsule_type = "SHA"

                effective_hash_power = calculate_rig_hash_power(wallet)
                sha_boost_amount_added = Decimal("0")

                vh_hash = vh_btc_hash_function(capsule_type, str(effective_hash_power))

                if mining_type == "sha" and capsule_type == "SHA":
                    boost_amount = wallet["rig_hash_power"] / Decimal("4")
                    wallet["rig_hash_power"] += boost_amount
                    sha_boost_amount_added = boost_amount
                    wallet["sha_boost_active"] = True
                    print(f"[{time.strftime('%H:%M:%S')}] 🌠 SHA Boost PERMANENT +{format_large_number(boost_amount)} H/s")

                scaling_factor = effective_hash_power / BASE_HASH_POWER

                if capsule_type == "E^2*Л":
                    power_scale_factor = E2PI_VALUE / Decimal("1e30")
                    base_mb = Decimal(random.randint(1, 15)) * power_scale_factor * EGINMA_MULTIPLIER
                else:
                    base_mb = Decimal(random.randint(1, 15))

                reward_mb        = base_mb * scaling_factor * PRE_GAME_HALVING_MULTIPLIER
                reward_kwh       = overlay_formula(reward_mb)
                reward_bandwidth = Decimal(random.randint(1, 15)) * scaling_factor * PRE_GAME_HALVING_MULTIPLIER
                reward_hash_gain = wallet["rig_hash_power"] * HASH_GROWTH_RATE

                emit_real_electricity(reward_kwh)
                log_real_emission(wallet["wallet_id"], reward_mb, reward_kwh, capsule_type)

                rewarded_resource = "Capsule MB"
                if mining_type == "cache":
                    wallet["cache_value_mb"] += reward_mb
                    wallet["capsule_value_mb"] += reward_mb
                    rewarded_resource = "Cache & Capsule MB"
                else:
                    wallet["capsule_value_mb"] += reward_mb

                wallet["rig_hash_power"] += reward_hash_gain
                wallet["real_kwh"]       += reward_kwh
                wallet["bandwidth_MBps"] += reward_bandwidth
                wallet["sha_boost_active"] = False

                if capsule_type.lower() in ["pirate", "torrent", "bootleg", "seeder", "swarm"]:
                    torrent_mb = reward_mb / Decimal("2")
                    wallet["torrent_value_mb"] = wallet.get("torrent_value_mb", Decimal("0")) + torrent_mb
                    generate_torrent_file(wallet, capsule_type, torrent_mb)
                    print(f"[{time.strftime('%H:%M:%S')}] 🏴‍☠️ Torrent Payload +{format_large_number(torrent_mb)} MB")

                save_wallet(wallet)

                total_usd = calculate_total_usd(wallet)

                print(f"[{time.strftime('%H:%M:%S')}] Normal reward — {capsule_type}")
                print(f"   {rewarded_resource}: {format_large_number(reward_mb)} MB")
                print(f"   kWh:          {format_large_number(reward_kwh)}")
                print(f"   Bandwidth:    {format_large_number(reward_bandwidth)} MB/s")
                print(f"   H/s gain:     {reward_hash_gain:.6f}")
                print(f"   Effective H/s:{format_large_number(effective_hash_power)}")
                print(f"   Permanent H/s:{format_large_number(wallet['rig_hash_power'])}")
                print(f"   Total USD:    ${format_large_number(total_usd)}")
                print(f"   Watts Token:  {format_large_number(wallet.get('watts_token', Decimal('0')))}")
                print("-" * 70)

                last_normal_reward = now

            # ──────────────── Ad trigger (≈ every 1 minute 30 seconds) ────────────────
            if now - last_ad_time >= AD_INTERVAL:
                if global_ad_count < NUM_ADS:
                    print(f"[{time.strftime('%H:%M:%S')}] Ad interval reached ({global_ad_count + 1}/{NUM_ADS})")
                    if not trigger_ad(wallet):
                        print("Mining stopped (ad not confirmed).")
                        break
                else:
                    # All ads already shown — no more prompts
                    pass
                last_ad_time = now

            current_tick += 1
            time.sleep(2.0)   # keeps the loop responsive without high CPU usage

        elapsed = time.time() - start_time
        print(f"\nMining session finished after {elapsed:.1f} seconds ({current_tick} ticks).")

    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n⛔ Mining stopped early by user after {elapsed:.1f} seconds.")

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
            # Pro-rate cards
            total_cards = Decimal(wallet.get("sports_cards", 0) + wallet.get("mtg_cards", 0))
            if total_cards > 0:
                card_prop = amt / (total_cards * CARD_USD_VALUE)
                wallet["sports_cards"] -= int(wallet.get("sports_cards", 0) * card_prop)
                wallet["mtg_cards"] -= int(wallet.get("mtg_cards", 0) * card_prop)
        elif resource_name in ["sports_cards", "mtg_cards"]:
            if wallet.get(resource_name, 0) < int(amt):
                print(f"⚠️ Not enough {resource_name} balance.")
                return
            wallet[resource_name] -= int(amt)
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
        elif resource_name in ["sports_cards", "mtg_cards"]:
            target[resource_name] = target.get(resource_name, 0) + int(amt)
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

        if resource_name in ["sports_cards", "mtg_cards"]:
            int_amt = int(amt)
            if wallet.get(resource_name, 0) < int_amt:  
                print(f"⚠️ Not enough {resource_name} balance.")  
                return  
            wallet[resource_name] -= int_amt
            donation_wallet[resource_name] = donation_wallet.get(resource_name, 0) + int_amt
            hash_power_gain = Decimal(int_amt) * Decimal("100")  # Arbitrary gain for cards
        else:
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

# --- Withdrawal Functions (unchanged) ---

def load_withdrawal_requests():
    if os.path.exists(WITHDRAWAL_REQUESTS_FILE):
        with open(WITHDRAWAL_REQUESTS_FILE, "r") as f:
            return json.load(f)
    return []

def save_withdrawal_requests(requests):
    with open(WITHDRAWAL_REQUESTS_FILE, "w") as f:
        json.dump(requests, f, indent=4)

def request_cash_out(wallet):
    if wallet['watts_token'] < PAYOUT_THRESHOLD_USD:
        print(f"⚠️ You need at least ${PAYOUT_THRESHOLD_USD} in Watts Token to cash out. Current: ${wallet['watts_token']}")
        return

    if not wallet.get('btc_address'):
        print("⚠️ No BTC address set. Please set one first using option 20.")
        return

    wallet['watts_token'] -= PAYOUT_THRESHOLD_USD
    save_wallet(wallet)

    requests = load_withdrawal_requests()
    request = {
        "wallet_id": wallet['wallet_id'],
        "node_id": wallet['node_id'],
        "btc_address": wallet['btc_address'],
        "amount": float(PAYOUT_THRESHOLD_USD),
        "timestamp": time.time()
    }
    requests.append(request)
    save_withdrawal_requests(requests)

    donation_wallet = load_wallet(DONATION_WALLET_ID)
    if donation_wallet:
        donation_wallet['watts_token'] += PAYOUT_THRESHOLD_USD
        save_wallet(donation_wallet)

    print(f"✅ Cash-out request for ${PAYOUT_THRESHOLD_USD} sent to admin. It will be processed to your BTC address: {wallet['btc_address']}")

def view_withdrawal_requests():
    requests = load_withdrawal_requests()
    if not requests:
        print("No withdrawal requests pending.")
        return

    print("\n--- Pending Withdrawal Requests ---")
    for req in requests:
        print(f"Wallet ID: {req['wallet_id']}")
        print(f"Node ID: {req['node_id']}")
        print(f"BTC Address: {req['btc_address']}")
        print(f"Amount: ${req['amount']}")
        print(f"Timestamp: {time.ctime(req['timestamp'])}")
        print("-----------------------------")

# --- Updated Card Balance and Trading Menu ---

def show_card_balances(wallet):
    print(f"\n--- Trading Card Balances ---")
    print(f"🎴 Sports Cards: {wallet.get('sports_cards', 0)} (Value: ${format_large_number(Decimal(wallet.get('sports_cards', 0)) * CARD_USD_VALUE)})")
    print(f"🎴 MTG Cards: {wallet.get('mtg_cards', 0)} (Value: ${format_large_number(Decimal(wallet.get('mtg_cards', 0)) * CARD_USD_VALUE)})")
    print(f"Total Cards Value: ${format_large_number(calculate_total_usd(wallet) - (wallet.get('capsule_value_mb', Decimal("0")) * MB_USD_RATE + ... ))}")  # Simplified

def card_trading_menu(wallet):
    while True:
        show_card_balances(wallet)
        print("\n--- Card Actions ---")
        print("1. Trade Cards to Another Wallet")
        print("2. View Transaction History")
        print("3. Ship Cards for Physical Delivery")
        print("4. Back to Wallet Menu")
        choice = input("Enter option: ").strip()
        if choice == "1":
            target_id = input("Enter target Wallet ID: ").strip()
            sports_amt = int(input("Sports cards to trade: ").strip() or 0)
            mtg_amt = int(input("MTG cards to trade: ").strip() or 0)
            trade_cards(wallet, target_id, sports_amt, mtg_amt)
        elif choice == "2":
            txs = load_transactions()
            print("\n--- Transaction History ---")
            for tx in txs[-10:]:  # Last 10
                print(f"From {tx['from_wallet']} to {tx['to_wallet']}: {tx['sports']} Sports + {tx['mtg']} MTG ({time.ctime(tx['timestamp'])})")
        elif choice == "3":
            total_cards = int(input("Total cards to ship: ").strip())
            location = input("Location (USA/Overseas): ").strip()
            process_shipping_payment(wallet, total_cards, location)
        elif choice == "4":
            break
        else:
            print("Invalid option.")

# --- Wallet Selection (unchanged) ---

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

# --- Updated Rig Dashboard with Cards ---

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
    print(f"🎴 Sports Cards: {wallet.get('sports_cards', 0)}")  
    print(f"🎴 MTG Cards: {wallet.get('mtg_cards', 0)}")  
    print(f"🔋 Watts Token: {format_large_number(wallet.get('watts_token', Decimal('0')))} USD")  
    print(f"💵 WATTS USD Value: ${format_large_number(total_usd)}")  
    print("-" * 40)  

    if wallet['wallet_id'] == WORLD_DEBT_WALLET_ID:  
        total_debt_paid_usd = calculate_total_usd(wallet)  
        print(f"🌎 Total Debt Paid: ${format_large_number(total_debt_paid_usd)} (This Wallet's USD Value)")  
    elif wallet['wallet_id'] != DONATION_WALLET_ID:  
        print(f"🌎 World Debt Contributed: ${format_large_number(wallet['world_debt_paid_usd'])}")  
    print("-" * 40)

# --- Internet Terminal Integration (unchanged) ---

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

# --- Receive Info (unchanged) ---

def show_receive_info(wallet):
    print("\n--- Receive Info ---")
    print(f"Wallet ID (for receiving resources): {wallet['wallet_id']}")
    print(f"Node ID (for network interactions): {wallet['node_id']}")
    print("Share these to receive transfers.")
    input("Press Enter to continue...")

# --- Device Cache Scanner (unchanged) ---

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

# --- Rig Info Export (updated) ---

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
        "sports_cards": wallet.get('sports_cards', 0),
        "mtg_cards": wallet.get('mtg_cards', 0),
        "rig_hash_power": float(wallet.get('rig_hash_power', BASE_HASH_POWER)),
        "world_debt_paid_usd": float(wallet.get('world_debt_paid_usd', Decimal("0"))),
        "watts_token": float(wallet.get('watts_token', Decimal("0"))),
        "btc_address": wallet.get('btc_address', ""),
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
    print("  6. Watts Token")
    print("  7. Sports Cards")
    print("  8. MTG Cards")
    print("  9. Watts USD (calculated)")
    print(" 10. Cancel")
    choice = input("Enter option: ").strip()

    resource_map = {  
        "1": "capsule_value_mb",  
        "2": "cache_value_mb",  
        "3": "real_kwh",  
        "4": "bandwidth_MBps",  
        "5": "torrent_value_mb",  
        "6": "watts_token",  
        "7": "sports_cards",
        "8": "mtg_cards",
        "9": "usd_value"  
    }  

    if choice == "10":  
        print("🛑 Cancelled.")  
        return  

    resource_key = resource_map.get(choice)  
    if not resource_key:  
        print("⚠️ Invalid selection.")  
        return  

    try:  
        amt_str = input(f"\nEnter amount of {resource_key.replace('_',' ')} to export: ").strip()  
        amt = Decimal(amt_str)  
        if amt <= 0:  
            print("⚠️ Must be greater than zero.")  
            return  
    except:  
        print("❌ Invalid number format.")  
        return  

    if resource_key == "usd_value":  
        available = calculate_total_usd(wallet)  
    elif resource_key in ["sports_cards", "mtg_cards"]:
        available = wallet.get(resource_key, 0)
        amt = int(amt)
    else:  
        available = wallet.get(resource_key, Decimal("0"))  

    if amt > available:  
        print(f"⚠️ Not enough balance. Max available: {format_large_number(available)}")  
        return  

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

# --- World Debt Payment Plan (unchanged) ---

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
    # Pro-rate cards
    total_card_value = (Decimal(wallet.get("sports_cards", 0)) + Decimal(wallet.get("mtg_cards", 0))) * CARD_USD_VALUE
    if total_card_value > 0:
        card_prop = amt / total_card_value
        wallet["sports_cards"] -= int(Decimal(wallet.get("sports_cards", 0)) * card_prop)
        wallet["mtg_cards"] -= int(Decimal(wallet.get("mtg_cards", 0)) * card_prop)
    wallet['world_debt_paid_usd'] += amt  

    debt_wallet = load_wallet(WORLD_DEBT_WALLET_ID)  
    if debt_wallet:  
        debt_wallet['capsule_value_mb'] += amt / MB_USD_RATE  
        debt_wallet['torrent_value_mb'] += amt / MB_USD_RATE  
        save_wallet(debt_wallet)  

    save_wallet(wallet)  
    print(f"✅ Contributed ${format_large_number(amt)} to World Debt Wallet.")  
    print("🌍 Your node has been logged as a symbolic contributor to planetary debt reduction.")

# --- Updated Wallet Transaction Menu with Cards ---

def wallet_transaction_menu(wallet):
    while True:
        wallet = load_wallet(wallet['wallet_id'])
        if not wallet:
            break

        show_rig_dashboard(wallet)  
        
        print("\n--- Wallet Actions ---")  
        print("  1. Send Capsule MB")  
        print("  2. Send Cache MB")  
        print("  3. Send kWh")  
        print("  4. Send Bandwidth")  
        print("  5. Send Watts USD")  
        print("  6. Send Torrent MB")  
        print("  7. Send Watts Token")  
        print("  8. Send Sports Cards")  
        print("  9. Send MTG Cards")  
        print("  ----------------------------------------")  
        print(" 10. Donate Capsule MB to Creator (Gain Hash Power)")  
        print(" 11. Donate Cache MB to Creator (Gain Hash Power)")  
        print(" 12. Donate kWh to Creator (Gain Hash Power)")  
        print(" 13. Donate Bandwidth to Creator (Gain Hash Power)")  
        print(" 14. Donate Torrent MB to Creator (Gain Hash Power)")  
        print(" 15. Donate Watts Token to Creator (Gain Hash Power)")  
        print(" 16. Donate Sports Cards to Creator (Gain Hash Power)")  
        print(" 17. Donate MTG Cards to Creator (Gain Hash Power)")  
        print("  ----------------------------------------")  
        print(" 18. View Receive Info (Wallet/Node IDs)")  
        print(" 19. Download Resource to File")  
        print(" 20. Everything About the Rig (Download Info)")  
        print(" 21. World Debt Payment Plan 🌎")  
        print(" 22. Back to Main Menu")  
        print(" 23. Access Internet Terminal (Node-Linked)")  
        print(" 24. Set BTC Wallet Address")  
        print(" 25. Cash Out Watts Token (if >= $5)")  
        print(" 26. Trading Card Menu")  
        if wallet['wallet_id'] == DONATION_WALLET_ID:
            print(" 27. View Withdrawal Requests (Admin Only)")  
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
            send_resource(wallet, "watts_token")  
        elif option == "8":  
            send_resource(wallet, "sports_cards")  
        elif option == "9":  
            send_resource(wallet, "mtg_cards")  
        elif option == "10":  
            donate_for_hash(wallet, "capsule_value_mb")  
        elif option == "11":  
            donate_for_hash(wallet, "cache_value_mb")  
        elif option == "12":  
            donate_for_hash(wallet, "real_kwh")  
        elif option == "13":  
            donate_for_hash(wallet, "bandwidth_MBps")  
        elif option == "14":  
            donate_for_hash(wallet, "torrent_value_mb")  
        elif option == "15":  
            donate_for_hash(wallet, "watts_token")  
        elif option == "16":  
            donate_for_hash(wallet, "sports_cards")  
        elif option == "17":  
            donate_for_hash(wallet, "mtg_cards")  
        elif option == "18":  
            show_receive_info(wallet)  
        elif option == "19":  
            enhanced_download_resource_menu(wallet)  
        elif option == "20":  
            show_rig_download_info(wallet)  
        elif option == "21":  
            if wallet['wallet_id'] in [DONATION_WALLET_ID, WORLD_DEBT_WALLET_ID]:  
                print("🛑 Cannot access the World Debt Payment Plan menu from a system wallet.")  
            else:  
                show_world_debt_payment_menu(wallet)  
        elif option == "22": 
            break  
        elif option == "23":  
            print(f"🌐 Launching Internet Terminal for Node: {wallet['node_id']}")  
            run_internet_terminal(wallet)  
        elif option == "24":  
            print("Help: Add wallet for BTC. Reach $5 in Watts Token to cash out.")
            btc_addr = input("Enter your BTC wallet address for payouts: ").strip()
            wallet['btc_address'] = btc_addr
            save_wallet(wallet)
            print(f"✅ BTC address set to {btc_addr}")
        elif option == "25":  
            request_cash_out(wallet)
        elif option == "26":
            card_trading_menu(wallet)
        elif option == "27" and wallet['wallet_id'] == DONATION_WALLET_ID:  
            view_withdrawal_requests()
        else:  
            print("⚠️ Invalid option.")

# --- Mining Start (unchanged) ---

def start_mining(mining_type):
    wallet = select_wallet_for_mining()
    if wallet:
        print(f"Starting {mining_type.upper()} Mining for wallet {wallet['wallet_id']}...")
        unified_mining_loop(wallet, mining_type)

# --- Wallet View Menu (unchanged) ---

def view_wallets_rigs_menu():
    wallet = select_wallet_or_rig()
    if wallet:
        wallet_transaction_menu(wallet)

# --- Main Menu (updated with card info) ---

def main_menu():
    global AD_URL
    _initialize_special_wallets()
    world_debt_node_value_generation()

    while True:  
        print("\n=== Manierism Megabytes Mining Menu ===")  
        print("1. Start Kinetic Mining (Select Rig)")  
        print("2. Start Wi-Fi Mining (Select Rig)")  
        print("3. Start SHA Capsule Mining (Select Rig)")  
        print("4. Start Cache Mining (Select Rig)")  
        print("5. Play Blackjack (Bet Files)🃏") 
        print("6. Create New Rig / Wallet")  
        print("7. View Wallets & Rigs / Wallet Actions")  
        print("8. Exit")  
        choice = input("Enter option (1-8): ").strip()  

        world_debt_node_value_generation()  

        if choice == "1":  
            start_mining("kinetic")  
        elif choice == "2":  
            start_mining("wifi")  
        elif choice == "3":  
            start_mining("sha")  
        elif choice == "4":  
            start_mining("cache")  
        elif choice == "5": 
            rig_id = input("Enter Rig ID (Wallet Name) to use for betting: ").strip()  
            wallet_to_use = load_wallet(rig_id) or load_wallet(f"{rig_id}")
            if not wallet_to_use:
                print(f"⚠️ Wallet/Rig '{rig_id}' not found.")
            else:
                blackjack_game(wallet_to_use) 
        elif choice == "6":  
            rig_id = input("Enter Rig ID or Wallet Name: ").strip()  
            wallet_id = input("Enter Wallet ID: ").strip()  
            new_wallet = create_wallet(wallet_id, rig_id)  
            if new_wallet:  
                print(f"✅ Created new wallet/rig: {rig_id} ({wallet_id}) with Node ID: {new_wallet['node_id']}")
                btc_addr = input("Enter your BTC wallet address for payouts (optional): ").strip()
                if btc_addr:
                    new_wallet['btc_address'] = btc_addr
                    save_wallet(new_wallet)
                    print(f"✅ BTC address set to {btc_addr}")
        elif choice == "7":  
            view_wallets_rigs_menu()
        elif choice == "8":
            print("Exiting... 👋 See you later F&F ❤️")
            break
        else:
            print("⚠️ Invalid selection.")

# --- Runtime Launch ---

if __name__ == "__main__":
    main_menu()
