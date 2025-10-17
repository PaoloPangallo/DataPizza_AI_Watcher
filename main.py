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


# === Invio messaggi Telegram con stile hacker ===
def send_telegram_message(text: str, parse_mode: str = "HTML", reply_markup=None):
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
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        print("✅ Messaggio Telegram inviato.")
        return True
    except Exception as e:
        print(f"❌ Errore Telegram: {e}")
        return False


def create_hacker_buttons(url_commit):
    """Crea pulsanti interattivi stile hacker."""
    return {
        "inline_keyboard": [
            [
                {"text": "🔗 VIEW_COMMIT.exe", "url": url_commit},
                {"text": "📊 REPO_STATS", "url": f"https://github.com/{REPO}"}
            ],
            [
                {"text": "⭐ STAR_ME", "url": f"https://github.com/{REPO}"},
                {"text": "🍴 FORK_IT", "url": f"https://github.com/{REPO}/fork"}
            ]
        ]
    }


# === Tool: controllo commit intelligente ===
@tool
def check_repo_updates(**kwargs) -> str:
    """Controlla nuovi commit e invia notifiche + statistiche solo se necessario."""
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

        # 🆕 Nuovo commit rilevato
        msg = data["commit"]["message"].split("\n")[0]  # Prima riga
        author = data["commit"]["author"]["name"]
        date = data["commit"]["author"]["date"]
        url_commit = f"https://github.com/{REPO}/commit/{commit_sha}"
        commit_type = get_commit_type(msg)

        # Aggiungi alla history
        commit_entry = {
            "sha": commit_sha,
            "message": msg,
            "author": author,
            "date": date,
            "type": commit_type,
            "url": url_commit
        }
        history["commits"].insert(0, commit_entry)
        history["commits"] = history["commits"][:100]
        history["stats"][author] = history["stats"].get(author, 0) + 1

        save_commit_history(history)
        save_last_commit(commit_sha)

        # Costruisci messaggio “stile hacker”
        emoji_map = {
            "feat": "✨", "fix": "🐛", "security": "🔒",
            "docs": "📚", "style": "🎨", "refactor": "♻️",
            "perf": "⚡", "test": "🧪", "other": "💾"
        }
        emoji = emoji_map.get(commit_type, "💾")

        hacker_lines = [
            ">>> ALERT: NEW_PAYLOAD DETECTED",
            ">>> SYSTEM: CRITICAL_UPDATE INCOMING",
            ">>> STATUS: REPOSITORY_MUTATION_ACTIVE",
            ">>> SCANNER: HIGH_PRIORITY_CHANGE_FOUND",
            ">>> DAEMON: CODE_INJECTION_INITIATED",
        ]

        text = (
            f"<code>{'='*40}\n"
            f"{random.choice(hacker_lines)}\n"
            f"{'='*40}\n\n"
            f"[{commit_type.upper()}] {emoji}\n"
            f"├─ AUTHOR: {author}\n"
            f"├─ MESSAGE: {msg}\n"
            f"├─ HASH: {commit_sha[:8]}...\n"
            f"└─ TIME: {date}\n"
            f"{'='*40}</code>\n\n"
            f"<b>⚡ {emoji} New commit detected — updating stats...</b>"
        )

        buttons = create_hacker_buttons(url_commit)
        send_telegram_message(text, reply_markup=buttons)

        # 🧠 Subito dopo: invia statistiche aggiornate
        print("📊 Nuovo commit rilevato → invio statistiche aggiornate...")
        result_stats = get_repo_stats()
        print(f"📈 Statistiche inviate: {result_stats}")

        return f"✅ Notifica inviata e statistiche aggiornate: {commit_type} - {msg}"

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

        # Costruisci messaggio - STILE HACKER
        type_str = "".join([f"\n  {ct.upper()}: {count}" for ct, count in sorted(type_counts.items())])
        authors_str = "".join([f"\n  [{i+1}] {author}: {count}$" for i, (author, count) in enumerate(top_authors)])

        text = (
            f"<code>╔════════════════════════════════╗\n"
            f"║   WEEKLY_DIGEST.log [SYSTEM]    ║\n"
            f"╚════════════════════════════════╝\n\n"
            f"[SCAN_RESULTS]\n"
            f"├─ COMMITS_FOUND: {len(weekly_commits)}\n"
            f"├─ TIME_RANGE: 7_DAYS_BACK\n"
            f"├─ STATUS: ✓ ANALYSIS_COMPLETE\n\n"
            f"[COMMIT_TYPES]\n"
            f"{type_str}\n\n"
            f"[TOP_CONTRIBUTORS]\n"
            f"{authors_str}\n\n"
            f"╔════════════════════════════════╗\n"
            f"║ END_REPORT - STAY_TUNED()      ║\n"
            f"╚════════════════════════════════╝</code>"
        )
        buttons = {
            "inline_keyboard": [
                [{"text": "🔗 OPEN_REPO.exe", "url": f"https://github.com/{REPO}"}],
                [{"text": "📊 COMMITS_LOG", "url": f"https://github.com/{REPO}/commits/main"}]
            ]
        }

        send_telegram_message(text, reply_markup=buttons)
        return f"✅ Digest inviato: {len(weekly_commits)} commit"

    except Exception as e:
        return f"❌ Errore digest: {e}"


