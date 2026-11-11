from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "news.db"
SNAPSHOT_DIR = DATA_DIR / "snapshot"

SEED = 42

USER_AGENT = "Mozilla/5.0 (compatible; insightflow-ai/0.1; student course project)"
REQUEST_TIMEOUT = 15

CATEGORIES = ["programming", "economics", "design", "marketing", "science", "world"]

FEEDS = [
    # --- programming ---
    {"name": "Hacker News", "url": "https://hnrss.org/frontpage", "category": "programming"},
    {"name": "DEV.to", "url": "https://dev.to/feed", "category": "programming"},
    {"name": "GitHub Blog", "url": "https://github.blog/feed/", "category": "programming"},
    {"name": "Stack Overflow Blog", "url": "https://stackoverflow.blog/feed/", "category": "programming"},
    # --- economics ---
    {"name": "BBC Business", "url": "http://feeds.bbci.co.uk/news/business/rss.xml", "category": "economics"},
    {"name": "NYT Business", "url": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", "category": "economics"},
    # --- design ---
    {"name": "Smashing Magazine", "url": "https://www.smashingmagazine.com/feed/", "category": "design"},
    {"name": "A List Apart", "url": "https://alistapart.com/main/feed/", "category": "design"},
    {"name": "Dezeen", "url": "https://www.dezeen.com/feed/", "category": "design"},
    {"name": "NN/g", "url": "https://www.nngroup.com/feed/rss/", "category": "design"},
    # --- marketing ---
    {"name": "HubSpot Marketing", "url": "https://blog.hubspot.com/marketing/rss.xml", "category": "marketing"},
    {"name": "Neil Patel", "url": "https://neilpatel.com/blog/feed/", "category": "marketing"},
    # --- science ---
    {"name": "Nature", "url": "https://www.nature.com/nature.rss", "category": "science"},
    {"name": "ScienceDaily", "url": "https://www.sciencedaily.com/rss/all.xml", "category": "science"},
    # --- world ---
    {"name": "BBC World", "url": "http://feeds.bbci.co.uk/news/world/rss.xml", "category": "world"},
    {"name": "NYT World", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "category": "world"},
    # --- змішані (без слабкої мітки) ---
    {"name": "BBC Top Stories", "url": "http://feeds.bbci.co.uk/news/rss.xml", "category": None},
    {"name": "Guardian International", "url": "https://www.theguardian.com/international/rss", "category": None},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "category": None},
    {"name": "Ars Technica", "url": "https://arstechnica.com/feed/", "category": None},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "category": None},
]
