# Smart City AQI Predictor

Pick an Indian city and get its live air quality index, what the next
24 hours look like, and how it compares to other cities.

Live pollutant readings come from OpenWeatherMap. The index is predicted by
an XGBoost model trained on 24,850 CPCB monitoring records.

---

## What you see

```
┌────────────────────────────────────────────────────────────────┐
│  AIR QUALITY INDEX · INDIA · LIVE                              │
│  SMART CITY AQI                                                │
│  Live pollutant readings, scored by an XGBoost model.          │
│════════════════════════════════════════════════════════════════│
│  STATE [ Karnataka ▾ ]  CITY [ Bengaluru ▾ ]     [ ANALYSE ]   │
├──────────────────────────────────┬─────────────────────────────┤
│  CURRENT READING                 │  POLLUTANTS · µG/M³         │
│  BENGALURU, KARNATAKA            │  PM2.5              88.4    │
│                                  │  PM10              149.2    │
│   142  AQI                       │  NO2                31.0    │
│        INDEX                     │  SO2                11.4    │
│                                  │  CO               1180.0    │
│  NEEDS ATTENTION                 │  O3                 38.2    │
│  Moderate — asthma and heart     │  NH3                16.9    │
│  patients should limit outdoor   │                             │
│  effort.                         │  Highest: PM10              │
│           ▼                      │                             │
│  ███░███░██████░██████░██████░██ │                             │
│  0   50  100    200    300  500  │                             │
└──────────────────────────────────┴─────────────────────────────┘
  24-HOUR OUTLOOK │ POLLUTANT PROFILE │ CITY COMPARISON │ LOCATION │ MODEL
```

The scale under the reading is the point of the design: it shows where the
city sits on the full CPCB 0–500 range, not just a number floating on its own.
The chassis is deliberately colourless — the only saturated colour on the page
is the band colour of the reading itself.

---

## Files

| File | What it is | Owner |
|---|---|---|
| `app.py` | The web app | Person 4 + 5 |
| `api_functions.py` | OpenWeatherMap calls | Person 3 |
| `cities.csv` | 40 Indian cities with coordinates | Person 3 |
| `aqi_predictor.py` | Loads the model, predicts, categorises | Person 2 |
| `aqi_model.json` | Trained XGBoost model | Person 2 |
| `model_info.json` | Feature order, units, accuracy scores | Person 2 |
| `requirements.txt` | Dependencies | — |
| `runtime.txt` | Python version for Streamlit Cloud | — |
| `.gitignore` | Keeps the API key out of git | — |
| `DEPLOY.md` | Deployment walkthrough | — |

---

## How it works

```
  Pick a state and city
          │
          ▼
  cities.csv  ──►  latitude, longitude
          │
          ▼
  OpenWeatherMap Air Pollution API
          │  returns 7 pollutants, all in µg/m³
          ▼
  aqi_predictor.predict_from_api()
          │  converts CO µg/m³ → mg/m³
          │  adds month and season
          │  orders features exactly as trained
          ▼
  XGBoost model  ──►  AQI number
          │
          ▼
  CPCB band  ──►  category, colour, health advice
```

---

## Running it locally

```bash
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml`:

```toml
OWM_API_KEY = "your_openweathermap_key"
```

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`.

Get a free key at openweathermap.org. A new key takes about 30 minutes to
activate — until then you get a 401.

For deployment, see `DEPLOY.md`.

---

## The model

XGBoost regressor. 24,850 rows of CPCB data, 2015–2020.

| Model | R² | RMSE | MAE |
|---|---|---|---|
| **XGBoost** | **0.929** | **30.11** | **18.66** |
| Random Forest | 0.925 | 30.91 | 18.67 |
| Linear Regression | 0.781 | 52.97 | 32.67 |

Category accuracy: 78.6% — how often the predicted AQI lands in the correct
CPCB band, which is what the interface actually shows.

**Inputs, in this exact order:**

```
PM2.5, PM10, NO2, SO2, CO, O3, NH3, month, season
```

Feature importance: PM2.5 42%, CO 25%, PM10 19%, everything else 14%.

---

## Two things that silently break predictions

**Feature order.** The model takes an unlabelled array. Send the columns in a
different order and you get a plausible-looking number that is wrong, with no
error raised. Always build the row from `model_info.json["features"]`.

**CO units.** OpenWeatherMap returns every pollutant in µg/m³. The model was
trained on CPCB data where CO is in mg/m³. Divide the API's CO by 1000.

Same air, both ways:

| CO handling | AQI | Category |
|---|---|---|
| Divided by 1000 | 124.3 | Moderate |
| Raw API value | 443.2 | Severe |

CO is the model's second most important feature. `predict_from_api()` handles
this for you — use it rather than calling `predict()` directly.

Run `python aqi_predictor.py` to print both numbers. If they match, the
conversion isn't being applied.

---

## AQI bands

| AQI | Category | Verdict | Advice |
|---|---|---|---|
| 0–50 | Good | Smart & Clean City | Safe for everyone |
| 51–100 | Satisfactory | Liveable City | Minor discomfort for the very sensitive |
| 101–200 | Moderate | Needs Attention | Asthma and heart patients should limit outdoor effort |
| 201–300 | Poor | Polluted City | Discomfort likely on prolonged exposure |
| 301–400 | Very Poor | Severely Polluted | Wear a mask outdoors, avoid exercise |
| 401–500 | Severe | Dangerously Polluted | Stay indoors |

---

## API quota

The free OpenWeatherMap tier allows roughly 1,000 calls a day. The app caches
every response for 10 minutes, so repeated clicks on the same city cost
nothing. City comparison is capped at six cities because each one is a
separate call.

---

## Limitations

- Trained on Indian CPCB data, so accuracy is best where monitoring stations
  are dense. Small towns fall back on the nearest city's coordinates.
- AQI above 500 was capped during training, since the index is defined on a
  0–500 scale.
- The 24-hour outlook applies the model to the API's own pollutant forecast,
  so it inherits that forecast's uncertainty.
- Estimates only. Not a substitute for official CPCB bulletins.

---

## Team

| Person | Role |
|---|---|
| 1 | Data collection and cleaning |
| 2 | Model training and export |
| 3 | API integration and city data |
| 4 | Web application |
| 5 | Visualisation, deployment, report |

---

## Credits

Pollution data: [OpenWeatherMap Air Pollution API](https://openweathermap.org/api/air-pollution).
Training data: CPCB records via the Kaggle *Air Quality Data in India* dataset.
Built with [Streamlit](https://streamlit.io), [XGBoost](https://xgboost.ai)
and [Plotly](https://plotly.com).
