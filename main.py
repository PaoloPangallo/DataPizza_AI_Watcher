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
from datetime import datetime, timedelta
from datapizza.agents import Agent
from datapizza.tools import tool

# === Variabili d'ambiente ===
if os.path.exists("telegram.env"):
    from dotenv import load_dotenv
    load_dotenv("telegram.env")

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"
RUN_MODE = os.getenv("RUN_MODE", "auto")

REPO = "datapizza-labs/datapizza-ai"
CACHE_FILE = "last_commit.json"
HISTORY_FILE = "commit_history.json"
STATS_FILE = "repo_stats.json"

# Configurazione notifiche
IMPORTANT_TYPES = {"feat", "fix", "security"}  # Notifica solo questi
QUIET_TYPES = {"docs", "style", "refactor", "test", "chore"}  # Accumula questi
DIGEST_DAY = 3  # Giovedì (0=lunedì, 6=domenica)


# === Utility: cache e history ===
def load_json_file(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def save_json_file(filepath, data):
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️ Errore salvataggio {filepath}: {e}")


def load_last_commit():
    return load_json_file(CACHE_FILE) or {"sha": None}


def save_last_commit(sha):
    save_json_file(CACHE_FILE, {"sha": sha})


def load_commit_history():
    return load_json_file(HISTORY_FILE) or {"commits": [], "stats": {}}


def save_commit_history(history):
    save_json_file(HISTORY_FILE, history)


def load_repo_stats():
    return load_json_file(STATS_FILE) or {}


def save_repo_stats(stats):
    save_json_file(STATS_FILE, stats)


def should_send_digest():
    """Controlla se è il giorno per il digest settimanale."""
    today = datetime.now().weekday()
    return today == DIGEST_DAY


def get_commit_type(msg):
    """Estrae il tipo di commit (feat, fix, docs, etc)."""
    msg_lower = msg.lower().split(":")[0].strip()
    for commit_type in IMPORTANT_TYPES | QUIET_TYPES | {"other"}:
        if msg_lower.startswith(commit_type):
            return commit_type
    return "other"


def is_important_commit(commit_type):
    """Controlla se il commit è importante."""
    return commit_type in IMPORTANT_TYPES


# === Invio messaggi Telegram ===
def send_telegram_message(text: str, parse_mode: str = "HTML"):
    if not TOKEN or not CHAT_ID:
        print("⚠️ Telegram non configurato.")
        return False
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
        return True
    except Exception as e:
        print(f"❌ Errore Telegram: {e}")
        return False


# === Tool: controllo commit intelligente ===
@tool
def check_repo_updates(**kwargs) -> str:
    """Controlla nuovi commit con notifiche intelligenti."""
    try:
        url = f"https://api.github.com/repos/{REPO}/commits/main"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()

        if isinstance(data, list) and data:
            data = data[0]

        if not isinstance(data, dict) or "commit" not in data:
            return "⚠️ Risposta GitHub inaspettata"

        commit_sha = data.get("sha")
        last_commit = load_last_commit()
        history = load_commit_history()

        # Nessun nuovo commit
        if last_commit.get("sha") == commit_sha:
            print("✅ Nessun nuovo commit")
            return "✅ Nessun nuovo commit"

        # Nuovo commit rilevato
        msg = data["commit"]["message"].split("\n")[0]  # Prima riga
        author = data["commit"]["author"]["name"]
        date = data["commit"]["author"]["date"]
        url_commit = f"https://github.com/{REPO}/commit/{commit_sha}"
        commit_type = get_commit_type(msg)

        # Aggiungi a history
        commit_entry = {
            "sha": commit_sha,
            "message": msg,
            "author": author,
            "date": date,
            "type": commit_type,
            "url": url_commit
        }
        history["commits"].insert(0, commit_entry)
        history["commits"] = history["commits"][:100]  # Mantieni ultimi 100

        # Aggiorna stats
        if author not in history["stats"]:
            history["stats"][author] = 0
        history["stats"][author] += 1

        save_commit_history(history)
        save_last_commit(commit_sha)

        # Decidi se notificare
        if is_important_commit(commit_type):
            # Notifica immediata per commit importanti
            emoji_map = {
                "feat": "✨", "fix": "🐛", "security": "🔒",
                "docs": "📚", "style": "🎨", "refactor": "♻️",
                "perf": "⚡", "test": "🧪", "other": "💾"
            }
            emoji = emoji_map.get(commit_type, "💾")

            jokes = [
                "🍕 Fresco di forno!",
                "🔥 Un nuovo commit appena sfornato!",
                "😎 Aggiornamento servito caldo!",
                "🧠 Gli chef AI sono tornati al lavoro!",
                "🚨 Allarme commit fresco!",
            ]

            text = (
                f"{random.choice(jokes)}\n\n"
                f"<b>{emoji} {commit_type.upper()}</b>\n"
                f"👨‍💻 <b>Autore:</b> {author}\n"
                f"💬 <b>Messaggio:</b> <code>{msg}</code>\n"
                f"🔗 <a href='{url_commit}'>Visualizza su GitHub</a>"
            )
            send_telegram_message(text)
            return f"✅ Notifica inviata: {commit_type} - {msg}"
        else:
            # Commit non importante - accumula silenziosamente
            print(f"📝 Commit {commit_type} accumulato (non notificato): {msg}")
            return f"📝 Commit {commit_type} accumulato"

    except Exception as e:
        err_msg = f"❌ Errore check_repo_updates: {e}"
        print(err_msg)
        return err_msg


# === Tool: digest settimanale ===
@tool
def send_weekly_digest(**kwargs) -> str:
    """Invia un digest settimanale se è il giorno giusto."""
    try:
        if not should_send_digest():
            print(f"📅 Non è il giorno del digest (oggi è {datetime.now().strftime('%A')})")
            return "📅 Non è il giorno del digest"

        history = load_commit_history()
        if not history["commits"]:
            return "📋 Nessun commit nella storia"

        # Filtra commit della scorsa settimana
        week_ago = datetime.now() - timedelta(days=7)
        weekly_commits = []
        for commit in history["commits"]:
            commit_date = datetime.fromisoformat(commit["date"].replace("Z", "+00:00"))
            if commit_date > week_ago:
                weekly_commits.append(commit)

        if not weekly_commits:
            return "📋 Nessun commit nella scorsa settimana"

        # Conta per tipo
        type_counts = {}
        for commit in weekly_commits:
            c_type = commit["type"]
            type_counts[c_type] = type_counts.get(c_type, 0) + 1

        # Top autori
        author_counts = {}
        for commit in weekly_commits:
            author = commit["author"]
            author_counts[author] = author_counts.get(author, 0) + 1
        top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:3]

        # Costruisci messaggio
        type_str = "\n".join([f"  {ct}: {count}" for ct, count in sorted(type_counts.items())])
        authors_str = "\n".join([f"  👤 {author}: {count}" for author, count in top_authors])

        text = (
            f"📊 <b>DIGEST SETTIMANALE</b>\n\n"
            f"📈 <b>Commit della scorsa settimana:</b> {len(weekly_commits)}\n\n"
            f"<b>Per tipo:</b>\n{type_str}\n\n"
            f"<b>Top Autori:</b>\n{authors_str}"
        )

        send_telegram_message(text)
        return f"✅ Digest inviato: {len(weekly_commits)} commit"

    except Exception as e:
        return f"❌ Errore digest: {e}"


