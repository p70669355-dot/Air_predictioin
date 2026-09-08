"""
AQI predictor — loads the model and turns pollutant values into an AQI
number plus a Smart City category.
"""

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import xgboost as xgb


HERE = Path(__file__).resolve().parent
MODEL_PATH = HERE / "aqi_model.json"
INFO_PATH = HERE / "model_info.json"


# --------------------------------------------------------------------------
# Load once at import
# --------------------------------------------------------------------------

with open(INFO_PATH, "r", encoding="utf-8") as f:
    INFO = json.load(f)

FEATURES = INFO["features"]                    # exact order the model expects
UNIT_CONVERSION = INFO["api_unit_conversion"]  # OpenWeatherMap -> CPCB units

_booster = xgb.Booster()
_booster.load_model(str(MODEL_PATH))


# --------------------------------------------------------------------------
# Categories
# --------------------------------------------------------------------------

CATEGORIES = [
    (50,   "Good",         "#2E7D32", "Smart & Clean City",
     "Air quality is safe for everyone."),
    (100,  "Satisfactory", "#7CB342", "Liveable City",
     "Minor discomfort possible for very sensitive people."),
    (200,  "Moderate",     "#F9A825", "Needs Attention",
     "People with asthma or heart conditions should limit outdoor effort."),
    (300,  "Poor",         "#EF6C00", "Polluted City",
     "Discomfort likely for most people on prolonged exposure."),
    (400,  "Very Poor",    "#C62828", "Severely Polluted",
     "Wear a mask outdoors. Avoid outdoor exercise."),
    (500,  "Severe",       "#7B1FA2", "Dangerously Polluted",
     "Stay indoors. Health emergency conditions."),
]


def categorise(aqi: float) -> dict:
    """Turn an AQI number into a category, colour, verdict and advice."""
    for upper, label, colour, verdict, advice in CATEGORIES:
        if aqi <= upper:
            return {
                "category": label,
                "colour": colour,
                "verdict": verdict,
                "advice": advice,
            }

    last = CATEGORIES[-1]
    return {
        "category": last[1],
        "colour": last[2],
        "verdict": last[3],
        "advice": last[4],
    }


# --------------------------------------------------------------------------
# Seasons
# --------------------------------------------------------------------------

def season_from_month(month: int) -> int:
    """Indian seasons, encoded the same way the model was trained."""
    if month in (12, 1, 2):
        return 0   # Winter
    if month in (3, 4, 5):
        return 1   # Summer
    if month in (6, 7, 8, 9):
        return 2   # Monsoon
    return 3       # Post-Monsoon (10, 11)


# --------------------------------------------------------------------------
# Prediction
# --------------------------------------------------------------------------

def predict(pollutants: dict, month: int = None, season: int = None) -> dict:
    """
    Predict AQI from pollutant values already in CPCB units.

    pollutants: dict with keys PM2.5, PM10, NO2, SO2, CO, O3, NH3
                CO must be in mg/m3. Everything else in ug/m3.
    """
    if month is None:
        month = datetime.now().month

    if season is None:
        season = season_from_month(month)

    values = dict(pollutants)
    values["month"] = month
    values["season"] = season

    missing = [f for f in FEATURES if f not in values]
    if missing:
        raise ValueError(f"Missing required values: {missing}")

    row = np.array([[float(values[f]) for f in FEATURES]], dtype=np.float32)

    matrix = xgb.DMatrix(row, feature_names=FEATURES)
    aqi = float(_booster.predict(matrix)[0])

    # AQI is defined on a 0-500 scale
    aqi = min(max(aqi, 0.0), 500.0)

    result = {"aqi": round(aqi, 1)}
    result.update(categorise(aqi))
    return result


def predict_from_api(api_pollutants: dict, month: int = None,
                     season: int = None) -> dict:
    """
    Predict AQI directly from OpenWeatherMap values.

    OpenWeatherMap returns every pollutant in ug/m3. The model was trained on
    CPCB data where CO is in mg/m3. This converts CO for you.

    Pass the dict from Person 3's get_pollution()["pollutants"] straight in.
    """
    converted = {
        name: float(value) * UNIT_CONVERSION.get(name, 1.0)
        for name, value in api_pollutants.items()
    }
    return predict(converted, month=month, season=season)


# --------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------

if __name__ == "__main__":

    print("Model loaded from:", MODEL_PATH.name)
    print("Feature order    :", FEATURES)
    print()

    # Realistic OpenWeatherMap response: everything in ug/m3
    api_sample = {
        "PM2.5": 60.0, "PM10": 110.0, "NO2": 30.0, "SO2": 12.0,
        "CO": 900.0,   # ug/m3 -- this is the one that needs converting
        "O3": 35.0, "NH3": 20.0,
    }

    right = predict_from_api(api_sample, month=6)
    print("Correct (CO converted):", right)

    wrong = predict(api_sample, month=6)   # deliberately skips conversion
    print("Wrong   (CO raw)      :", wrong)
    print()
    print("If those two match, the unit conversion is not being applied.")
