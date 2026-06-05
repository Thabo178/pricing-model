"""
Structured Note Pricer — Streamlit Dashboard

Launch: double-click start.command (Mac) or start.bat (Windows)
        or run: streamlit run dashboard.py
"""

import calendar
import numpy as np
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Page config + custom CSS
# ---------------------------------------------------------------------------

def _make_hc_icon():
    from PIL import Image, ImageDraw, ImageFont
    img  = Image.new("RGB", (64, 64), color="#1e3a5f")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "HC", font=font)
    x = (64 - (bbox[2] - bbox[0])) // 2 - bbox[0]
    y = (64 - (bbox[3] - bbox[1])) // 2 - bbox[1]
    draw.text((x, y), "HC", fill="#ffffff", font=font)
    return img

st.set_page_config(
    page_title="Structured Note Pricer | Ryan Hysmith",
    page_icon=_make_hc_icon(),
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', sans-serif;
    background-color: #ffffff;
    color: #1a1a2e;
    font-size: 15px;
}

/* ── Shrink page margins ── */
.main .block-container {
    padding: 0.75rem 2rem 1rem;
    max-width: 100%;
}

/* ── Streamlit top toolbar — remove bottom padding that hides the title ── */
.st-emotion-cache-12fmjuu {
    padding-bottom: 0 !important;
}

/* ── Tighten vertical spacing between widgets ── */
.stVerticalBlock > div {
    gap: 0.35rem;
}
div[data-testid="column"] > div[data-testid="stVerticalBlock"] > div {
    gap: 0.35rem;
}

/* ── Tab bar ── */
[data-baseweb="tab-list"] {
    border-bottom: 2px solid #e2e8f0;
    gap: 0;
    margin-bottom: 0.75rem;
}
[data-baseweb="tab"] {
    font-size: 0.9rem;
    font-weight: 500;
    color: #64748b;
    padding: 0.5rem 1.1rem;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: #1e3a5f;
    border-bottom-color: #1e3a5f;
    font-weight: 700;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.7rem 1rem;
}
[data-testid="stMetricLabel"] p {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #64748b;
}
[data-testid="stMetricValue"] {
    font-size: 1.45rem;
    font-weight: 700;
    color: #1e3a5f;
}

/* ── Primary buttons ── */
[kind="primary"] button {
    background-color: #1e3a5f !important;
    color: #ffffff !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em;
    font-size: 0.9rem !important;
}
[kind="primary"] button:hover {
    background-color: #2d5282 !important;
}

/* ── Dividers ── */
hr {
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 0.6rem 0;
}

/* ── Dataframes ── */
[data-testid="stDataFrame"] {
    border-radius: 6px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
}

