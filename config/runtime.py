from config.config import ROOT

REPORTS_DIR = ROOT / "reports"

N_CTX = 4096
CLASSIFY_MAX_CHARS = 700

MODELS = {
    "phi":    {"repo_id": "bartowski/microsoft_Phi-4-mini-instruct-GGUF", "filename": "*Q4_K_M.gguf"},
    "qwen3":  {"repo_id": "bartowski/Qwen_Qwen3-4B-GGUF",   "filename": "*Q4_K_M.gguf", "empty_think": True},
    "qwen35": {"repo_id": "bartowski/Qwen_Qwen3.5-4B-GGUF", "filename": "*Q4_K_M.gguf", "empty_think": True},
}
DEFAULT_MODEL = "phi"

CATEGORY_HINTS = {
    "programming": "software, programming, IT, AI/ML, cybersecurity, tech products and gadgets",
    "economics": "economy, business, finance, markets, companies, trade, jobs",
    "design": "design, UX/UI, architecture, art, typography, creative work",
    "marketing": "marketing, advertising, SEO, branding, social media, sales",
    "science": "science, space, medical research, climate, scientific discoveries",
    "world": "politics, government, wars and conflicts, elections, society, international news",
}
