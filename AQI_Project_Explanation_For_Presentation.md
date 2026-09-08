# Smart City AQI Predictor — Full Explanation (Simple Words)

Use this to explain the project to your teacher today. ML parts are covered in the most detail since that's the core of the project.

---

## 1. What does this project do? (one line)

- You pick a city → the app fetches live pollution data → a trained ML model predicts the Air Quality Index (AQI) → the app shows you a health verdict (Good, Moderate, Poor, etc.)

---

## 2. Why is this a Machine Learning project?

- We are **not** just showing raw pollution numbers
- We are **predicting** a value (AQI) using a model that learned patterns from past data
- The model was never told "if PM2.5 is X, AQI is Y" — it figured out that relationship itself by looking at thousands of past examples
- This is called **regression** — predicting a number (AQI), not a category

---

## 3. Where did the training data come from?

- **Source:** CPCB (Central Pollution Control Board) — the official Indian government body that measures air quality
- **Dataset:** "Air Quality Data in India" — real historical readings, 2015 to 2020
- **Size:** 24,850 rows — each row is one reading, at one place, at one time
- **Columns in raw data:** date, city, and pollutant levels — PM2.5, PM10, NO2, SO2, CO, O3, NH3 — plus the official AQI for that reading

---

## 4. Cleaning the data (before training)

Real data is always messy. We had to fix it before the model could learn from it:

- **Missing values** → filled in using the median (middle value) of that column, so one missing reading doesn't break everything
- **Negative pollution values** → deleted. Pollution can't be negative — these were sensor errors
- **AQI values above 500** → capped at 500. Official AQI is defined only from 0 to 500, so anything above that is also a sensor error, not a real reading
- **Duplicate rows** → removed

**Why this matters for your teacher:** a model trained on dirty data learns dirty patterns. Cleaning first is a standard, required ML step, not optional polish.

---

## 5. Choosing what the model should learn from (features)

**Features** = the inputs the model uses to make its guess.

We used exactly these **9 features**:
```
PM2.5, PM10, NO2, SO2, CO, O3, NH3, month, season
```

**Why these 7 pollutants specifically?**
- These are the exact 7 pollutants that our live weather API (OpenWeatherMap) can give us in real time
- **Golden rule we followed:** never train on a column the live API can't supply later. If we trained on "humidity" but the API doesn't give humidity, the live app would break the moment we tried to use it

**Why add month and season?**
- Pollution changes with seasons — Indian winters are much more polluted than monsoon season (due to stubble burning, temperature inversion, less rain washing out particles)
- Giving the model this information helps it make more accurate predictions

**Target (what the model is trying to predict):**
```
AQI  (a single number, 0 to 500)
```

---

## 6. Splitting the data — train vs test

- **80% of the data** → used to teach the model (training set)
- **20% of the data** → hidden from the model, used only afterward to check how well it actually learned (test set)

**Why do this?**
- If we tested the model on data it already memorized, it would look artificially perfect
- Testing on unseen data tells us how it will perform on a real city it hasn't seen readings from before — which is exactly what happens in the live app

---

## 7. The three models we trained and compared

We didn't just pick one model and hope — we trained three different types and compared them fairly.

### Model 1: Linear Regression
- **Simple explanation:** draws the "best straight-line relationship" between the pollutants and AQI
- Fastest and simplest, but real pollution-to-AQI relationships aren't simple straight lines — so it performed the weakest

### Model 2: Random Forest
- **Simple explanation:** builds hundreds of small decision trees (like a big flowchart of yes/no questions — "is PM2.5 above 100? is CO above 2? ..."), then averages all their answers together
- Much better than Linear Regression because it can capture curved, complicated relationships

### Model 3: XGBoost (the one we chose)
- **Simple explanation:** also builds decision trees, but each new tree is specifically built to fix the mistakes of the previous trees — it learns from its own errors, round after round
- This "learning from mistakes" approach is why it usually performs best on this kind of structured, tabular data
- **XGBoost = eXtreme Gradient Boosting**

---

## 8. How we measured which model was best

We used three standard ML evaluation numbers. Here's what each one actually means, in plain words:

| Metric | What it means in simple words |
|---|---|
| **R² (R-squared)** | How much of the AQI's ups and downs the model successfully explains. 1.0 = perfect, 0 = no better than guessing the average every time |
| **RMSE** | On average, how far off the model's guess is from the real AQI, in AQI points — bigger mistakes are punished more heavily |
| **MAE** | On average, how far off the model's guess is from the real AQI — treats every mistake equally, easier to read directly |

### Our actual results:

| Model | R² | RMSE | MAE |
|---|---|---|---|
| **XGBoost (chosen)** | **0.929** | **30.11** | **18.66** |
| Random Forest | 0.925 | 30.91 | 18.67 |
| Linear Regression | 0.781 | 52.97 | 32.67 |

**In simple words:** XGBoost explains 92.9% of the pattern in AQI, and on average its guess is off by about 18-19 AQI points. That's the best of the three, so we chose it.

### One more number: Category Accuracy — 78.6%

- The app doesn't just show a raw number, it shows a **category** — Good, Moderate, Poor, etc.
- This measures: out of 100 predictions, how many land in the **correct category**, not just close in raw number
- 78.6% means it gets the right health category about 4 out of 5 times

---

## 9. Which pollutant matters most to the model? (Feature Importance)

XGBoost can tell us which inputs it relies on most:

| Feature | How much it matters |
|---|---|
| **PM2.5** | 42% |
| **CO** | 25% |
| **PM10** | 19% |
| Season | 4% |
| NO2, month, SO2, NH3, O3 (combined) | 10% |

