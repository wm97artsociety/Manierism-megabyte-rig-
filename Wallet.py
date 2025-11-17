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
