#!/usr/bin/env python3
# === Patch preventiva per GitHub Actions (namespace datapizza) ===
import sys
import types
import importlib

try:
    import datapizza.clients.openai_like
    print("✅ datapizza.clients.openai_like importato correttamente")
except (ModuleNotFoundError, ImportError, AttributeError):
    try:
        pkg = importlib.import_module("datapizza_ai_clients_openai_like")
        sys.modules["datapizza"] = types.ModuleType("datapizza")
        sys.modules["datapizza.clients"] = types.ModuleType("datapizza.clients")
        sys.modules["datapizza.clients.openai_like"] = pkg
        print("⚙️ [PATCH] Namespace 'datapizza.clients.openai_like' creato dinamicamente.")
    except Exception as inner_e:
        print(f"⚠️ Patch datapizza fallito: {inner_e}")

import os
import json
import random
import requests
from datapizza.agents import Agent
from datapizza.tools import tool

# === Variabili d'ambiente ===
if os.path.exists("telegram.env"):
    from dotenv import load_dotenv
    load_dotenv("telegram.env")

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"
RUN_MODE = os.getenv("RUN_MODE", "auto")  # "auto", "agent", "direct"

REPO = "datapizza-labs/datapizza-ai"
CACHE_FILE = "last_commit.json"


# === Utility: cache commit ===
def load_last_commit():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def save_last_commit(sha):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump({"sha": sha}, f)
    except Exception as e:
        print(f"⚠️ Errore salvataggio cache: {e}")


# === Invio messaggi Telegram ===
def send_telegram_message(text: str, parse_mode: str = "HTML"):
    if not TOKEN or not CHAT_ID:
        print("⚠️ Telegram non configurato (variabili mancanti).")
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
        print("✅ Messaggio Telegram inviato.")
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

        if isinstance(data, list) and data:
            data = data[0]

        if not isinstance(data, dict) or "commit" not in data:
            return "⚠️ Risposta inaspettata da GitHub"

        commit_sha = data.get("sha")
        last_commit = load_last_commit()

        if last_commit and last_commit.get("sha") == commit_sha:
            print("✅ Nessun nuovo commit")
            return "✅ Nessun nuovo commit"

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
        return f"✅ Notifica inviata: {msg}"

    except Exception as e:
        err_msg = f"❌ Errore: {e}"
        send_telegram_message(err_msg)
        return err_msg


# === Tool: statistiche repo ===
@tool
def get_repo_stats(**kwargs) -> str:
    """Recupera e invia statistiche del repository."""
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


# === LLM Client Setup ===
def setup_llm_client():
    """Configura client LLM: Ollama se disponibile, altrimenti None."""
    if not USE_LLM:
        return None

    print("🧠 Tentativo connessione a Ollama...")
    try:
        probe = requests.get("http://localhost:11434/api/tags", timeout=2)
        if probe.status_code == 200:
            from datapizza.clients.openai_like import OpenAILikeClient
            client = OpenAILikeClient(
                api_key="",
                base_url="http://localhost:11434/v1",
                model="llama3.2",
                system_prompt="You are a helpful assistant that announces repository updates humorously."
            )
            print("✅ Ollama disponibile e connesso.")
            return client
        else:
            print("⚠️ Ollama non risponde.")
    except Exception as e:
        print(f"⚠️ Ollama non raggiungibile: {e}")

    return None


# === Execution mode detection ===
def detect_mode(client_available):
    """Rileva il modalità di esecuzione."""
    if RUN_MODE == "direct":
        return "direct"
    elif RUN_MODE == "agent":
        return "agent" if client_available else "direct"
    else:  # "auto"
        # In CI (GitHub Actions), usa direct
        if os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true":
            return "direct"
        # Localmente, usa agent se LLM disponibile
        return "agent" if client_available else "direct"


# === Main ===
if __name__ == "__main__":
    print("🚀 Datapizza Repo Watcher avviato...\n")

    try:
        # Setup LLM
        llm_client = setup_llm_client()

        # Rileva modalità
        mode = detect_mode(llm_client is not None)
        print(f"📌 Modalità: {mode.upper()}")
        if mode == "agent":
            print(f"   → Agent con LLM reale (Ollama)")
        else:
            print(f"   → Esecuzione diretta dei tool\n")

        if mode == "agent" and llm_client:
            # === MODALITÀ AGENT (con LLM reale) ===
            print("🤖 Avvio Agent con LLM...\n")

            agent = Agent(
                name="repo-watcher",
                client=llm_client,
                tools=[check_repo_updates, get_repo_stats]
            )

            # Custom max_iterations per evitare loop infiniti
            print("📋 Task 1: Controllo aggiornamenti...")
            try:
                agent.run(
                    "Check if something new happened on the Datapizza AI repo",
                    max_iterations=5
                )
            except TypeError:
                # Se max_iterations non supportato, esegui senza
                agent.run("Check if something new happened on the Datapizza AI repo")

            print("\n📋 Task 2: Statistiche repo...")
            try:
                agent.run(
                    "Get the repository statistics",
                    max_iterations=5
                )
            except TypeError:
                agent.run("Get the repository statistics")

        else:
            # === MODALITÀ DIRECT (esecuzione diretta tool) ===
            print("🔧 Esecuzione diretta tool...\n")

            print("📋 Task 1: Controllo aggiornamenti...")
            result1 = check_repo_updates()
            print(f"Risultato: {result1}\n")

            print("📋 Task 2: Statistiche repo...")
            result2 = get_repo_stats()
            print(f"Risultato: {result2}\n")

        print("✅ Watcher completato con successo!")

    except Exception as e:
        print(f"\n❌ Errore critico: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)