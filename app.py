"""
Smart City AQI Predictor — Streamlit application.

Design: a monitoring-station bulletin. The chassis is achromatic; the only
saturated colour on the page is the CPCB band colour of the reading itself.

Run:   streamlit run app.py
Needs: .streamlit/secrets.toml containing OWM_API_KEY
"""

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api_functions import get_pollution, get_pollution_forecast
from aqi_predictor import predict_from_api, categorise


st.set_page_config(
    page_title="Smart City AQI",
    page_icon="◐",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ==========================================================================
# Design tokens
# ==========================================================================

CHASSIS = "#E8EAE6"
SURFACE = "#FFFFFF"
INK = "#191C1A"
INK_SOFT = "#5C635E"
RULE = "#CDD2CB"

# CPCB mandated bands. These are the only saturated colours in the interface.
BANDS = [
    (0, 50, "Good", "#2E7D32"),
    (50, 100, "Satisfactory", "#7CB342"),
    (100, 200, "Moderate", "#F9A825"),
    (200, 300, "Poor", "#EF6C00"),
    (300, 400, "Very Poor", "#C62828"),
    (400, 500, "Severe", "#7B1FA2"),
]


st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Public+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

.stApp {{ background: {CHASSIS}; }}

html, body, [class*="css"], .stMarkdown, p, li {{
  font-family: 'Public Sans', system-ui, sans-serif;
  color: {INK};
}}

/* masthead */
.aq-head {{ border-bottom: 2px solid {INK}; padding-bottom: 14px; margin-bottom: 22px; }}
.aq-eyebrow {{
  font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .18em;
  text-transform: uppercase; color: {INK_SOFT}; margin: 0 0 6px;
}}
.aq-title {{
  font-family: 'Barlow Condensed', sans-serif; font-size: 54px; font-weight: 700;
  letter-spacing: -0.01em; line-height: .95; text-transform: uppercase;
  color: {INK}; margin: 0;
}}
.aq-sub {{ font-size: 14px; color: {INK_SOFT}; margin: 8px 0 0; max-width: 62ch; }}

/* panels */
.aq-card {{
  background: {SURFACE}; border: 1px solid {RULE}; border-radius: 3px;
  padding: 20px 22px; margin-bottom: 14px;
}}
.aq-legend {{
  font-family: 'JetBrains Mono', monospace; font-size: 10px; letter-spacing: .16em;
  text-transform: uppercase; color: {INK_SOFT};
  margin: 0 0 14px; padding-bottom: 9px; border-bottom: 1px solid {RULE};
}}

/* the reading */
.aq-reading {{ display: flex; align-items: baseline; gap: 16px; }}
.aq-value {{
  font-family: 'Barlow Condensed', sans-serif; font-size: 92px; font-weight: 700;
  line-height: .82; letter-spacing: -0.02em;
}}
.aq-unit {{
  font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .16em;
  text-transform: uppercase; color: {INK_SOFT};
}}
.aq-verdict {{
  font-family: 'Barlow Condensed', sans-serif; font-size: 30px; font-weight: 600;
  text-transform: uppercase; letter-spacing: .01em; line-height: 1.05; margin: 12px 0 4px;
}}
.aq-advice {{ font-size: 14px; color: {INK_SOFT}; max-width: 46ch; }}
.aq-place {{
  font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .14em;
  text-transform: uppercase; color: {INK_SOFT}; margin-bottom: 4px;
}}

/* scale */
.aq-scale-labels {{
  display: flex; font-family: 'JetBrains Mono', monospace; font-size: 9px;
  letter-spacing: .08em; color: {INK_SOFT}; margin-top: 5px;
}}

/* data rows */
.aq-row {{
  display: flex; justify-content: space-between; align-items: baseline;
  font-family: 'JetBrains Mono', monospace; font-size: 12px;
  padding: 7px 0; border-bottom: 1px solid {RULE};
}}
.aq-row:last-child {{ border-bottom: none; }}
.aq-row .k {{ color: {INK_SOFT}; letter-spacing: .08em; text-transform: uppercase; }}
.aq-row .v {{ color: {INK}; font-weight: 500; }}

/* streamlit chrome */
.stButton button {{
  background: {INK} !important; color: {SURFACE} !important; border: none !important;
  border-radius: 3px !important; font-family: 'Barlow Condensed', sans-serif !important;
  font-size: 17px !important; font-weight: 600 !important; text-transform: uppercase !important;
  letter-spacing: .06em !important; padding: 11px 26px !important;
}}
.stButton button:hover {{ background: #000 !important; }}
div[data-testid="stMetricValue"] {{ font-family: 'Barlow Condensed', sans-serif; }}
label, .stSelectbox label, .stMultiSelect label {{
  font-family: 'JetBrains Mono', monospace !important; font-size: 10px !important;
  letter-spacing: .14em !important; text-transform: uppercase !important;
  color: {INK_SOFT} !important;
}}
.stTabs [data-baseweb="tab"] {{
  font-family: 'JetBrains Mono', monospace; font-size: 11px;
  letter-spacing: .1em; text-transform: uppercase;
}}
#MainMenu, footer {{ visibility: hidden; }}
</style>
""",
    unsafe_allow_html=True,
)


PLOT_LAYOUT = dict(
    paper_bgcolor=SURFACE,
    plot_bgcolor=SURFACE,
    font=dict(family="Public Sans, sans-serif", color=INK, size=12),
    margin=dict(l=10, r=10, t=44, b=10),
    xaxis=dict(gridcolor=RULE, zerolinecolor=RULE),
    yaxis=dict(gridcolor=RULE, zerolinecolor=RULE),
)


# ==========================================================================
# Data loading
# ==========================================================================

@st.cache_data
def load_cities() -> pd.DataFrame:
    return pd.read_csv("cities.csv")


def get_api_key():
    """Read the key without letting a missing config look like an API fault."""
    try:
        return st.secrets["OWM_API_KEY"]
    except Exception:
        return None


@st.cache_data(ttl=600, show_spinner=False)
def fetch_current(lat: float, lon: float, api_key: str) -> dict:
    return get_pollution(lat, lon, api_key)


@st.cache_data(ttl=600, show_spinner=False)
def fetch_forecast(lat: float, lon: float, api_key: str, hours: int = 24) -> list:
    return get_pollution_forecast(lat, lon, api_key, hours=hours)


# ==========================================================================
# The signature element: the CPCB band scale
# ==========================================================================

def band_scale(aqi: float) -> str:
    """
    The full 0-500 CPCB scale drawn as six proportional segments, with a
    marker at the current reading. Shows where a city sits on the mandated
    scale, not just its number in isolation.
    """
    position = min(max(aqi, 0), 500) / 500 * 100

    segments = "".join(
        f'<div style="flex:{(hi - lo)};background:{colour};height:100%;"></div>'
        for lo, hi, _, colour in BANDS
    )

    return f"""
<div style="position:relative;margin-top:6px;">
  <div style="display:flex;height:26px;border-radius:2px;overflow:hidden;">{segments}</div>
  <div style="position:absolute;top:-7px;left:{position}%;transform:translateX(-50%);">
    <div style="width:0;height:0;border-left:7px solid transparent;
                border-right:7px solid transparent;border-top:9px solid {INK};"></div>
  </div>
  <div style="position:absolute;top:26px;left:{position}%;transform:translateX(-50%);">
    <div style="width:2px;height:9px;background:{INK};margin:0 auto;"></div>
  </div>
</div>
<div class="aq-scale-labels">
  <span style="flex:50">0</span><span style="flex:50">50</span>
  <span style="flex:100">100</span><span style="flex:100">200</span>
  <span style="flex:100">300</span><span style="flex:100;text-align:right">500</span>
</div>
"""


def reading_card(city, state, result) -> str:
    """The headline reading. Colour comes from the data, not the theme."""
    return f"""
<div class="aq-card">
  <p class="aq-legend">Current reading</p>
  <div class="aq-place">{city}, {state}</div>
  <div class="aq-reading">
    <div class="aq-value" style="color:{result['colour']}">{result['aqi']:.0f}</div>
    <div class="aq-unit">AQI<br>Index</div>
  </div>
  <div class="aq-verdict" style="color:{result['colour']}">{result['verdict']}</div>
  <div class="aq-advice">{result['category']} — {result['advice']}</div>
  {band_scale(result['aqi'])}
</div>
"""


# ==========================================================================
# Masthead
# ==========================================================================

st.markdown(
    '<div class="aq-head">'
    '<p class="aq-eyebrow">Air quality index · India · live</p>'
    '<h1 class="aq-title">Smart City AQI</h1>'
    '<p class="aq-sub">Live pollutant readings from OpenWeatherMap, scored by an '
    'XGBoost model trained on 24,850 CPCB records. Pick a city to see its '
    'current index, the next 24 hours, and how it compares.</p>'
    '</div>',
    unsafe_allow_html=True,
)

cities = load_cities()
api_key = get_api_key()

if api_key is None:
    st.error(
        "No API key configured. Create `.streamlit/secrets.toml` containing:\n\n"
        '```toml\nOWM_API_KEY = "your_key_here"\n```\n\n'
        "On Streamlit Cloud, add it under Settings → Secrets instead."
    )
    st.stop()


# ==========================================================================
# Location picker
# ==========================================================================

pick_state, pick_city, pick_go = st.columns([2, 2, 1])

with pick_state:
    state = st.selectbox("State", sorted(cities["state"].unique()))

state_cities = cities[cities["state"] == state]

with pick_city:
    city = st.selectbox("City", sorted(state_cities["city"].unique()))

with pick_go:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    analyse = st.button("Analyse", use_container_width=True)


if not analyse:
    st.markdown(
        '<div class="aq-card"><p class="aq-legend">Ready</p>'
        '<p style="color:%s;margin:0">Choose a state and city, then press '
        '<b>Analyse</b>.</p></div>' % INK_SOFT,
        unsafe_allow_html=True,
    )
    st.stop()


# ==========================================================================
# Fetch and predict
# ==========================================================================

selected = state_cities[state_cities["city"] == city].iloc[0]
lat, lon = float(selected["lat"]), float(selected["lon"])

try:
    with st.spinner(f"Reading {city}..."):
        current = fetch_current(lat, lon, api_key)
except Exception as exc:
    st.error(f"Could not fetch pollution data: {exc}")
    st.stop()

pollutants = current["pollutants"]

try:
    # predict_from_api() handles the CO unit conversion and season encoding.
    result = predict_from_api(pollutants)
except Exception as exc:
    st.error(f"Prediction failed: {exc}")
    st.stop()


# ==========================================================================
# Headline
# ==========================================================================

head_left, head_right = st.columns([3, 2])

with head_left:
    st.markdown(reading_card(city, state, result), unsafe_allow_html=True)

with head_right:
    dominant = max(pollutants, key=pollutants.get)
    rows = "".join(
        f'<div class="aq-row"><span class="k">{name}</span>'
        f'<span class="v">{value:.1f}</span></div>'
        for name, value in pollutants.items()
    )
    st.markdown(
        f'<div class="aq-card"><p class="aq-legend">Pollutants · µg/m³</p>{rows}'
        f'<div style="margin-top:14px;font-size:13px;color:{INK_SOFT}">'
        f'Highest concentration: <b style="color:{INK}">{dominant}</b></div></div>',
        unsafe_allow_html=True,
    )

st.caption(f"Reading taken {current.get('timestamp_utc','')} UTC · {lat:.4f}, {lon:.4f}")


# ==========================================================================
# Analysis tabs
# ==========================================================================

tab_forecast, tab_breakdown, tab_compare, tab_map, tab_model = st.tabs(
    ["24-hour outlook", "Pollutant profile", "City comparison", "Location", "Model"]
)


# --- forecast -------------------------------------------------------------

with tab_forecast:
    try:
        with st.spinner("Fetching forecast..."):
            forecast = fetch_forecast(lat, lon, api_key, hours=24)
    except Exception as exc:
        st.warning(f"Forecast unavailable: {exc}")
        forecast = []

    if forecast:
        rows = []
        for record in forecast:
            stamp = datetime.fromisoformat(record["timestamp_utc"])
            predicted = predict_from_api(record["pollutants"], month=stamp.month)
            rows.append({
                "time": stamp,
                "aqi": predicted["aqi"],
                "category": predicted["category"],
            })

        fdf = pd.DataFrame(rows)

        fig = go.Figure()

        for lo, hi, label, colour in BANDS:
            fig.add_hrect(y0=lo, y1=hi, fillcolor=colour, opacity=0.10,
                          line_width=0, layer="below")

        fig.add_trace(go.Scatter(
            x=fdf["time"], y=fdf["aqi"],
            mode="lines+markers",
            line=dict(width=2.5, color=INK),
            marker=dict(size=5, color=INK),
            hovertemplate="%{x|%d %b %H:%M}<br>AQI %{y:.0f}<extra></extra>",
            name="Predicted AQI",
        ))

        fig.update_layout(
            **PLOT_LAYOUT,
            title="Predicted AQI, next 24 hours",
            height=420,
            showlegend=False,
        )
        fig.update_yaxes(title="AQI", range=[0, max(500, fdf["aqi"].max() * 1.15)])
        fig.update_xaxes(title="Time (UTC)")

        st.plotly_chart(fig, use_container_width=True)

        peak = fdf.loc[fdf["aqi"].idxmax()]
        trough = fdf.loc[fdf["aqi"].idxmin()]

        a, b, c = st.columns(3)
        a.metric("Now", f"{result['aqi']:.0f}")
        b.metric("Worst expected", f"{peak['aqi']:.0f}",
                 delta=f"{peak['aqi'] - result['aqi']:+.0f}")
        c.metric("Best expected", f"{trough['aqi']:.0f}",
                 delta=f"{trough['aqi'] - result['aqi']:+.0f}")

        st.caption(
            f"Worst air expected at {peak['time'].strftime('%d %b, %H:%M')} UTC "
            f"({peak['category']}). Cleanest at "
            f"{trough['time'].strftime('%d %b, %H:%M')} UTC ({trough['category']})."
        )


# --- pollutant profile ----------------------------------------------------

with tab_breakdown:
    profile = pd.DataFrame({
        "pollutant": list(pollutants.keys()),
        "value": list(pollutants.values()),
    }).sort_values("value")

    fig = go.Figure(go.Bar(
        x=profile["value"], y=profile["pollutant"],
        orientation="h",
        marker=dict(color=result["colour"]),
        text=[f"{v:.1f}" for v in profile["value"]],
        textposition="outside",
        hovertemplate="%{y}: %{x:.1f} µg/m³<extra></extra>",
    ))

    fig.update_layout(
        **PLOT_LAYOUT,
        title=f"Pollutant concentrations · {city}",
        height=380,
        showlegend=False,
    )
    fig.update_xaxes(title="µg/m³")

    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        f"""
<div class="aq-card"><p class="aq-legend">How the model weighs these</p>
<div class="aq-row"><span class="k">PM2.5</span><span class="v">42% of decisions</span></div>
<div class="aq-row"><span class="k">CO</span><span class="v">25%</span></div>
<div class="aq-row"><span class="k">PM10</span><span class="v">19%</span></div>
<div class="aq-row"><span class="k">Season</span><span class="v">4%</span></div>
<div class="aq-row"><span class="k">NO2 · month · SO2 · NH3 · O3</span><span class="v">10% combined</span></div>
<div style="margin-top:12px;font-size:13px;color:{INK_SOFT}">
Fine particulate matter dominates the index. All values are as returned by the
API in µg/m³; CO is converted to mg/m³ internally to match the training data.
</div></div>
""",
        unsafe_allow_html=True,
    )


# --- city comparison ------------------------------------------------------

with tab_compare:
    st.markdown(
        f'<p style="color:{INK_SOFT};font-size:13px;margin-bottom:10px">'
        "Compare up to six cities. Each one is a separate API call, so keep "
        "the list short — the free tier allows about 1,000 calls a day."
        "</p>",
        unsafe_allow_html=True,
    )

    labels = [f"{r.city}, {r.state}" for r in cities.itertuples()]
    default = [f"{city}, {state}"]

    chosen = st.multiselect(
        "Cities", labels, default=default, max_selections=6,
    )

    if st.button("Compare"):
        records = []

        progress = st.progress(0.0)
        for index, label in enumerate(chosen):
            name = label.split(",")[0].strip()
            row = cities[cities["city"] == name].iloc[0]

            try:
                data = fetch_current(float(row["lat"]), float(row["lon"]), api_key)
                scored = predict_from_api(data["pollutants"])
                records.append({
                    "City": name,
                    "State": row["state"],
                    "AQI": scored["aqi"],
                    "Category": scored["category"],
                    "colour": scored["colour"],
                })
            except Exception as exc:
                st.warning(f"{name}: {exc}")

            progress.progress((index + 1) / max(len(chosen), 1))

        progress.empty()

        if records:
            cdf = pd.DataFrame(records).sort_values("AQI")

            fig = go.Figure(go.Bar(
                x=cdf["AQI"], y=cdf["City"],
                orientation="h",
                marker=dict(color=cdf["colour"]),
                text=[f"{v:.0f}" for v in cdf["AQI"]],
                textposition="outside",
                hovertemplate="%{y}: AQI %{x:.0f}<extra></extra>",
            ))
            fig.update_layout(
                **PLOT_LAYOUT,
                title="Cleanest to worst, right now",
                height=90 + 46 * len(cdf),
                showlegend=False,
            )
            fig.update_xaxes(title="AQI")

            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(
                cdf[["City", "State", "AQI", "Category"]],
                use_container_width=True,
                hide_index=True,
            )


# --- location -------------------------------------------------------------

with tab_map:
    st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}), zoom=9)
    st.caption(f"{city}, {state} — {lat:.4f}, {lon:.4f}")


# --- model ----------------------------------------------------------------

with tab_model:
    left, right = st.columns(2)

    with left:
        st.markdown(
            """
<div class="aq-card"><p class="aq-legend">Model comparison</p>
<div class="aq-row"><span class="k">XGBoost · selected</span><span class="v">R² 0.929</span></div>
<div class="aq-row"><span class="k">Random Forest</span><span class="v">R² 0.925</span></div>
<div class="aq-row"><span class="k">Linear Regression</span><span class="v">R² 0.781</span></div>
</div>
""",
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            """
<div class="aq-card"><p class="aq-legend">Selected model</p>
<div class="aq-row"><span class="k">RMSE</span><span class="v">30.11</span></div>
<div class="aq-row"><span class="k">MAE</span><span class="v">18.66</span></div>
<div class="aq-row"><span class="k">Category accuracy</span><span class="v">78.6%</span></div>
<div class="aq-row"><span class="k">Training rows</span><span class="v">24,850</span></div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
<div class="aq-card"><p class="aq-legend">Limitations</p>
<p style="font-size:14px;color:{INK_SOFT};margin:0">
Trained on CPCB station data from Indian cities between 2015 and 2020, so
accuracy is best where monitoring stations are dense. AQI above 500 was capped
during training because the index is defined on a 0–500 scale. These are
model estimates and are not a substitute for official CPCB bulletins.
</p></div>
""",
        unsafe_allow_html=True,
    )
