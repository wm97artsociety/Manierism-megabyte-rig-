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
