# === Patch preventiva per GitHub Actions (namespace datapizza) ===
import sys, types, importlib

try:
    import datapizza.clients.openai_like
except ModuleNotFoundError:
    try:
        pkg = importlib.import_module("datapizza_ai_clients_openai_like")
        sys.modules["datapizza"] = types.ModuleType("datapizza")
        sys.modules["datapizza.clients"] = types.ModuleType("datapizza.clients")
        sys.modules["datapizza.clients.openai_like"] = pkg
        print("⚙️ [PATCH] Namespace 'datapizza.clients.openai_like' creato dinamicamente.")
    except Exception as inner_e:
        print(f"❌ Patch datapizza fallita: {inner_e}")
# ================================================================

import os
import requests
import json
import random
from datapizza.agents import Agent
from datapizza.tools import tool

# === Variabili d'ambiente (da GitHub Secrets o da telegram.env in locale) ===
if os.path.exists("telegram.env"):
    from dotenv import load_dotenv
    load_dotenv("telegram.env")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"  # 🧠 controlla se usare LLM

REPO = "datapizza-labs/datapizza-ai"
CACHE_FILE = "last_commit.json"


# === Utility: cache commit ===
def load_last_commit():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return None


def save_last_commit(sha):
    with open(CACHE_FILE, "w") as f:
        json.dump({"sha": sha}, f)


# === Utility: invio messaggi Telegram ===
def send_telegram_message(text: str, parse_mode: str = "HTML"):
    if not TOKEN or not CHAT_ID:
        print("⚠️ Variabili TELEGRAM_TOKEN o TELEGRAM_CHAT_ID mancanti.")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ Errore Telegram: {e}")


# === Tool: controllo commit ===
@tool
def check_repo_updates(**kwargs) -> str:
    """Controlla nuovi commit e notifica su Telegram."""
    try:
        url = kwargs.get("url", f"https://api.github.com/repos/{REPO}/commits/main")
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()

        # Fix: l'API può restituire lista invece di oggetto
        if isinstance(data, list):
            data = data[0]

        if "commit" not in data:
            return "⚠️ Risposta inaspettata da GitHub"

        commit_sha = data["sha"]
        last_commit = load_last_commit()

        # Se non ci sono novità → esce
        if last_commit and last_commit["sha"] == commit_sha:
            print("✅ Nessun nuovo commit")
            return "✅ Nessun nuovo commit"

        # Nuovo commit → prepara messaggio
        msg = data["commit"]["message"]
        author = data["commit"]["author"]["name"]
        date = data["commit"]["author"]["date"]
        url_commit = f"https://github.com/{REPO}/commit/{commit_sha}"

        jokes = [
            "🍕 Fresco di forno!",
            "🔥 Un nuovo commit appena sfornato!",
            "😎 Aggiornamento servito caldo!",
            "🧠 Gli chef AI sono tornati al lavoro!",
            "🚨 Allarme commit fresco!",
        ]
        emoji_map = {
            "feat": "✨", "fix": "🐛", "docs": "📚",
            "style": "🎨", "refactor": "♻️", "perf": "⚡", "test": "🧪",
        }

        emoji = "💾"
        for k, e in emoji_map.items():
            if msg.lower().startswith(k):
                emoji = e
                break

        text = (
            f"{random.choice(jokes)}\n\n"
            f"<b>{emoji} Nuovo Commit</b>\n"
            f"👨‍💻 <b>Autore:</b> {author}\n"
            f"🕐 <b>Data:</b> {date}\n"
            f"💬 <b>Messaggio:</b> <code>{msg}</code>\n"
            f"🔗 <a href='{url_commit}'>Visualizza su GitHub</a>"
        )

        send_telegram_message(text)
        save_last_commit(commit_sha)
        return f"✅ Nuova notifica inviata: {msg}"

    except Exception as e:
        send_telegram_message(f"❌ Errore: {e}")
        return f"❌ Errore: {e}"


# === Tool: statistiche repo ===
@tool
def get_repo_stats(**kwargs) -> str:
    try:
        r = requests.get(f"https://api.github.com/repos/{REPO}", timeout=10)
        r.raise_for_status()
        d = r.json()
        stats = (
            f"📊 <b>Statistiche Repo</b>\n\n"
            f"⭐ <b>Stars:</b> {d['stargazers_count']}\n"
            f"🔀 <b>Forks:</b> {d['forks_count']}\n"
            f"👀 <b>Watchers:</b> {d['watchers_count']}\n"
            f"📝 <b>Issues:</b> {d['open_issues_count']}\n"
            f"📦 <b>Linguaggio:</b> {d['language']}\n"
            f"📅 <b>Ultimo update:</b> {d['updated_at']}"
        )
        send_telegram_message(stats)
        return stats
    except Exception as e:
        return f"❌ Errore stats: {e}"


# === Client Datapizza (solo se USE_LLM è true) ===
# === Client Datapizza (solo se USE_LLM è true) ===
if USE_LLM:
    from datapizza.clients.openai_like import OpenAILikeClient
    client = OpenAILikeClient(
        api_key="",
        base_url="http://localhost:11434/v1",
        model="llama3.2",
        system_prompt="You are a funny assistant that announces repo updates humorously."
    )
    print("🤖 Modalità LLM attiva: uso Ollama locale.")
else:

    # ✅ Dummy client per GitHub Actions con interfaccia completa
    class DummyResponse:
        def __init__(self, text="LLM disattivato su CI."):
            self.text = text
            self.function_calls = []  # richiesto da Agent
            self.messages = []  # opzionale ma utile per coerenza
            self.raw = {"status": "ok", "source": "DummyClient"}


    class DummyClient:
        def invoke(self, *args, **kwargs):
            print("🧩 DummyClient.invoke() chiamato (LLM disabilitato).")
            return DummyResponse()


    client = DummyClient()
    print("🌐 Modalità CI attiva: LLM disabilitato (uso DummyClient compatibile).")

# === Crea l'agente Datapizza ===
agent = Agent(name="repo-watcher", client=client, tools=[check_repo_updates, get_repo_stats])


# === Esecuzione principale ===
if __name__ == "__main__":
    print("🚀 Starting Datapizza Repo Watcher Bot...")

    # Controlla aggiornamenti e statistiche (una sola esecuzione)
    agent.run("Check if something new happened on the Datapizza AI repo")
    agent.run("Get the repository statistics")
