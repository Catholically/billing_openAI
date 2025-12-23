# OpenAI Invoice Downloader

Automatizza il download mensile delle fatture da OpenAI e le salva su S3.

## 🚀 Quick Start

### Opzione 1: GitHub Actions (Consigliato)

1. **Crea un nuovo repository** su GitHub (privato)

2. **Copia questi file** nel repository:
   ```
   your-repo/
   ├── .github/
   │   └── workflows/
   │       └── download-invoices.yml
   ├── scripts/
   │   └── download_openai_invoice.py
   ├── requirements.txt
   └── README.md
   ```

3. **Configura i Secrets** nel repository:
   
   Vai su: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`
   
   | Secret Name | Valore | Obbligatorio |
   |-------------|--------|--------------|
   | `OPENAI_EMAIL` | La tua email OpenAI | ✅ |
   | `OPENAI_PASSWORD` | La tua password OpenAI | ✅ |
   | `AWS_ACCESS_KEY_ID` | AWS access key | Solo per S3 |
   | `AWS_SECRET_ACCESS_KEY` | AWS secret key | Solo per S3 |
   | `S3_BUCKET` | Nome bucket (es. `catholically-invoices`) | Solo per S3 |

4. **Testa manualmente**:
   - Vai su `Actions` → `Download OpenAI Invoice` → `Run workflow`

5. **Automatico**: Il workflow gira automaticamente il 1° di ogni mese alle 9:00 UTC

---

### Opzione 2: Esecuzione Locale

```bash
# Clona e installa
git clone <your-repo>
cd openai-invoice-downloader
pip install -r requirements.txt
playwright install chromium

# Configura credenziali (scegli uno):

# A) Environment variables
export OPENAI_EMAIL="tua@email.com"
export OPENAI_PASSWORD="tuapassword"

# B) File .env (crea il file)
echo 'OPENAI_EMAIL=tua@email.com' >> .env
echo 'OPENAI_PASSWORD=tuapassword' >> .env

# Esegui
python scripts/download_openai_invoice.py
```

---

### Opzione 3: AWS Secrets Manager

Per maggiore sicurezza, salva le credenziali in AWS Secrets Manager:

```bash
# Crea il secret
aws secretsmanager create-secret \
    --name catholically/openai \
    --region eu-south-1 \
    --secret-string '{"email":"tua@email.com","password":"tuapassword"}'
```

Lo script le recupererà automaticamente se non trova environment variables.

---

## 📁 Struttura Output

```
/tmp/invoices/
├── openai_invoice_202412.pdf    # Fattura scaricata
├── billing_page.png             # Screenshot pagina (debug)
└── error_screenshot.png         # Screenshot errore (se fallisce)
```

## ⚙️ Configurazione Avanzata

### Environment Variables

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `OPENAI_EMAIL` | - | Email account OpenAI |
| `OPENAI_PASSWORD` | - | Password account OpenAI |
| `OUTPUT_DIR` | `/tmp/invoices` | Directory output |
| `HEADLESS` | `true` | Browser headless mode |
| `S3_BUCKET` | - | Bucket S3 per upload |
| `AWS_SECRET_NAME` | `catholically/openai` | Nome secret in AWS |
| `AWS_REGION` | `eu-south-1` | Region AWS |

### Modificare la Schedulazione

Nel file `.github/workflows/download-invoices.yml`:

```yaml
on:
  schedule:
    # Formato: minuto ora giorno-mese mese giorno-settimana
    - cron: '0 9 1 * *'    # 1° del mese alle 9:00 UTC
    # - cron: '0 9 * * 1'  # Ogni lunedì alle 9:00 UTC
    # - cron: '0 9 1,15 * *' # 1° e 15° del mese
```

---

## 🔐 Note sulla Sicurezza

### 2FA / MFA
Se hai abilitato l'autenticazione a due fattori su OpenAI, lo script non funzionerà automaticamente. Opzioni:
1. Disabilita 2FA per questo account (sconsigliato)
2. Usa un account dedicato senza 2FA
3. Usa le API key di OpenAI (se disponibili per billing)

### Credenziali
- **Mai** committare credenziali nel repository
- Usa GitHub Secrets o AWS Secrets Manager
- Il file `.env` è nel `.gitignore`

---

## 🐛 Troubleshooting

### "No invoice download links found"
- Controlla lo screenshot `billing_page.png` negli artifacts
- OpenAI potrebbe aver cambiato la UI
- Verifica di avere fatture disponibili nel tuo account

### "Login failed"
- Verifica email e password
- Controlla `error_screenshot.png`
- Potrebbe esserci un CAPTCHA (raro)

### Timeout
- OpenAI potrebbe essere lento
- Prova a rieseguire il workflow

---

## 📊 Estendere ad Altri Servizi

Puoi duplicare lo script per altri servizi. Esempio struttura:

```
scripts/
├── download_openai_invoice.py
├── download_anthropic_invoice.py
├── download_aws_invoice.py
└── download_shopify_invoice.py
```

E nel workflow:
```yaml
- name: Download All Invoices
  run: |
    python scripts/download_openai_invoice.py
    python scripts/download_anthropic_invoice.py
    # etc...
```

---

## 📝 License

MIT - Usa come vuoi!
