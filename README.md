Datapizza Repo Watcher 🤖
Un bot Python intelligente che monitora un repository GitHub, analizza i nuovi commit e invia notifiche personalizzate e riepiloghi settimanali a un canale Telegram con uno stile... particolare. hacker! 💻

✨ Caratteristiche Principali
Monitoraggio Commit: Controlla il branch main di un repository GitHub per nuovi commit.

Notifiche Intelligenti: Invia notifiche immediate su Telegram solo per i commit "importanti" (es. feat, fix, security).

Digest Settimanale: Accumula i commit meno critici (es. docs, chore, refactor) e li invia in un riepilogo settimanale.

Stile Unico: Le notifiche sono formattate con un tema "hacker" per un tocco di originalità, complete di pulsanti interattivi.

Statistiche del Repo: Traccia e notifica le statistiche principali del repository (stelle, fork, issue).

Modalità Agente (LLM): Può essere eseguito da un agente basato su LLM (tramite Ollama) per un'orchestrazione più flessibile dei task.

Persistenza: Salva lo stato (ultimo commit, storico) su file JSON locali per non perdere informazioni tra un'esecuzione e l'altra.

Configurazione Flessibile: Gestisce tutte le impostazioni tramite variabili d'ambiente.

🔧 Installazione e Configurazione
Per far funzionare lo script, segui questi passaggi.

1. Prerequisiti
Python 3.8+

Un bot Telegram e il suo Token.

L'ID della chat Telegram dove inviare i messaggi.

2. Installazione delle Dipendenze
Crea un file requirements.txt con le librerie necessarie:

Plaintext

# requirements.txt
requests
python-dotenv
datapizza-ai-clients-openai-like
E installale con pip:

Bash

pip install -r requirements.txt
3. Configurazione dell'Ambiente
Crea un file chiamato telegram.env nella stessa directory dello script e inserisci le tue credenziali. Puoi usare il seguente template:

Snippet di codice

# telegram.env
# Obbligatori per le notifiche
TELEGRAM_TOKEN="IL_TUO_TOKEN_TELEGRAM"
TELEGRAM_CHAT_ID="IL_TUO_CHAT_ID"

# Opzionali
USE_LLM="false"  # Imposta a "true" per usare la modalità Agente con Ollama
RUN_MODE="auto"  # Modalità di esecuzione: auto, direct, agent
🚀 Utilizzo
Una volta configurato, puoi eseguire lo script direttamente dal tuo terminale:

Bash

python3 nome_script.py
Lo script eseguirà i seguenti task in sequenza:

Controllo dei nuovi commit: Se trova un commit importante, invia una notifica. Altrimenti, lo salva per il digest.

Invio del digest settimanale: Se è il giorno giusto della settimana (configurato su Giovedì), invia il riepilogo.

Recupero delle statistiche: Invia un messaggio con le statistiche aggiornate del repository.

Automazione
Questo script è pensato per essere eseguito periodicamente. Puoi automatizzarlo usando:

Cron Job su un server Linux.

GitHub Actions con un trigger schedulato (es. ogni 15 minuti).

Esempio di cron job per eseguirlo ogni 15 minuti:

Snippet di codice

*/15 * * * * /usr/bin/python3 /percorso/del/tuo/script.py >> /percorso/log.txt 2>&1
⚙️ Dettagli di Configurazione
Puoi personalizzare il comportamento dello script modificando le costanti globali o le variabili d'ambiente.

Variabili d'Ambiente (telegram.env)
TELEGRAM_TOKEN: Il token del tuo bot Telegram.

TELEGRAM_CHAT_ID: L'ID della chat, gruppo o canale dove il bot invierà i messaggi.

USE_LLM: Se impostato a true, lo script tenterà di connettersi a un'istanza locale di Ollama per usare la modalità Agente.

RUN_MODE:

auto (default): Esegue in modalità direct se in un ambiente CI/CD, altrimenti prova la modalità agent se l'LLM è disponibile.

direct: Esegue sempre i tool in sequenza, senza l'intervento di un LLM.

agent: Tenta sempre di usare l'agente LLM.

Costanti nello Script
REPO: Il repository GitHub da monitorare (default: datapizza-labs/datapizza-ai).

IMPORTANT_TYPES: L'insieme dei tipi di commit che triggerano una notifica immediata.

QUIET_TYPES: L'insieme dei tipi di commit che vengono accumulati per il digest.

DIGEST_DAY: Il giorno della settimana per l'invio del digest (0=Lunedì, 3=Giovedì).

🧠 Modalità Agente (LLM)
Se USE_LLM è true, lo script attiva una modalità avanzata in cui un Agente AI decide quali strumenti eseguire.

Requisiti:

Un'istanza di Ollama in esecuzione su http://localhost:11434.

Il modello llama3.2 scaricato (ollama pull llama3.2).

In questa modalità, l'agente riceve un prompt generico (es. "Controlla gli aggiornamenti del repo e invia il digest se necessario") e orchestra autonomamente le chiamate alle funzioni check_repo_updates, send_weekly_digest, ecc.

📦 File Generati
Lo script crea e gestisce i seguenti file JSON per mantenere lo stato:

last_commit.json: Salva l'hash (SHA) dell'ultimo commit notificato per evitare duplicati.

commit_history.json: Mantiene uno storico degli ultimi 100 commit analizzati e le statistiche per autore.

repo_stats.json: Salva le ultime statistiche del repository per calcolare le variazioni (es. nuove stelle).

🛠️ Patch per datapizza
La sezione iniziale dello script include una patch dinamica per il namespace datapizza. Questo garantisce che il modulo datapizza.clients.openai_like sia importabile correttamente anche in ambienti (come alcune configurazioni di GitHub Actions) dove i pacchetti con namespace possono creare problemi. Se l'import diretto fallisce, crea la struttura del namespace in memoria.
