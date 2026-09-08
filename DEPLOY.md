# Deploy to Streamlit Cloud — step by step

## Before you start

You need: a GitHub account, and your OpenWeatherMap API key.

Do **not** put the key in any file you push. It goes in Streamlit's
Secrets panel instead.

---

## Step 1 — Test locally first

```bash
cd smart-city-aqi
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` (copy from `secrets.toml.example`):

```toml
OWM_API_KEY = "your_real_key_here"
```

Run it:

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`. Test 5 different cities before deploying.
Fixing things locally is fast; fixing them on Cloud is slow.

---

## Step 2 — Make the GitHub repo

On github.com: **New repository** → name it `smart-city-aqi` → **Public**
→ Create.

Streamlit Cloud's free tier requires a public repo.

Then in your project folder:

```bash
git init
git add .
git commit -m "Smart City AQI Predictor"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/smart-city-aqi.git
git push -u origin main
```

### Check before you push

```bash
git status
```

`secrets.toml` must **not** appear. If it does, stop — `.gitignore` isn't
working. Fix it before pushing. A key pushed to a public repo is
compromised the moment it lands, even if you delete it after.

---

## Step 3 — Deploy

1. Go to **share.streamlit.io**
2. Sign in with GitHub
3. **New app** → pick your repo → branch `main` → main file `app.py`
4. Click **Advanced settings** → **Secrets**
5. Paste:

```toml
OWM_API_KEY = "your_real_key_here"
```

6. **Deploy**

First build takes 3–5 minutes (xgboost is a large wheel).

You get a link like `https://yourname-smart-city-aqi.streamlit.app`.

---

## Step 4 — Test the live app

Open the link. Try 5 cities across different states. Check that:

- Both dropdowns populate
- Analyse returns an AQI within a few seconds
- The forecast tab draws a line
- The map shows the right location

---

## If deployment fails

| Error in the build log | Fix |
|---|---|
| `ModuleNotFoundError: xgboost` | Missing from `requirements.txt` |
| `No secrets found` | Add the key in Settings → Secrets, then Reboot |
| `FileNotFoundError: cities.csv` | File wasn't committed. `git add cities.csv` |
| `FileNotFoundError: aqi_model.json` | Same — check it was pushed (it's 2.4 MB) |
| Build times out | Remove unused packages from `requirements.txt` |
| Python version error | `runtime.txt` says 3.12. Don't change it to 3.14. |

After changing Secrets, always **Reboot app** from the menu — it does not
pick them up automatically.

---

## Updating the app later

```bash
git add .
git commit -m "what changed"
git push
```

Streamlit Cloud redeploys automatically within a minute.

---

## Report checklist

- [ ] Live app link
- [ ] GitHub repo link
- [ ] Screenshot of a clean city (low AQI)
- [ ] Screenshot of a polluted city (high AQI)
- [ ] Screenshot of the forecast chart
- [ ] Model comparison table (R², RMSE, MAE for all 3 models)
- [ ] Feature importance chart
- [ ] Person 1's EDA charts