**In simple words:** fine particulate matter (PM2.5) — the tiny dust/smoke particles small enough to enter your lungs — drives most of the AQI score. This actually matches real-world science: PM2.5 is widely considered the most dangerous and most heavily weighted pollutant in most AQI formulas worldwide, so it makes sense the model picked up on this itself.

---

## 10. How the live app actually works (step by step)

1. You pick a State, then a City, from a dropdown
2. The app looks up that city's latitude/longitude
3. It calls the **OpenWeatherMap Air Pollution API** — a live, real-time data source
4. The API returns the current PM2.5, PM10, NO2, SO2, CO, O3, NH3 levels for that exact location, right now
5. Those 7 numbers, plus the current month and season, are fed into our trained XGBoost model
6. The model outputs a predicted AQI number
7. That number is converted into a category (Good/Moderate/Poor/etc.) with a colour and health advice
8. Everything is displayed on the screen — including a 24-hour forecast, pollutant breakdown chart, and a city comparison tool

---

## 11. The one tricky bug we found and fixed (good to mention — shows real engineering)

- Our training data (CPCB) measures **CO in mg/m³**
- But the live API (OpenWeatherMap) sends **CO in µg/m³** — a completely different unit, 1000x different
- If we hadn't caught this, the app would have silently fed the wrong CO value into the model every single time — no error message, just a wrong answer
- **Fix:** we divide the API's CO value by 1000 before handing it to the model, so both sides speak the same unit

**We tested it directly — same air, two different results:**

| CO handling | Predicted AQI | Category |
|---|---|---|
| Correctly converted | 124.3 | Moderate |
| Left un-converted (wrong) | 443.2 | Severe |

**Why this is worth mentioning to your teacher:** finding and fixing a silent bug like this — one that doesn't crash the program but quietly gives wrong answers — is a real, valuable engineering skill, not just a coding task.

---

## 12. Full tech stack, and why each part was chosen

| Tool | What it's for | Why we chose it |
|---|---|---|
| **Python** | Programming language | Standard for ML work, huge library support |
| **Pandas / NumPy** | Handling and cleaning tabular data | Industry-standard tools for this exact job |
| **Scikit-learn** | Linear Regression, Random Forest, train/test split, metrics | Well-tested, standard ML library |
| **XGBoost** | Our chosen final model | Best accuracy for structured/tabular data like this |
| **Google Colab** | Where we trained the model | Free, gives access to computing power, no installation needed |
| **OpenWeatherMap API** | Live pollution data | Free tier, reliable, gives exactly the 7 pollutants we need |
| **Streamlit** | Building the web app | Turns Python code into a working website very quickly, ideal for a project like this |
| **Plotly** | Charts (pollutant bars, forecast lines) | Makes interactive, good-looking charts easily |
| **Streamlit Cloud** | Hosting the live app | Free, connects directly to GitHub, one-click deploy |
| **GitHub** | Storing and version-controlling the code | Standard practice, also required for Streamlit Cloud deployment |

---

## 13. Questions your teacher might ask — with short answers ready

**Q: Why did you choose XGBoost over the other two models?**
A: We tested all three fairly on the same held-out data. XGBoost had the highest R² (0.929) and lowest error (RMSE 30.11), so it made the most accurate predictions.

**Q: What is XGBoost, simply?**
A: A method that builds many small decision trees one after another, where each new tree is trained specifically to fix the mistakes of the trees before it.

**Q: How much data did you train on?**
A: 24,850 real readings from CPCB, covering Indian cities from 2015 to 2020, split 80% for training and 20% for testing.

**Q: Why not just use the AQI formula directly instead of ML?**
A: The formal method exists, but this project's goal is to demonstrate a full ML pipeline — data cleaning, feature engineering, model comparison, evaluation, and deployment — connected to live data through a real application.

**Q: What was the hardest part?**
A: Finding a unit mismatch between our training data (CO in mg/m³) and the live API (CO in µg/m³) that would have silently broken every prediction if we hadn't caught it.

**Q: How accurate is it really?**
A: R² of 0.929 (explains 92.9% of AQI variation), and it picks the exact correct health category about 78.6% of the time.

**Q: What would you improve with more time?**
A: A larger, more recent dataset, adding weather features like humidity and wind speed if a suitable free API provided them, and testing more advanced models like neural networks for comparison.

---

## 14. One paragraph you can say out loud to start your presentation

> "Our project predicts live air quality for Indian cities using a machine learning model. We trained three different regression models — Linear Regression, Random Forest, and XGBoost — on 24,850 real CPCB pollution readings, and selected XGBoost because it gave the best accuracy, with an R² of 0.929. The model takes 7 live pollutant readings from a real-time weather API, along with the month and season, and predicts the current AQI, which we then convert into a health category with colour-coded advice. Along the way, we identified and fixed a real bug — a unit mismatch between our training data and the live API — which shows the kind of practical debugging real ML deployment requires, not just model training in isolation."

---

## 15. If your teacher asks for the model comparison as a quick visual

```
R² Score (higher = better)
XGBoost            ████████████████████░  0.929
Random Forest       ███████████████████░  0.925
Linear Regression   ███████████████░░░░░  0.781

MAE — Average Error in AQI points (lower = better)
XGBoost            ██████░░░░░░░░░░░░░░  18.66
Random Forest       ██████░░░░░░░░░░░░░░  18.67
Linear Regression   ███████████░░░░░░░░░  32.67
```