# === Tool: statistiche repo ===
@tool
def get_repo_stats(**kwargs) -> str:
    """Recupera e invia statistiche del repository in formato grafico e interattivo."""
    try:
        # === 1️⃣ Fetch info repository ===
        repo_url = f"https://api.github.com/repos/{REPO}"
        commit_url = f"https://api.github.com/repos/{REPO}/commits/main"

        repo_resp = requests.get(repo_url, timeout=10)
        repo_resp.raise_for_status()
        d = repo_resp.json()

        commit_resp = requests.get(commit_url, timeout=10)
        commit_resp.raise_for_status()
        commit_data = commit_resp.json()
        last_commit = commit_data[0] if isinstance(commit_data, list) else commit_data

        # === 2️⃣ Estrai dati principali ===
        stats = {
            "stars": d['stargazers_count'],
            "forks": d['forks_count'],
            "watchers": d['watchers_count'],
            "issues": d['open_issues_count'],
            "language": d['language'],
            "updated_at": d['updated_at'],
            "html_url": d['html_url'],
        }

        commit_msg = last_commit["commit"]["message"].split("\n")[0]
        commit_author = last_commit["commit"]["author"]["name"]
        commit_date = last_commit["commit"]["author"]["date"]
        commit_sha = last_commit["sha"]
        commit_web_url = f"https://github.com/{REPO}/commit/{commit_sha}"

        # === 3️⃣ Calcola variazioni ===
        old_stats = load_repo_stats()
        stars_delta = stats["stars"] - old_stats.get("stars", 0) if old_stats else 0
        forks_delta = stats["forks"] - old_stats.get("forks", 0) if old_stats else 0
        issues_delta = stats["issues"] - old_stats.get("issues", 0) if old_stats else 0

        trend = (stars_delta / (old_stats["stars"] + 1) * 100) if old_stats else 0

        # Salva per confronti futuri
        save_repo_stats(stats)

        # === 4️⃣ Formatta data locale ===
        utc_dt = datetime.fromisoformat(commit_date.replace("Z", "+00:00"))
        local_dt = utc_dt + timedelta(hours=2)  # 🇮🇹
        formatted_date = local_dt.strftime("%d %b %Y — %H:%M")

        # === 5️⃣ Mini barra grafica ===
        bar_len = 10
        filled = min(max(int((trend / 10) * bar_len), 0), bar_len)
        bar = "█" * filled + "▒" * (bar_len - filled)
        trend_icon = "🚀" if trend > 0 else "💤" if trend == 0 else "📉"

        # === 6️⃣ Messaggio Telegram ===
        text = (
            f"📦 <b>Datapizza Repo Watcher</b>\n\n"
            f"🔗 <a href='{stats['html_url']}'>{REPO}</a>\n"
            f"💻 <b>{stats['language']}</b>\n\n"
            f"⭐ <b>Stars:</b> {stats['stars']} (<i>{stars_delta:+}</i>)\n"
            f"🍴 <b>Forks:</b> {stats['forks']} (<i>{forks_delta:+}</i>)\n"
            f"👀 <b>Watchers:</b> {stats['watchers']}\n"
            f"🐞 <b>Issues:</b> {stats['issues']} (<i>{issues_delta:+}</i>)\n\n"
            f"📈 <b>Andamento:</b> {bar} {trend_icon} ({trend:+.1f}%)\n"
            f"🕓 <b>Ultimo commit:</b> <a href='{commit_web_url}'>{formatted_date}</a>\n"
            f"<i>«{commit_msg}» — {commit_author}</i>"
        )

        # === 7️⃣ Pulsanti interattivi ===
        buttons = {
            "inline_keyboard": [
                [
                    {"text": "🔗 Apri Commit", "url": commit_web_url},
                    {"text": "📊 Repo Stats", "url": stats["html_url"]}
                ],
                [
                    {"text": "⭐ Aggiungi Star", "url": stats["html_url"]},
                    {"text": "🍴 Fai un Fork", "url": f"{stats['html_url']}/fork"}
                ]
            ]
        }

        send_telegram_message(text, reply_markup=buttons)
        return f"✅ Statistiche inviate: {stats['stars']}⭐ ({stars_delta:+})"

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

    send_telegram_message("✅ Test Datapizza Watcher — messaggio di prova inviato da locale.")

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


        print("✅ Watcher completato!")

    except Exception as e:
        print(f"\n❌ Errore critico: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)