/* ── Headings ── */
h1 { font-size: 1.5rem !important; margin-bottom: 0 !important; }
h2 { font-size: 1.15rem !important; color: #1e3a5f; font-weight: 700; margin: 0.4rem 0 0.2rem; }
h3 { font-size: 1rem !important; color: #1e3a5f; font-weight: 700; margin: 0.3rem 0 0.1rem; }
h4, h5 { font-size: 0.9rem !important; color: #1e3a5f; font-weight: 700; margin: 0.3rem 0 0.1rem; }

/* ── Widget labels ── */
[data-testid="stWidgetLabel"] p {
    font-size: 0.85rem;
    font-weight: 500;
    color: #374151;
}

/* ── Smaller select/input boxes ── */
[data-baseweb="input"] input,
[data-baseweb="select"] div {
    font-size: 0.875rem !important;
}

/* ── Captions ── */
[data-testid="stCaptionContainer"] p {
    color: #64748b;
    font-size: 0.82rem;
}

/* ── Info / alert boxes ── */
[data-testid="stAlert"] {
    border-radius: 6px;
    padding: 0.5rem 0.75rem;
    font-size: 0.85rem;
}

/* ── Expanders ── */
[data-testid="stExpander"] summary {
    font-weight: 600;
    font-size: 0.88rem;
    color: #1e3a5f;
}

/* ── Vertical divider between input cols and results ── */
.results-panel {
    border-left: 1px solid #e2e8f0;
    padding-left: 1.5rem;
}

/* ── Section label ── */
.section-label {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94a3b8;
    margin-bottom: 0.2rem;
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

UNDERLIERS = [
    "NVDA",
    "TSLA",
    "AMD",
    "META",
    "GOOGL",
    "AMZN",
    "HOOD",
    "LULU",
    "NOW",
    "PLTR",
    "WFC",
    "SPY",
]

DEFAULT_SPOTS = {
    "NVDA": 219.16,
    "TSLA": 180.0,
    "AMD": 160.0,
    "META": 510.0,
    "GOOGL": 175.0,
    "AMZN": 190.0,
    "HOOD": 22.0,
    "LULU": 85.0,
    "NOW": 820.0,
    "PLTR": 25.0,
    "WFC": 57.0,
    "SPY": 525.0,
}


def _add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _generate_obs_dates(issue: date, maturity: date, freq: str) -> list:
    step = {"Monthly": 1, "Quarterly": 3, "Semi-Annual": 6}[freq]
    dates, cur = [], _add_months(issue, step)
    while cur <= maturity:
        dates.append(cur.strftime("%Y-%m-%d"))
        cur = _add_months(cur, step)
    return dates


def _build_note_dict(
    underlier,
    spot,
    face_value,
    issue_date,
    maturity_date,
    obs_freq,
    autocall_pct,
    coupon_pct,
    knockin_pct,
    coupon_rate,
    rfr,
    credit_spread_bps=0,
) -> dict:
    note = {
        "underlier": underlier,
        "spot": spot,
        "face_value": face_value,
        "issue_date": issue_date.strftime("%Y-%m-%d"),
        "maturity_date": maturity_date.strftime("%Y-%m-%d"),
        "observation_dates": _generate_obs_dates(issue_date, maturity_date, obs_freq),
        "autocall_barrier": autocall_pct / 100,
        "coupon_barrier": coupon_pct / 100,
        "knockin_barrier": knockin_pct / 100,
        "coupon_rate": coupon_rate / 100,
        "risk_free_rate": rfr / 100,
    }
    if credit_spread_bps:
        note["credit_spread"] = credit_spread_bps / 10000
    return note


def _build_wo_note_dict(
    tickers,
    spots,
    corr_matrix,
    face_value,
    issue_date,
    maturity_date,
    obs_freq,
    autocall_pct,
    coupon_pct,
    knockin_pct,
    coupon_rate,
    rfr,
    credit_spread_bps=0,
) -> dict:
    note = {
        "underliers": tickers,
        "spots": spots,
        "correlation_matrix": corr_matrix,
        "face_value": face_value,
        "issue_date": issue_date.strftime("%Y-%m-%d"),
        "maturity_date": maturity_date.strftime("%Y-%m-%d"),
        "observation_dates": _generate_obs_dates(issue_date, maturity_date, obs_freq),
        "autocall_barrier": autocall_pct / 100,
        "coupon_barrier": coupon_pct / 100,
        "knockin_barrier": knockin_pct / 100,
        "coupon_rate": coupon_rate / 100,
        "risk_free_rate": rfr / 100,
    }
    if credit_spread_bps:
        note["credit_spread"] = credit_spread_bps / 10000
    return note


def _recommendation_badge(rec: str) -> str:
    colour = {"Buy": "#16a34a", "Skip": "#dc2626", "Gray Zone": "#d97706"}.get(
        rec, "#64748b"
    )
    return (
        f'<span style="background:{colour};color:#fff;padding:4px 14px;'
        f'border-radius:4px;font-weight:700;font-size:1rem;">{rec}</span>'
    )


def _label(text):
    st.markdown(f'<p class="section-label">{text}</p>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    "<h1 style='color:#1e3a5f;font-weight:800;letter-spacing:-0.02em;margin-top:0.5rem;'>"
    "Structured Note Pricer</h1>"
    "<p style='color:#94a3b8;font-size:0.82rem;margin-top:0.1rem;margin-bottom:0.5rem;'>"
    "Phoenix Autocallable &nbsp;·&nbsp; Single-Asset &amp; Worst-Of &nbsp;·&nbsp; "
    "Heston Stochastic Volatility &nbsp;·&nbsp; ORATS Live Data</p>",
    unsafe_allow_html=True,
)

tab_price, tab_vol, tab_cal, tab_wo, tab_port, tab_offer = st.tabs(
    [
        "Note Pricer",
        "Vol Surface",
        "Calibration",
        "Worst-Of Pricer",
        "Portfolio",
        "Offering Evaluator",
    ]
)

# ===========================================================================
# TAB 1 — NOTE PRICER
# ===========================================================================

with tab_price:
    col_a, col_b, col_out = st.columns([1, 1, 1.6])

    # ── Column A: Underlier & dates ──────────────────────────────────────
    with col_a:
        _label("Underlier")
        underlier = st.selectbox(
            "Ticker", UNDERLIERS, key="p_underlier", label_visibility="collapsed"
        )

        sp_c1, sp_c2 = st.columns(2)
        with sp_c1:
            spot = st.number_input(
                "Spot ($)",
                min_value=1.0,
                value=DEFAULT_SPOTS.get(underlier, 100.0),
                step=0.01,
                format="%.2f",
                key=f"p_spot_{underlier}",
            )
        with sp_c2:
            face_value = st.number_input(
                "Face Value ($)",
                min_value=100.0,
                value=1000.0,
                step=100.0,
                key="p_face",
            )

        st.markdown("<hr>", unsafe_allow_html=True)
        _label("Schedule")

        d1, d2 = st.columns(2)
        with d1:
            issue_date = st.date_input(
                "Issue Date", value=date(2026, 6, 3), key="p_issue"
            )
        with d2:
            maturity_date = st.date_input(
                "Maturity Date", value=date(2027, 12, 3), key="p_mat"
            )

        obs_freq = st.selectbox(
            "Observation Frequency",
            ["Quarterly", "Monthly", "Semi-Annual"],
            key="p_freq",
        )

        st.markdown("<hr>", unsafe_allow_html=True)
        _label("Model Settings")

        m1, m2 = st.columns(2)
        with m1:
            memory_on = st.checkbox(
                "Memory Coupon",
                value=False,
                key="p_memory",
                help="Unpaid coupons accrue and are paid at the next qualifying observation.",
            )
        with m2:
            n_paths = st.select_slider(
                "MC Paths",
                options=[10_000, 50_000, 100_000],
                value=50_000,
                format_func=lambda x: f"{x:,}",
                key="p_npaths",
            )

    # ── Column B: Barriers & rates ───────────────────────────────────────
    with col_b:
        _label("Barrier Structure")
        autocall_pct = st.slider(
            "Autocall Barrier", 80, 115, 100, step=5, format="%d%%", key="p_autocall"
        )
        coupon_pct = st.slider(
            "Coupon Barrier", 50, 95, 75, step=5, format="%d%%", key="p_coupon"
        )
        knockin_pct = st.slider(
            "Knock-In Barrier", 40, 80, 65, step=5, format="%d%%", key="p_knockin"
        )

        st.markdown("<hr>", unsafe_allow_html=True)
        _label("Rates")

        r1, r2 = st.columns(2)
        with r1:
            coupon_rate = st.number_input(
                "Annual Coupon (%)",
                min_value=0.0,
                max_value=50.0,
                value=12.0,
                step=0.5,
                key="p_cpn",
            )
        with r2:
            rfr = st.number_input(
                "Risk-Free Rate (%)",
                min_value=0.0,
                max_value=20.0,
                value=3.75,
                step=0.25,
                key="p_rfr",
            )

        credit_spread_bps = st.number_input(
            "Issuer Credit Spread (bps)",
            min_value=0,
            max_value=500,
            value=0,
            step=5,
            help="§6.1 — Treasury + CDS spread. Added to discount rate. Typical A-rated issuer: 50–150 bps.",
            key="p_cs",
        )

        st.markdown("<hr>", unsafe_allow_html=True)
        price_btn = st.button(
            "Run Pricing", type="primary", use_container_width=True, key="p_btn"
        )

    # ── Column C: Results ────────────────────────────────────────────────
    with col_out:
        st.markdown('<div class="results-panel">', unsafe_allow_html=True)
        _label("Results")

        if price_btn:
            note_dict = _build_note_dict(
                underlier,
                spot,
                face_value,
                issue_date,
                maturity_date,
                obs_freq,
                autocall_pct,
                coupon_pct,
                knockin_pct,
                coupon_rate,
                rfr,
                credit_spread_bps=credit_spread_bps,
            )
            note_dict["memory"] = memory_on
            if not note_dict["observation_dates"]:
                st.error(
                    "No observation dates — check that Maturity Date is after Issue Date."
                )
            else:
                with st.spinner(f"Pricing {underlier} · {n_paths:,} paths …"):
                    try:
                        from pricer.pricer import price_note_dict

                        result = price_note_dict(
                            note_dict, n_paths=n_paths, memory=memory_on
                        )
                        st.session_state["last_result"] = result
                        st.session_state["last_note"] = note_dict
                    except Exception as e:
                        st.error(f"Pricing failed: {e}")
                        st.session_state.pop("last_result", None)

        if "last_result" in st.session_state:
            r = st.session_state["last_result"]
            n = st.session_state["last_note"]

            rm1, rm2, rm3 = st.columns(3)
            rm1.metric("Fair Value", f"{r['npv_pct']:.2f}%")
            rm2.metric("Dollar FV", f"${r['npv_dollar']:,.2f}")
            rm3.metric("MC Std Err", f"±{r['se_bps']:.1f} bps")

            if credit_spread_bps:
                st.info(
                    f"Credit spread of {credit_spread_bps} bps applied to discount curve (§6.1).",
                    icon="ℹ️",
                )

            with st.expander("Greeks  (§6.3)", expanded=False):
                g_paths = st.select_slider(
                    "Paths for Greeks",
                    options=[10_000, 20_000, 30_000],
                    value=20_000,
                    format_func=lambda x: f"{x:,}",
                    key="p_g_paths",
                )
                if st.button("Compute Greeks", key="p_greeks_btn"):
                    with st.spinner("Computing Greeks (5 reprice calls) …"):
                        try:
                            from pricer.greeks import compute_greeks

                            st.session_state["last_greeks"] = compute_greeks(
                                n, n_paths=g_paths
                            )
                        except Exception as e:
                            st.error(f"Greeks failed: {e}")

                if "last_greeks" in st.session_state:
                    g = st.session_state["last_greeks"]
                    gc1, gc2, gc3, gc4 = st.columns(4)
                    gc1.metric("Δ (% / 1% spot)", f"{g['delta_pct']:+.3f}%")
                    gc2.metric("Δ ($ / $1 spot)", f"${g['delta_dollar']:+.4f}")
                    gc3.metric("ν (% / 1 vol pt)", f"{g['vega_pct']:+.3f}%")
                    gc4.metric("Θ ($ / day)", f"${g['theta_dollar']:+.4f}")
                    st.caption(
                        f"Gamma: ${g['gamma_dollar']:+.6f} per $1² · ±1% central-difference"
                    )

            st.markdown("<hr>", unsafe_allow_html=True)
            _label("Term Sheet Summary")

            obs = n["observation_dates"]
            cs = n.get("credit_spread", 0)
            summary = {
                "Underlier": n["underlier"],
                "Spot / Face": f"${n['spot']:,.2f}  /  ${n['face_value']:,.0f}",
                "Dates": f"{n['issue_date']} → {n['maturity_date']}",
                "Observations": f"{len(obs)} ({obs[0]} → {obs[-1]})",
                "Autocall / Coupon / KI": (
                    f"{n['autocall_barrier']*100:.0f}%  /  "
                    f"{n['coupon_barrier']*100:.0f}%  /  "
                    f"{n['knockin_barrier']*100:.0f}%"
                ),
                "Coupon / RFR": f"{n['coupon_rate']*100:.2f}%  /  {n['risk_free_rate']*100:.3f}%",
                "Credit Spread": f"{cs*10000:.0f} bps" if cs else "None",
                "Memory Coupon": "Yes" if n.get("memory") else "No",
                "MC Paths": f"{r['n_paths']:,}",
            }
            st.dataframe(
                pd.DataFrame.from_dict(summary, orient="index", columns=["Value"]),
                use_container_width=True,
            )
        else:
            st.info(
                "Configure the term sheet in the columns on the left, then click **Run Pricing**."
            )

        st.markdown("</div>", unsafe_allow_html=True)

# ===========================================================================
# TAB 2 — VOL SURFACE
# ===========================================================================

with tab_vol:
    col_v1, col_v2 = st.columns([0.22, 0.78])

    with col_v1:
        _label("Ticker")
        vol_ticker = st.selectbox(
            "Ticker", UNDERLIERS, key="v_ticker", label_visibility="collapsed"
        )
        fetch_btn = st.button(
            "Fetch from ORATS", type="primary", key="v_fetch", use_container_width=True
        )

    with col_v2:
        if fetch_btn:
            with st.spinner(f"Fetching {vol_ticker} from ORATS …"):
                try:
                    from pricer.orats import get_monies_implied, get_smv_summary

                    st.session_state["vol_mono"] = get_monies_implied(vol_ticker)
                    st.session_state["vol_smv"] = get_smv_summary(vol_ticker)
                    st.session_state["vol_ticker"] = vol_ticker
                except Exception as e:
                    st.error(f"ORATS fetch failed: {e}")

        if (
            st.session_state.get("vol_ticker") == vol_ticker
            and "vol_mono" in st.session_state
        ):
            df = st.session_state["vol_mono"]
            smv = st.session_state["vol_smv"]

            if not smv.empty:
                row = smv.iloc[0]
                s1, s2, s3, s4 = st.columns(4)
                s1.metric("Spot", f"${float(row.get('stockPrice', 0)):,.2f}")
                s2.metric("30d ATM IV", f"{float(row.get('iv30d', 0))*100:.1f}%")
                s3.metric("Skew (30d)", f"{float(row.get('rSlp30', 0)):.3f}")
                s4.metric(
                    "Implied Move", f"{float(row.get('impliedMove', 0))*100:.1f}%"
                )

            st.markdown("<hr>", unsafe_allow_html=True)

            want = ["expirDate", "atmiv", "slope", "vol25", "vol50", "vol75", "vol5"]
            show = [c for c in want if c in df.columns]
            disp = df[show].copy()
            disp.rename(
                columns={
                    "expirDate": "Expiry",
                    "atmiv": "ATM IV",
                    "slope": "Skew",
                    "vol25": "25Δ IV",
                    "vol50": "50Δ IV",
                    "vol75": "75Δ IV",
                    "vol5": "5Δ IV",
                },
                inplace=True,
            )
            for col in ["ATM IV", "25Δ IV", "50Δ IV", "75Δ IV", "5Δ IV"]:
                if col in disp.columns:
                    disp[col] = (disp[col].astype(float) * 100).round(2).astype(
                        str
                    ) + "%"
            st.dataframe(disp, use_container_width=True, hide_index=True)

            if "expirDate" in df.columns and "atmiv" in df.columns:
                chart_df = df[["expirDate", "atmiv"]].copy()
                chart_df["ATM IV (%)"] = chart_df["atmiv"].astype(float) * 100
                st.line_chart(
                    chart_df.set_index("expirDate")[["ATM IV (%)"]],
                    use_container_width=True,
                )
                st.caption(
                    "ATM Implied Volatility (%) by Expiry — source: ORATS /monies/implied"
                )
        else:
            st.info(
                "Select a ticker and click **Fetch from ORATS** to load the live vol surface."
            )

# ===========================================================================
# TAB 3 — CALIBRATION
# ===========================================================================

with tab_cal:
    col_c1, col_c2 = st.columns([0.32, 0.68])

    with col_c1:
        _label("Underlier")
        cal_ticker = st.selectbox(
            "Ticker", UNDERLIERS, key="c_ticker", label_visibility="collapsed"
        )

        cc1, cc2 = st.columns(2)
        with cc1:
            cal_spot = st.number_input(
                "Spot ($)",
                value=float(DEFAULT_SPOTS.get(cal_ticker, 100.0)),
                min_value=1.0,
                step=1.0,
                key=f"c_spot_{cal_ticker}",
            )
        with cc2:
            cal_rfr = st.number_input("RFR (%)", value=3.75, step=0.25, key="c_rfr")

        use_orats = st.checkbox("Use live ORATS surface", value=True, key="c_orats")
        if not use_orats:
            st.caption("Mock mode — calibrates to a synthetic surface (RMSE ≈ 0).")

        cal_btn = st.button(
            "Run Calibration", type="primary", use_container_width=True, key="c_btn"
        )

        st.markdown("<hr>", unsafe_allow_html=True)
        st.caption(
            "DE global search → L-BFGS-B polish (§8.1).  \n"
            "Bounds: κ [0.5,8] · θ [0.01,0.5] · σ [0.1,2.5] · ρ [−0.95,−0.1] · v₀ [0.01,0.6]"
        )

    with col_c2:
        if cal_btn:
            with st.spinner(f"Calibrating {cal_ticker} …"):
                try:
                    import QuantLib as ql

                    today = ql.Date.todaysDate()
                    rfr = cal_rfr / 100.0
                    if use_orats:
                        from pricer.orats import build_calibration_set, live_spot
                        from pricer.calibration import (
                            calibrate_heston_orats,
                            save_calibrated,
                        )

                        try:
                            spot = live_spot(cal_ticker)
                        except Exception:
                            spot = cal_spot
                        cal_set = build_calibration_set(cal_ticker, today, spot, r=rfr)
                        if not cal_set:
                            st.error(f"No ORATS data for {cal_ticker}.")
                        else:
                            result = calibrate_heston_orats(
                                cal_ticker, today, spot, rfr, cal_set
                            )
                            save_calibrated(result)
                            st.session_state["cal_result"] = result
                            st.session_state["cal_live_spot"] = spot
                    else:
                        from pricer.calibration import (
                            generate_mock_surface,
                            calibrate_heston,
                            save_calibrated,
                        )

                        surface = generate_mock_surface(
                            cal_ticker, cal_spot, rfr, today=today
                        )
                        result = calibrate_heston(
                            cal_ticker, cal_spot, rfr, surface, today=today
                        )
                        save_calibrated(result)
                        st.session_state["cal_result"] = result
                        st.session_state.pop("cal_live_spot", None)
                except Exception as e:
                    st.error(f"Calibration failed: {e}")

        if "cal_result" in st.session_state:
            r = st.session_state["cal_result"]
            if st.session_state.get("cal_live_spot"):
                st.caption(
                    f"Live spot from ORATS: **${st.session_state['cal_live_spot']:,.2f}**"
                )

            feller_ok = r.get("feller_satisfied", True)
            if not feller_ok:
                st.warning(
                    f"Feller condition violated: 2κθ = {2*r['kappa']*r['theta']:.4f} < σ² = {r['sigma']**2:.4f}. "
                    "Full-truncation MC handles this numerically — result is still valid. (§8.2)",
                    icon="⚠️",
                )

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Status", "Converged" if r["converged"] else "Did Not Converge")
            m2.metric("RMSE", f"{r['rmse']:.6f}")
            m3.metric("IV Points", str(r["n_points"]))
            m4.metric("Feller", "Satisfied" if feller_ok else "Violated")

            st.markdown("<hr>", unsafe_allow_html=True)
            _label("Calibrated Parameters")

            params = {
                "v₀  (initial variance)": f"{r['v0']:.6f}",
                "κ   (mean-reversion speed)": f"{r['kappa']:.6f}",
                "θ   (long-run variance)": f"{r['theta']:.6f}",
                "σ   (vol of vol)": f"{r['sigma']:.6f}",
                "ρ   (asset / vol corr.)": f"{r['rho']:.6f}",
            }
            st.dataframe(
                pd.DataFrame.from_dict(params, orient="index", columns=["Value"]),
                use_container_width=True,
            )
            st.caption(f"Saved → data/calibrated/{r['underlier']}.json")
        else:
            st.info("Select a ticker and click **Run Calibration**.")

# ===========================================================================
# TAB 4 — WORST-OF PRICER
# ===========================================================================

with tab_wo:
    col_wa, col_wb, col_wout = st.columns([1, 1, 1.6])

    # ── Column A: Basket & correlations ─────────────────────────────────
    with col_wa:
        _label("Basket")
        n_assets = st.radio(
            "Size",
            [2, 3],
            horizontal=True,
            key="wo_n",
            format_func=lambda x: f"{x} Underliers",
        )

        wa1, wa2 = st.columns(2)
        with wa1:
            wo_t1 = st.selectbox("Underlier 1", UNDERLIERS, index=0, key="wo_t1")
        with wa2:
            wo_s1 = st.number_input(
                "Spot 1 ($)",
                value=float(DEFAULT_SPOTS[wo_t1]),
                min_value=1.0,
                step=0.01,
                format="%.2f",
                key=f"wo_s1_{wo_t1}",
            )

        wb1, wb2 = st.columns(2)
        with wb1:
            wo_t2 = st.selectbox("Underlier 2", UNDERLIERS, index=1, key="wo_t2")
        with wb2:
            wo_s2 = st.number_input(
                "Spot 2 ($)",
                value=float(DEFAULT_SPOTS[wo_t2]),
                min_value=1.0,
                step=0.01,
                format="%.2f",
                key=f"wo_s2_{wo_t2}",
            )

        wo_t3, wo_s3 = None, None
        if n_assets == 3:
            wc1, wc2 = st.columns(2)
            with wc1:
                wo_t3 = st.selectbox("Underlier 3", UNDERLIERS, index=2, key="wo_t3")
            with wc2:
                wo_s3 = st.number_input(
                    "Spot 3 ($)",
                    value=float(DEFAULT_SPOTS[wo_t3]),
                    min_value=1.0,
                    step=0.01,
                    format="%.2f",
                    key=f"wo_s3_{wo_t3}",
                )

        st.markdown("<hr>", unsafe_allow_html=True)
        _label("Correlations")

        rho_12 = st.slider(
            f"ρ  {wo_t1}/{wo_t2}", -0.99, 0.99, 0.55, step=0.01, key="wo_r12"
        )
        rho_13, rho_23 = 0.0, 0.0
        if n_assets == 3:
            rho_13 = st.slider(
                f"ρ  {wo_t1}/{wo_t3}", -0.99, 0.99, 0.50, step=0.01, key="wo_r13"
            )
            rho_23 = st.slider(
                f"ρ  {wo_t2}/{wo_t3}", -0.99, 0.99, 0.50, step=0.01, key="wo_r23"
            )
            st.caption("Automatically projected to PSD before simulation.")

    # ── Column B: Note parameters ────────────────────────────────────────
    with col_wb:
        _label("Note Parameters")

        wd1, wd2 = st.columns(2)
        with wd1:
            wo_issue = st.date_input(
                "Issue Date", value=date(2026, 6, 3), key="wo_issue"
            )
        with wd2:
            wo_mat = st.date_input(
                "Maturity Date", value=date(2027, 12, 3), key="wo_mat"
            )

        we1, we2 = st.columns(2)
        with we1:
            wo_face = st.number_input(
                "Face Value ($)",
                min_value=100.0,
                value=1000.0,
                step=100.0,
                key="wo_face",
            )
        with we2:
            wo_freq = st.selectbox(
                "Frequency", ["Quarterly", "Monthly", "Semi-Annual"], key="wo_freq"
            )

        st.markdown("<hr>", unsafe_allow_html=True)
        _label("Barrier Structure")

        wo_autocall = st.slider(
            "Autocall Barrier", 80, 115, 100, step=5, format="%d%%", key="wo_autocall"
        )
        wo_coupon = st.slider(
            "Coupon Barrier", 50, 95, 75, step=5, format="%d%%", key="wo_coupon"
        )
        wo_knockin = st.slider(
            "Knock-In Barrier", 40, 80, 65, step=5, format="%d%%", key="wo_knockin"
        )

        st.markdown("<hr>", unsafe_allow_html=True)
        _label("Rates & Model")

        wf1, wf2 = st.columns(2)
        with wf1:
            wo_cpn = st.number_input(
                "Coupon (%)",
                min_value=0.0,
                max_value=50.0,
                value=12.0,
                step=0.5,
                key="wo_cpn",
            )
        with wf2:
            wo_rfr = st.number_input(
                "RFR (%)",
                min_value=0.0,
                max_value=20.0,
                value=3.75,
                step=0.25,
                key="wo_rfr",
            )

        wg1, wg2 = st.columns(2)
        with wg1:
            wo_cs = st.number_input(
                "Credit Spread (bps)",
                min_value=0,
                max_value=500,
                value=0,
                step=5,
                key="wo_cs",
            )
        with wg2:
            wo_paths = st.select_slider(
                "MC Paths",
                options=[10_000, 50_000, 100_000],
                value=50_000,
                format_func=lambda x: f"{x:,}",
                key="wo_npaths",
            )

        wo_btn = st.button(
            "Price Worst-Of", type="primary", use_container_width=True, key="wo_btn"
        )

    # ── Column C: Results ────────────────────────────────────────────────
    with col_wout:
        st.markdown('<div class="results-panel">', unsafe_allow_html=True)
        _label("Results")

        if wo_btn:
            if n_assets == 2:
                tickers = [wo_t1, wo_t2]
                spots = [wo_s1, wo_s2]
                corr = [[1.0, rho_12], [rho_12, 1.0]]
            else:
                tickers = [wo_t1, wo_t2, wo_t3]
                spots = [wo_s1, wo_s2, wo_s3]
                corr = [
                    [1.0, rho_12, rho_13],
                    [rho_12, 1.0, rho_23],
                    [rho_13, rho_23, 1.0],
                ]

            wo_note = _build_wo_note_dict(
                tickers,
                spots,
                corr,
                wo_face,
                wo_issue,
                wo_mat,
                wo_freq,
                wo_autocall,
                wo_coupon,
                wo_knockin,
                wo_cpn,
                wo_rfr,
                credit_spread_bps=wo_cs,
            )
            if not wo_note["observation_dates"]:
                st.error(
                    "No observation dates — check Maturity Date is after Issue Date."
                )
            else:
                with st.spinner(
                    f"Pricing {' / '.join(tickers)} worst-of · {wo_paths:,} paths …"
                ):
                    try:
                        from pricer.pricer import price_worst_of, price_note_dict

                        wo_result = price_worst_of(wo_note, n_paths=wo_paths)
                        base = {
                            k: v
                            for k, v in wo_note.items()
                            if k not in ("underliers", "spots", "correlation_matrix")
                        }
                        singles = [
                            price_note_dict(
                                {**base, "underlier": t, "spot": s}, n_paths=wo_paths
                            )
                            for t, s in zip(tickers, spots)
                        ]
                        st.session_state["wo_result"] = wo_result
                        st.session_state["wo_note"] = wo_note
                        st.session_state["wo_singles"] = singles
                    except Exception as e:
                        st.error(f"Pricing failed: {e}")
                        st.session_state.pop("wo_result", None)

        if "wo_result" in st.session_state:
            wo_r = st.session_state["wo_result"]
            wo_n = st.session_state["wo_note"]
            singles = st.session_state["wo_singles"]

            wm1, wm2, wm3 = st.columns(3)
            wm1.metric("Worst-Of FV", f"{wo_r['npv_pct']:.2f}%")
            wm2.metric(f"Per ${wo_r['face_value']:,.0f}", f"${wo_r['npv_dollar']:,.2f}")
            wm3.metric("MC Std Err", f"±{wo_r['se_bps']:.1f} bps")

            st.markdown("<hr>", unsafe_allow_html=True)
            _label("Single vs. Worst-Of Comparison")

            comp_rows = [
                {
                    "Structure": f"{s['underlier']} (single)",
                    "Fair Value": f"{s['npv_pct']:.2f}%",
                    "Dollar FV": f"${s['npv_dollar']:,.2f}",
                }
                for s in singles
            ]
            comp_rows.append(
                {
                    "Structure": f"Worst-Of  ({' / '.join(wo_n['underliers'])})",
                    "Fair Value": f"{wo_r['npv_pct']:.2f}%",
                    "Dollar FV": f"${wo_r['npv_dollar']:,.2f}",
                }
            )
            st.dataframe(
                pd.DataFrame(comp_rows), use_container_width=True, hide_index=True
            )

            discount = min(s["npv_pct"] for s in singles) - wo_r["npv_pct"]
            st.caption(
                f"Worst-of discount vs best single underlier: **{discount:.2f}%**"
            )

            st.markdown("<hr>", unsafe_allow_html=True)
            _label("Correlation Matrix")
            corr_df = pd.DataFrame(
                wo_n["correlation_matrix"],
                index=wo_n["underliers"],
                columns=wo_n["underliers"],
            )
            st.dataframe(corr_df.style.format("{:.2f}"), use_container_width=True)
        else:
            st.info(
                "Configure the basket and parameters, then click **Price Worst-Of**."
            )

        st.markdown("</div>", unsafe_allow_html=True)

# ===========================================================================
# TAB 5 — PORTFOLIO
# ===========================================================================

with tab_port:
    PORTFOLIO_PATH = Path(__file__).parent / "data" / "portfolio.json"

    col_po1, col_po2 = st.columns([0.22, 0.78])

    with col_po1:
        _label("Settings")
        port_paths = st.select_slider(
            "MC Paths per Note",
            options=[5_000, 10_000, 30_000, 50_000],
            value=10_000,
            format_func=lambda x: f"{x:,}",
            key="po_npaths",
        )
        port_btn = st.button(
            "Run Portfolio Pricing",
            type="primary",
            use_container_width=True,
            key="po_btn",
        )
        if PORTFOLIO_PATH.exists():
            try:
                import json as _json

                _pdata = _json.loads(PORTFOLIO_PATH.read_text())
                _n = len(
                    [_nt for _nt in _pdata.get("notes", []) if not _nt.get("_comment")]
                )
                st.caption(f"**{_n} notes** in portfolio.json")
            except Exception:
                pass
        else:
            st.warning("data/portfolio.json not found.")

        st.markdown("<hr>", unsafe_allow_html=True)
        st.caption(
            "Flags (§10):  \n"
            "**OK** — |dev| ≤ 100 bps  \n"
            "**Review** — ≤ 300 bps  \n"
            "**Flag ⚠** — > 300 bps"
        )

    with col_po2:
        if port_btn:
            if not PORTFOLIO_PATH.exists():
                st.error("data/portfolio.json not found.")
            else:
                with st.spinner(f"Pricing portfolio at {port_paths:,} paths/note …"):
                    try:
                        from pricer.portfolio import price_portfolio

                        port_results = price_portfolio(
                            str(PORTFOLIO_PATH), n_paths=port_paths
                        )
                        st.session_state["port_results"] = port_results
                    except Exception as e:
                        st.error(f"Portfolio pricing failed: {e}")
                        st.session_state.pop("port_results", None)

        if "port_results" in st.session_state:
            rows = st.session_state["port_results"]
            ok_rows = [r for r in rows if "error" not in r]

            if ok_rows:
                total_face = sum(r["face_value"] for r in ok_rows)
                avg_model = (
                    sum(r["model_fv"] * r["face_value"] for r in ok_rows) / total_face
                )
                flagged = sum(1 for r in ok_rows if r["flag"] not in ("OK", "N/A"))
                total_pnl = sum(r["pnl_vs_purchase"] or 0 for r in ok_rows)

                pm1, pm2, pm3, pm4 = st.columns(4)
                pm1.metric("Notes Priced", str(len(ok_rows)))
                pm2.metric("Wtd Avg Model FV", f"{avg_model:.2f}%")
                pm3.metric("Review / Flag", str(flagged))
                pm4.metric("P&L vs Purchase", f"${total_pnl:+,.0f}")
                st.markdown("<hr>", unsafe_allow_html=True)

            table_rows = []
            for r in rows:
                if "error" in r:
                    table_rows.append(
                        {
                            "CUSIP": r["cusip"],
                            "Issuer": r["issuer"],
                            "Structure": "ERROR",
                            "Underlier(s)": r["underliers"],
                            "Issuer Mark": "—",
                            "Model FV": "—",
                            "Dev (bps)": "—",
                            "SE (bps)": "—",
                            "Flag": "ERROR",
                        }
                    )
                else:
                    table_rows.append(
                        {
                            "CUSIP": r["cusip"],
                            "Issuer": r["issuer"],
                            "Structure": r["structure"],
                            "Underlier(s)": r["underliers"],
                            "Issuer Mark": (
                                f"{r['issuer_mark']:.2f}%" if r["issuer_mark"] else "—"
                            ),
                            "Model FV": f"{r['model_fv']:.2f}%",
                            "Dev (bps)": (
                                f"{r['deviation_bps']:+.0f}"
                                if r["deviation_bps"] is not None
                                else "—"
                            ),
                            "SE (bps)": f"±{r.get('se_bps', 0):.1f}",
                            "Flag": r["flag"],
                        }
                    )
            st.dataframe(
                pd.DataFrame(table_rows), use_container_width=True, hide_index=True
            )
            st.caption(
                "Deviation = (Model FV − Issuer Mark) × 100.  Positive = model prices richer than issuer."
            )
        else:
            st.info(
                "Click **Run Portfolio Pricing** to price all notes and compare against issuer marks."
            )

# ===========================================================================
# TAB 6 — OFFERING EVALUATOR
# ===========================================================================

with tab_offer:
    col_oa, col_ob, col_oout = st.columns([1, 1, 1.6])

    # ── Column A: Structure & underlier(s) ──────────────────────────────
    with col_oa:
        _label("Structure")
        oe_type = st.radio(
            "Type",
            ["Single Underlier", "Worst-Of Basket"],
            horizontal=True,
            key="oe_type",
        )

        if oe_type == "Single Underlier":
            _label("Underlier")
            oe_ul = st.selectbox(
                "Ticker", UNDERLIERS, key="oe_ul", label_visibility="collapsed"
            )
            oe_sp = st.number_input(
                "Spot ($)",
                value=float(DEFAULT_SPOTS[oe_ul]),
                min_value=1.0,
                step=0.01,
                format="%.2f",
                key=f"oe_sp_{oe_ul}",
            )
        else:
            oe_n_assets = st.radio(
                "Basket Size",
                [2, 3],
                horizontal=True,
                key="oe_n",
                format_func=lambda x: f"{x} Underliers",
            )
            oa1, oa2 = st.columns(2)
            with oa1:
                oe_t1 = st.selectbox("Asset 1", UNDERLIERS, index=0, key="oe_t1")
            with oa2:
                oe_s1 = st.number_input(
                    "Spot 1",
                    value=float(DEFAULT_SPOTS[oe_t1]),
                    min_value=1.0,
                    step=0.01,
                    format="%.2f",
                    key=f"oe_s1_{oe_t1}",
                )
            ob1, ob2 = st.columns(2)
            with ob1:
                oe_t2 = st.selectbox("Asset 2", UNDERLIERS, index=1, key="oe_t2")
            with ob2:
                oe_s2 = st.number_input(
                    "Spot 2",
                    value=float(DEFAULT_SPOTS[oe_t2]),
                    min_value=1.0,
                    step=0.01,
                    format="%.2f",
                    key=f"oe_s2_{oe_t2}",
                )
            oe_t3 = oe_s3 = None
            if oe_n_assets == 3:
                oc1, oc2 = st.columns(2)
                with oc1:
                    oe_t3 = st.selectbox("Asset 3", UNDERLIERS, index=2, key="oe_t3")
                with oc2:
                    oe_s3 = st.number_input(
                        "Spot 3",
                        value=float(DEFAULT_SPOTS[oe_t3]),
                        min_value=1.0,
                        step=0.01,
                        format="%.2f",
                        key=f"oe_s3_{oe_t3}",
                    )
            oe_rho12 = st.slider("ρ (1/2)", -0.99, 0.99, 0.55, step=0.01, key="oe_r12")
            oe_rho13 = oe_rho23 = 0.0
            if oe_n_assets == 3:
                oe_rho13 = st.slider(
                    "ρ (1/3)", -0.99, 0.99, 0.50, step=0.01, key="oe_r13"
                )
                oe_rho23 = st.slider(
                    "ρ (2/3)", -0.99, 0.99, 0.50, step=0.01, key="oe_r23"
                )

        st.markdown("<hr>", unsafe_allow_html=True)
        _label("Schedule")
        od1, od2 = st.columns(2)
        with od1:
            oe_issue = st.date_input(
                "Issue Date", value=date(2026, 6, 3), key="oe_issue"
            )
        with od2:
            oe_mat = st.date_input(
                "Maturity Date", value=date(2027, 12, 3), key="oe_mat"
            )

        oe_freq = st.selectbox(
            "Observation Frequency",
            ["Quarterly", "Monthly", "Semi-Annual"],
            key="oe_freq",
        )

    # ── Column B: Barriers, rates & offer price ──────────────────────────
    with col_ob:
        oe_face = st.number_input(
            "Face Value ($)", value=1000.0, step=100.0, key="oe_face"
        )

        _label("Barrier Structure")
        oe_autocall = st.slider(
            "Autocall Barrier", 80, 115, 100, step=5, format="%d%%", key="oe_autocall"
        )
        oe_coupon = st.slider(
            "Coupon Barrier", 50, 95, 75, step=5, format="%d%%", key="oe_coupon"
        )
        oe_knockin = st.slider(
            "Knock-In Barrier", 40, 80, 65, step=5, format="%d%%", key="oe_knockin"
        )

        st.markdown("<hr>", unsafe_allow_html=True)
        _label("Rates")

        oe1, oe2 = st.columns(2)
        with oe1:
            oe_cpn = st.number_input("Coupon (%)", value=12.0, step=0.5, key="oe_cpn")
        with oe2:
            oe_rfr = st.number_input("RFR (%)", value=3.75, step=0.25, key="oe_rfr")

        oe3, oe4 = st.columns(2)
        with oe3:
            oe_cs = st.number_input(
                "Credit Spread (bps)",
                value=100,
                step=5,
                min_value=0,
                max_value=500,
                key="oe_cs",
            )
        with oe4:
            oe_paths = st.select_slider(
                "MC Paths",
                options=[10_000, 50_000, 100_000],
                value=50_000,
                format_func=lambda x: f"{x:,}",
                key="oe_npaths",
            )

        st.markdown("<hr>", unsafe_allow_html=True)
        _label("Offer Price")
        oe_offer = st.number_input(
            "Issuer Offer (% of Face)",
            min_value=50.0,
            max_value=110.0,
            value=100.0,
            step=0.1,
            key="oe_offer",
            help="New issuances are almost always at par (100%). Use secondary price for seasoned notes.",
        )

        oe_btn = st.button(
            "Evaluate Offering", type="primary", use_container_width=True, key="oe_btn"
        )

    # ── Column C: Evaluation result ──────────────────────────────────────
    with col_oout:
        st.markdown('<div class="results-panel">', unsafe_allow_html=True)
        _label("Evaluation")

        if oe_btn:
            if oe_type == "Single Underlier":
                oe_note = _build_note_dict(
                    oe_ul,
                    oe_sp,
                    oe_face,
                    oe_issue,
                    oe_mat,
                    oe_freq,
                    oe_autocall,
                    oe_coupon,
                    oe_knockin,
                    oe_cpn,
                    oe_rfr,
                    credit_spread_bps=oe_cs,
                )
            else:
                if oe_n_assets == 2:
                    oe_tickers = [oe_t1, oe_t2]
                    oe_spots = [oe_s1, oe_s2]
                    oe_corr = [[1.0, oe_rho12], [oe_rho12, 1.0]]
                else:
                    oe_tickers = [oe_t1, oe_t2, oe_t3]
                    oe_spots = [oe_s1, oe_s2, oe_s3]
                    oe_corr = [
                        [1.0, oe_rho12, oe_rho13],
                        [oe_rho12, 1.0, oe_rho23],
                        [oe_rho13, oe_rho23, 1.0],
                    ]
                oe_note = _build_wo_note_dict(
                    oe_tickers,
                    oe_spots,
                    oe_corr,
                    oe_face,
                    oe_issue,
                    oe_mat,
                    oe_freq,
                    oe_autocall,
                    oe_coupon,
                    oe_knockin,
                    oe_cpn,
                    oe_rfr,
                    credit_spread_bps=oe_cs,
                )

            if not oe_note["observation_dates"]:
                st.error(
                    "No observation dates — check Maturity Date is after Issue Date."
                )
            else:
                with st.spinner(f"Evaluating · {oe_paths:,} paths …"):
                    try:
                        from pricer.offering import evaluate_offering

                        oe_result = evaluate_offering(
                            oe_note, offer_pct=oe_offer, n_paths=oe_paths
                        )
                        st.session_state["oe_result"] = oe_result
                    except Exception as e:
                        st.error(f"Evaluation failed: {e}")
                        st.session_state.pop("oe_result", None)

        if "oe_result" in st.session_state:
            oe_r = st.session_state["oe_result"]
            rec = oe_r["recommendation"]
            dev = oe_r["deviation_bps"]
            se = oe_r["se_bps"]

            st.markdown(
                f"<div style='background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;"
                f"padding:1rem 1.25rem;margin-bottom:0.75rem;'>"
                f"<p class='section-label'>Model Recommendation</p>"
                f"{_recommendation_badge(rec)}"
                f"<p style='margin:0.6rem 0 0;font-size:0.85rem;color:#374151;'>"
                f"Confidence: <strong>{oe_r['confidence']}</strong> — deviation ({dev:+.0f} bps) "
                f"{'exceeds' if oe_r['confidence'] == 'High' else 'is within'} "
                f"the 2σ MC noise band (±{se*2:.0f} bps).</p></div>",
                unsafe_allow_html=True,
            )

            om1, om2, om3 = st.columns(3)
            om1.metric(
                "Model Fair Value",
                f"{oe_r['model_fv']:.2f}%",
                delta=f"{oe_r['deviation_pct']:+.2f}% vs offer",
            )
            om2.metric("Issuer Offer", f"{oe_r['offer_pct']:.2f}%")
            om3.metric("Deviation", f"{dev:+.0f} bps")

            om4, om5 = st.columns(2)
            om4.metric("Model FV ($)", f"${oe_r['model_dollar']:,.2f}")
            om5.metric("MC Std Error", f"±{se:.1f} bps")

            st.markdown("<hr>", unsafe_allow_html=True)
            st.caption(
                f"**Buy** if deviation > +150 bps  ·  **Skip** if < −150 bps  ·  "
                f"**Gray Zone** within ±150 bps.  Current: {dev:+.0f} bps → **{rec}**."
            )
        else:
            st.info(
                "Enter the term sheet in the two columns on the left, "
                "set the issuer's offer price, and click **Evaluate Offering**."
            )

        st.markdown("</div>", unsafe_allow_html=True)
