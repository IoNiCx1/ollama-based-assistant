MODEL = "qwen2.5:3b-instruct"
OLLAMA_URL = "http://localhost:11434/api/chat"
NUM_CTX = 4096

# Tier 3: every write needs your yes
TIER3_FOLDERS = [
    r"C:\Users\Omkar\Downloads",
]

# Tier 2: writes allowed without asking, logged
TIER2_FOLDERS = [
    r"C:\Users\Omkar\Desktop",
    r"C:\Users\Omkar\Documents",
    r"C:\pipe\data",
]

# Reads are allowed in both tiers
ALLOWED_FOLDERS = TIER3_FOLDERS + TIER2_FOLDERS

BLOCKED_PATHS = [
    r"C:\Windows",
    r"C:\Program Files",
    r"C:\Program Files (x86)",
]