# === Tool: statistiche repo ===
@tool
def get_repo_stats(**kwargs) -> str:
    """Recupera e invia statistiche del repository."""
    try:
        r = requests.get(f"https://api.github.com/repos/{REPO}", timeout=10)
        r.raise_for_status()
        d = r.json()

        stats = {
            "stars": d['stargazers_count'],
            "forks": d['forks_count'],
            "watchers": d['watchers_count'],
            "issues": d['open_issues_count'],
            "language": d['language'],
            "updated_at": d['updated_at']
        }

        # Salva per confronti futuri
        old_stats = load_repo_stats()
        if old_stats:
            stars_delta = stats["stars"] - old_stats.get("stars", 0)
            issues_delta = stats["issues"] - old_stats.get("issues", 0)
            deltas = f"\n⭐ Variazione: {'+' if stars_delta >= 0 else ''}{stars_delta} stelle\n📝 Variazione: {'+' if issues_delta >= 0 else ''}{issues_delta} issues"
        else:
            deltas = ""

        save_repo_stats(stats)

        text = (
            f"📊 <b>Statistiche Repo</b>\n\n"
            f"⭐ <b>Stars:</b> {stats['stars']}\n"
            f"🔀 <b>Forks:</b> {stats['forks']}\n"
            f"👀 <b>Watchers:</b> {stats['watchers']}\n"
            f"📝 <b>Issues:</b> {stats['issues']}\n"
            f"📦 <b>Linguaggio:</b> {stats['language']}\n"
            f"📅 <b>Ultimo update:</b> {stats['updated_at']}"
            f"{deltas}"
        )

        send_telegram_message(text)
        return text

    except Exception as e:
        return f"❌ Errore stats: {e}"


# === LLM Client Setup ===
def setup_llm_client():
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
            print("✅ Ollama disponibile.")
            return client
    except Exception as e:
        print(f"⚠️ Ollama non raggiungibile: {e}")

    return None


def detect_mode(client_available):
    if RUN_MODE == "direct":
        return "direct"
    elif RUN_MODE == "agent":
        return "agent" if client_available else "direct"
    else:
        if os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true":
            return "direct"
        return "agent" if client_available else "direct"


# === Main ===
if __name__ == "__main__":
    print("🚀 Datapizza Repo Watcher avviato...\n")

    try:
        llm_client = setup_llm_client()
        mode = detect_mode(llm_client is not None)
        print(f"📌 Modalità: {mode.upper()}\n")

        if mode == "agent" and llm_client:
            print("🤖 Avvio Agent con LLM...\n")
            agent = Agent(
                name="repo-watcher",
                client=llm_client,
                tools=[check_repo_updates, send_weekly_digest, get_repo_stats]
            )
            try:
                agent.run("Check for new commits and send digest if needed", max_iterations=5)
            except TypeError:
                agent.run("Check for new commits and send digest if needed")
        else:
            print("🔧 Esecuzione diretta tool...\n")

            print("📋 Task 1: Controllo aggiornamenti intelligente...")
            result1 = check_repo_updates()
            print(f"Risultato: {result1}\n")

            print("📋 Task 2: Digest settimanale (se dovuto)...")
            result2 = send_weekly_digest()
            print(f"Risultato: {result2}\n")

            print("📋 Task 3: Statistiche repo...")
            result3 = get_repo_stats()
            print(f"Risultato: {result3}\n")

        print("✅ Watcher completato!")

    except Exception as e:
        print(f"\n❌ Errore critico: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)