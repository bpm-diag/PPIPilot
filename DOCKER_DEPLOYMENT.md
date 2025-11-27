# PPIPilot - Docker Deployment Guide

## Prerequisiti

- Docker Desktop installato (Windows/Mac) o Docker Engine (Linux)
- Docker Compose installato
- OpenAI API Key

## Setup Rapido

### 1. Configurazione API Key

Crea un file `.env` nella root del progetto:

```bash
cp .env.example .env
```

Modifica il file `.env` e inserisci la tua OpenAI API key:

```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 2. Build e Avvio

```bash
# Build dell'immagine Docker
docker-compose build

# Avvio del container
docker-compose up -d
```

### 3. Accesso all'Applicazione

Apri il browser e vai a: **http://localhost:8501**

## Comandi Utili

### Gestione Container

```bash
# Avvia i container
docker-compose up -d

# Ferma i container
docker-compose down

# Visualizza i logs
docker-compose logs -f

# Visualizza solo gli ultimi 100 log
docker-compose logs --tail=100 -f

# Riavvia il container
docker-compose restart

# Rebuild dopo modifiche al codice
docker-compose up -d --build
```

### Gestione Dati

```bash
# Accedi al container per debug
docker-compose exec ppipilot bash

# Copia file dal container
docker cp ppipilot-app:/app/testfolder ./backup_testfolder

# Pulisci i volumi (ATTENZIONE: cancella tutti i dati persistenti)
docker-compose down -v
```

### Monitoring

```bash
# Verifica stato del container
docker-compose ps

# Verifica risorse utilizzate
docker stats ppipilot-app

# Health check
docker inspect --format='{{.State.Health.Status}}' ppipilot-app
```

## Struttura Volumi

I seguenti dati sono persistiti anche dopo il riavvio del container:

- `./testfolder` → File JSON generati e corretti
- `./data` → File XES caricati
- `./1_prompt_description_goal` → Template prompt
- `./1_prompt_general` → Template prompt
- `./2_prompt` → Template prompt
- `./3_prompt_json_correction` → Template prompt per correzione errori

## Configurazione Avanzata

### Modifica Porta

Per cambiare la porta di accesso, modifica `docker-compose.yml`:

```yaml
ports:
  - "8080:8501"  # Accesso su http://localhost:8080
```

### Variabili d'Ambiente Aggiuntive

Aggiungi al file `.env` o alla sezione `environment` in `docker-compose.yml`:

```yaml
environment:
  - OPENAI_API_KEY=${OPENAI_API_KEY}
  - STREAMLIT_SERVER_MAX_UPLOAD_SIZE=200
  - STREAMLIT_SERVER_ENABLE_CORS=false
```

### Limiti Risorse

Aggiungi limiti di CPU e memoria in `docker-compose.yml`:

```yaml
services:
  ppipilot:
    # ... altre configurazioni ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## Troubleshooting

### Container non si avvia

```bash
# Verifica i logs
docker-compose logs

# Verifica che la porta 8501 non sia già in uso
netstat -ano | findstr :8501  # Windows
lsof -i :8501                 # Linux/Mac
```

### Errore API Key

Verifica che:
1. Il file `.env` esista nella root del progetto
2. La variabile `OPENAI_API_KEY` sia impostata correttamente
3. Non ci siano spazi extra nella chiave

### Problemi di Permessi (Linux)

```bash
# Dai i permessi corretti alle cartelle
sudo chown -R $USER:$USER ./testfolder ./data
```

### Reset Completo

```bash
# Ferma e rimuovi tutto
docker-compose down -v

# Rimuovi l'immagine
docker rmi ppipilot-ppipilot

# Rebuild da zero
docker-compose build --no-cache
docker-compose up -d
```

## Deployment in Produzione

### Reverse Proxy con Nginx

Esempio configurazione Nginx:

```nginx
server {
    listen 80;
    server_name ppipilot.yourdomain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### HTTPS con Let's Encrypt

```bash
# Installa certbot
sudo apt-get install certbot python3-certbot-nginx

# Ottieni certificato SSL
sudo certbot --nginx -d ppipilot.yourdomain.com
```

### Backup Automatico

Script di backup (salva come `backup.sh`):

```bash
#!/bin/bash
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR
docker cp ppipilot-app:/app/testfolder $BACKUP_DIR/
docker cp ppipilot-app:/app/data $BACKUP_DIR/
echo "Backup completato in $BACKUP_DIR"
```

## Note di Sicurezza

1. **Non committare mai il file `.env` su Git** - è già incluso in `.gitignore`
2. **Usa secrets per deployment in produzione** invece di variabili d'ambiente
3. **Abilita HTTPS** per deployment pubblici
4. **Limita l'accesso** tramite firewall o autenticazione

## Supporto

Per problemi o domande:
- Verifica i logs: `docker-compose logs -f`
- Controlla la documentazione Streamlit: https://docs.streamlit.io
- Verifica la connettività OpenAI API
