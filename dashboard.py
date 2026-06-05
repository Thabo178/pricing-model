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
# Page config + custom CSS (formal white theme)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Structured Note Pricer | Ryan Hysmith",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* ── Global typography & background ── */
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', sans-serif;
    background-color: #ffffff;
    color: #1a1a2e;
}

/* ── App header ── */
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1280px;
}

/* ── Tab bar ── */
[data-baseweb="tab-list"] {
    border-bottom: 2px solid #e2e8f0;
    gap: 0;
}
[data-baseweb="tab"] {
    font-size: 0.875rem;
    font-weight: 500;
    color: #64748b;
    padding: 0.65rem 1.25rem;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: #1e3a5f;
    border-bottom-color: #1e3a5f;
    font-weight: 600;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 1rem 1.25rem;
}
[data-testid="stMetricLabel"] {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #64748b;
}
[data-testid="stMetricValue"] {
    font-size: 1.5rem;
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
}
[kind="primary"] button:hover {
    background-color: #2d5282 !important;
}

/* ── Section dividers ── */
hr {
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 1.25rem 0;
}

/* ── Dataframe / table ── */
[data-testid="stDataFrame"] {
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
}

/* ── Subheaders ── */
h2, h3 {
    color: #1e3a5f;
    font-weight: 700;
    letter-spacing: -0.01em;
}

/* ── Caption text ── */
small, [data-testid="stCaptionContainer"] {
    color: #64748b;
    font-size: 0.8rem;
}

/* ── Input labels ── */
[data-testid="stWidgetLabel"] p {
    font-size: 0.8125rem;
    font-weight: 500;
    color: #374151;
}

/* ── Info / warning boxes ── */
[data-testid="stAlert"] {
    border-radius: 8px;
}

/* ── Expanders ── */
[data-testid="stExpander"] summary {
    font-weight: 600;
    color: #1e3a5f;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

UNDERLIERS = [
    "NVDA", "TSLA", "AMD", "META", "GOOGL",
    "AMZN", "HOOD", "LULU", "NOW", "PLTR", "WFC", "SPY",
]

DEFAULT_SPOTS = {
    "NVDA": 219.16, "TSLA": 180.0, "AMD":  160.0, "META": 510.0,
    "GOOGL": 175.0, "AMZN": 190.0, "HOOD":  22.0, "LULU":  85.0,
    "NOW":  820.0,  "PLTR":  25.0, "WFC":   57.0, "SPY":  525.0,
}


def _add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year  = d.year + month // 12
    month = month % 12 + 1
    day   = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _generate_obs_dates(issue: date, maturity: date, freq: str) -> list:
    step = {"Monthly": 1, "Quarterly": 3, "Semi-Annual": 6}[freq]
    dates, cur = [], _add_months(issue, step)
    while cur <= maturity:
        dates.append(cur.strftime("%Y-%m-%d"))
        cur = _add_months(cur, step)
    return dates


def _build_note_dict(
    underlier, spot, face_value, issue_date, maturity_date,
    obs_freq, autocall_pct, coupon_pct, knockin_pct, coupon_rate, rfr,
    credit_spread_bps=0,
) -> dict:
    note = {
        "underlier":         underlier,
        "spot":              spot,
        "face_value":        face_value,
        "issue_date":        issue_date.strftime("%Y-%m-%d"),
        "maturity_date":     maturity_date.strftime("%Y-%m-%d"),
        "observation_dates": _generate_obs_dates(issue_date, maturity_date, obs_freq),
        "autocall_barrier":  autocall_pct / 100,
        "coupon_barrier":    coupon_pct   / 100,
        "knockin_barrier":   knockin_pct  / 100,
        "coupon_rate":       coupon_rate  / 100,
        "risk_free_rate":    rfr          / 100,
    }
    if credit_spread_bps:
        note["credit_spread"] = credit_spread_bps / 10000
    return note


def _build_wo_note_dict(
    tickers, spots, corr_matrix,
    face_value, issue_date, maturity_date,
    obs_freq, autocall_pct, coupon_pct, knockin_pct, coupon_rate, rfr,
    credit_spread_bps=0,
) -> dict:
    note = {
        "underliers":         tickers,
        "spots":              spots,
        "correlation_matrix": corr_matrix,
        "face_value":         face_value,
        "issue_date":         issue_date.strftime("%Y-%m-%d"),
        "maturity_date":      maturity_date.strftime("%Y-%m-%d"),
        "observation_dates":  _generate_obs_dates(issue_date, maturity_date, obs_freq),
        "autocall_barrier":   autocall_pct / 100,
        "coupon_barrier":     coupon_pct   / 100,
        "knockin_barrier":    knockin_pct  / 100,
        "coupon_rate":        coupon_rate  / 100,
        "risk_free_rate":     rfr          / 100,
    }
    if credit_spread_bps:
        note["credit_spread"] = credit_spread_bps / 10000
    return note


def _recommendation_badge(rec: str) -> str:
    colour = {"Buy": "#16a34a", "Skip": "#dc2626", "Gray Zone": "#d97706"}.get(rec, "#64748b")
    return (
        f'<span style="background:{colour};color:#fff;padding:4px 12px;'
        f'border-radius:4px;font-weight:700;font-size:0.9rem;">{rec}</span>'
    )


def _flag_colour(flag: str) -> str:
    return {"OK": "#16a34a", "Review": "#d97706", "Flag ⚠": "#dc2626",
            "N/A": "#64748b", "ERROR": "#dc2626"}.get(flag, "#64748b")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

col_hdr, col_logo = st.columns([4, 1])
with col_hdr:
    st.markdown(
        "<h1 style='color:#1e3a5f;margin-bottom:0;font-size:1.75rem;"
        "font-weight:800;letter-spacing:-0.02em;'>"
        "Structured Note Pricer</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#64748b;margin-top:0.2rem;font-size:0.875rem;'>"
        "Phoenix Autocallable &nbsp;·&nbsp; Single-Asset &amp; Worst-Of Basket &nbsp;·&nbsp; "
        "Heston Stochastic Volatility &nbsp;·&nbsp; ORATS Live Data</p>",
        unsafe_allow_html=True,
    )

st.markdown("<hr style='margin:0.5rem 0 1.5rem;'>", unsafe_allow_html=True)

tab_price, tab_vol, tab_cal, tab_wo, tab_port, tab_offer = st.tabs([
    "Note Pricer",
    "Vol Surface",
    "Calibration",
    "Worst-Of Pricer",
    "Portfolio",
    "Offering Evaluator",
])

# ===========================================================================
# TAB 1 — NOTE PRICER  (single underlier)
# ===========================================================================

with tab_price:
    col_in, col_out = st.columns([1, 1.6])

    with col_in:
        st.markdown("#### Term Sheet")

        underlier  = st.selectbox("Underlier", UNDERLIERS, key="p_underlier")
        spot       = st.number_input(
            "Spot Price ($)", min_value=1.0,
            value=DEFAULT_SPOTS.get(underlier, 100.0),
            step=0.01, format="%.2f", key=f"p_spot_{underlier}",
        )
        face_value = st.number_input("Face Value ($)", min_value=100.0,
                                     value=1000.0, step=100.0, key="p_face")

        st.divider()

        issue_date    = st.date_input("Issue Date",    value=date(2026, 6, 3),  key="p_issue")
        maturity_date = st.date_input("Maturity Date", value=date(2027, 12, 3), key="p_mat")
        obs_freq      = st.selectbox("Observation Frequency",
                                     ["Quarterly", "Monthly", "Semi-Annual"], key="p_freq")

        st.divider()
        st.markdown("#### Barrier Structure")

        autocall_pct = st.slider("Autocall Barrier", 80, 115, 100, step=5, format="%d%%", key="p_autocall")
        coupon_pct   = st.slider("Coupon Barrier",   50,  95,  75, step=5, format="%d%%", key="p_coupon")
        knockin_pct  = st.slider("Knock-In Barrier", 40,  80,  65, step=5, format="%d%%", key="p_knockin")

        st.divider()
        st.markdown("#### Rates & Model")

        coupon_rate        = st.number_input("Annual Coupon (%)", min_value=0.0,
                                              max_value=50.0, value=12.0, step=0.5, key="p_cpn")
        rfr                = st.number_input("Risk-Free Rate (%)", min_value=0.0,
                                              max_value=20.0, value=3.75, step=0.25, key="p_rfr")
        credit_spread_bps  = st.number_input(
            "Issuer Credit Spread (bps)",
            min_value=0, max_value=500, value=0, step=5,
            help="§6.1 — Treasury + CDS spread. Adds to discount rate. "
                 "Typical A-rated issuer: 50–150 bps. Fair value drops by ~100–300 bps.",
            key="p_cs",
        )
        memory_on = st.checkbox("Memory Coupon Feature", value=False, key="p_memory",
                                help="Unpaid coupons from periods below the barrier accrue and "
                                     "are paid in full at the next qualifying observation.")
        n_paths   = st.select_slider(
            "Monte Carlo Paths",
            options=[10_000, 50_000, 100_000],
            value=50_000,
            format_func=lambda x: f"{x:,}",
            key="p_npaths",
        )

        price_btn = st.button("Run Pricing", type="primary",
                              use_container_width=True, key="p_btn")

    with col_out:
        st.markdown("#### Results")

        if price_btn:
            note_dict = _build_note_dict(
                underlier, spot, face_value, issue_date, maturity_date,
                obs_freq, autocall_pct, coupon_pct, knockin_pct, coupon_rate, rfr,
                credit_spread_bps=credit_spread_bps,
            )
            note_dict['memory'] = memory_on
            if not note_dict["observation_dates"]:
                st.error("No observation dates — check that Maturity Date is after Issue Date.")
            else:
                with st.spinner(f"Pricing {underlier} · {n_paths:,} paths …"):
                    try:
                        from pricer.pricer import price_note_dict
                        result = price_note_dict(note_dict, n_paths=n_paths, memory=memory_on)
                        st.session_state["last_result"] = result
                        st.session_state["last_note"]   = note_dict
                    except Exception as e:
                        st.error(f"Pricing failed: {e}")
                        st.session_state.pop("last_result", None)

        if "last_result" in st.session_state:
            r = st.session_state["last_result"]
            n = st.session_state["last_note"]

            m1, m2, m3 = st.columns(3)
            m1.metric("Fair Value (% of Face)", f"{r['npv_pct']:.2f}%")
            m2.metric("Fair Value per $1,000",  f"${r['npv_dollar']:,.2f}")
            m3.metric("MC Std Error", f"±{r['se_bps']:.1f} bps",
                      help="1σ standard error. 2σ band = ±" +
                           f"{r['se_bps']*2:.1f} bps. Target: < 30 bps for production.")

            if credit_spread_bps:
                st.info(
                    f"Credit spread of {credit_spread_bps} bps applied to discount curve. "
                    "Fair value reflects funding advantage embedded in issuer pricing.",
                    icon="ℹ️",
                )

            st.divider()

            # ── Greeks ──────────────────────────────────────────────────────
            with st.expander("Greeks (bump-and-reprice · §6.3)", expanded=False):
                g_paths = st.select_slider(
                    "Paths for Greeks",
                    options=[10_000, 20_000, 30_000],
                    value=20_000,
                    format_func=lambda x: f"{x:,}",
                    key="p_g_paths",
                )
                greeks_btn = st.button("Compute Greeks", key="p_greeks_btn")
                if greeks_btn:
                    with st.spinner("Computing Greeks (5 reprice calls) …"):
                        try:
                            from pricer.greeks import compute_greeks
                            g = compute_greeks(n, n_paths=g_paths)
                            st.session_state["last_greeks"] = g
                        except Exception as e:
                            st.error(f"Greeks failed: {e}")

                if "last_greeks" in st.session_state:
                    g = st.session_state["last_greeks"]
                    gc1, gc2, gc3, gc4 = st.columns(4)
                    gc1.metric("Delta (% face / 1% spot)",
                               f"{g['delta_pct']:+.3f}%",
                               help="Change in fair value (% of face) per 1% move in spot.")
                    gc2.metric("Delta ($ / $1 spot)",
                               f"${g['delta_dollar']:+.4f}",
                               help="Dollar sensitivity per $1 move in the underlying.")
                    gc3.metric("Vega (% face / 1 vol pt)",
                               f"{g['vega_pct']:+.3f}%",
                               help="Change in fair value per 1 percentage-point (0.01) "
                                    "move in annualised vol.")
                    gc4.metric("Theta ($ / day)",
                               f"${g['theta_dollar']:+.4f}",
                               help="Change in dollar fair value per calendar day. "
                                    "Typically negative (time decay).")
                    st.caption(
                        f"Gamma: ${g['gamma_dollar']:+.6f} per $1² spot move  ·  "
                        "All Greeks computed via ±1% central-difference bump-and-reprice."
                    )

            st.divider()
            st.markdown("##### Term Sheet Summary")

            obs = n["observation_dates"]
            cs  = n.get("credit_spread", 0)
            summary = {
                "Underlier":          n["underlier"],
                "Spot":               f"${n['spot']:,.2f}",
                "Face Value":         f"${n['face_value']:,.0f}",
                "Issue Date":         n["issue_date"],
                "Maturity Date":      n["maturity_date"],
                "Observation Dates":  f"{len(obs)} dates  ({obs[0]} → {obs[-1]})",
                "Autocall Barrier":   f"{n['autocall_barrier']*100:.0f}% of spot",
                "Coupon Barrier":     f"{n['coupon_barrier']*100:.0f}% of spot",
                "Knock-In Barrier":   f"{n['knockin_barrier']*100:.0f}% of spot",
                "Annual Coupon":      f"{n['coupon_rate']*100:.2f}%",
                "Risk-Free Rate":     f"{n['risk_free_rate']*100:.3f}%",
                "Credit Spread":      f"{cs*10000:.0f} bps" if cs else "None",
                "Memory Coupon":      "Yes" if n.get('memory') else "No",
                "MC Paths":           f"{r['n_paths']:,}",
            }
            st.dataframe(
                pd.DataFrame.from_dict(summary, orient="index", columns=["Value"]),
                use_container_width=True,
            )

        else:
            st.info("Configure the term sheet on the left and click **Run Pricing**.")

# ===========================================================================
# TAB 2 — VOL SURFACE
# ===========================================================================

with tab_vol:
    st.markdown("#### ORATS Live Vol Surface")

    col_v1, col_v2 = st.columns([0.28, 0.72])

    with col_v1:
        vol_ticker = st.selectbox("Ticker", UNDERLIERS, key="v_ticker")
        fetch_btn  = st.button("Fetch from ORATS", type="primary",
                               key="v_fetch", use_container_width=True)

    with col_v2:
        if fetch_btn:
            with st.spinner(f"Fetching {vol_ticker} from ORATS …"):
                try:
                    from pricer.orats import get_monies_implied, get_smv_summary
                    st.session_state["vol_mono"]   = get_monies_implied(vol_ticker)
                    st.session_state["vol_smv"]    = get_smv_summary(vol_ticker)
                    st.session_state["vol_ticker"] = vol_ticker
                except Exception as e:
                    st.error(f"ORATS fetch failed: {e}")

        if st.session_state.get("vol_ticker") == vol_ticker and "vol_mono" in st.session_state:
            df  = st.session_state["vol_mono"]
            smv = st.session_state["vol_smv"]

            if not smv.empty:
                row = smv.iloc[0]
                s1, s2, s3, s4 = st.columns(4)
                s1.metric("Spot",       f"${float(row.get('stockPrice', 0)):,.2f}")
                s2.metric("30d ATM IV", f"{float(row.get('iv30d', 0))*100:.1f}%")
                s3.metric("Skew (30d)", f"{float(row.get('rSlp30', 0)):.3f}")
                s4.metric("Implied Move", f"{float(row.get('impliedMove', 0))*100:.1f}%")

            st.divider()

            want = ["expirDate", "atmiv", "slope", "vol25", "vol50", "vol75", "vol5"]
            show = [c for c in want if c in df.columns]
            disp = df[show].copy()
            disp.rename(columns={
                "expirDate": "Expiry", "atmiv": "ATM IV", "slope": "Skew",
                "vol25": "25Δ IV",    "vol50": "50Δ IV",  "vol75": "75Δ IV",
                "vol5":  "5Δ IV",
            }, inplace=True)
            for col in ["ATM IV", "25Δ IV", "50Δ IV", "75Δ IV", "5Δ IV"]:
                if col in disp.columns:
                    disp[col] = (disp[col].astype(float) * 100).round(2).astype(str) + "%"

            st.dataframe(disp, use_container_width=True, hide_index=True)

            if "expirDate" in df.columns and "atmiv" in df.columns:
                chart_df = df[["expirDate", "atmiv"]].copy()
                chart_df["ATM IV (%)"] = chart_df["atmiv"].astype(float) * 100
                chart_df = chart_df.set_index("expirDate")[["ATM IV (%)"]]
                st.line_chart(chart_df, use_container_width=True)
                st.caption("ATM Implied Volatility (%) by Expiry — source: ORATS /monies/implied")

        else:
            st.info("Select a ticker and click **Fetch from ORATS** to load the live vol surface.")

# ===========================================================================
# TAB 3 — CALIBRATION
# ===========================================================================

with tab_cal:
    st.markdown("#### Heston Parameter Calibration")

    col_c1, col_c2 = st.columns([0.35, 0.65])

    with col_c1:
        cal_ticker = st.selectbox("Ticker", UNDERLIERS, key="c_ticker")
        cal_spot   = st.number_input(
            "Spot ($)", value=float(DEFAULT_SPOTS.get(cal_ticker, 100.0)),
            min_value=1.0, step=1.0, key=f"c_spot_{cal_ticker}",
        )
        cal_rfr   = st.number_input("Risk-Free Rate (%)", value=3.75, step=0.25, key="c_rfr")
        use_orats = st.checkbox("Use live ORATS surface", value=True, key="c_orats")
        if not use_orats:
            st.caption("Mock mode: calibrates to a synthetic surface. RMSE will be ~0.")
        cal_btn = st.button("Run Calibration", type="primary",
                            use_container_width=True, key="c_btn")

        st.divider()
        st.caption(
            "Calibration uses Differential Evolution (global) followed by "
            "L-BFGS-B refinement (§8.1). Bounds: κ [0.5,8] · θ [0.01,0.5] · "
            "σ [0.1,2.5] · ρ [−0.95,−0.1] · v₀ [0.01,0.6]."
        )

    with col_c2:
        if cal_btn:
            source = "ORATS" if use_orats else "mock surface"
            with st.spinner(f"Calibrating {cal_ticker} via {source} …"):
                try:
                    import QuantLib as ql
                    today = ql.Date.todaysDate()
                    rfr   = cal_rfr / 100.0

                    if use_orats:
                        from pricer.orats import build_calibration_set, live_spot
                        from pricer.calibration import calibrate_heston_orats, save_calibrated
                        try:
                            spot = live_spot(cal_ticker)
                        except Exception:
                            spot = cal_spot
                        cal_set = build_calibration_set(cal_ticker, today, spot, r=rfr)
                        if not cal_set:
                            st.error(f"No ORATS surface data available for {cal_ticker}.")
                        else:
                            result = calibrate_heston_orats(cal_ticker, today, spot, rfr, cal_set)
                            save_calibrated(result)
                            st.session_state["cal_result"]    = result
                            st.session_state["cal_live_spot"] = spot
                    else:
                        from pricer.calibration import (
                            generate_mock_surface, calibrate_heston, save_calibrated,
                        )
                        surface = generate_mock_surface(cal_ticker, cal_spot, rfr, today=today)
                        result  = calibrate_heston(cal_ticker, cal_spot, rfr, surface, today=today)
                        save_calibrated(result)
                        st.session_state["cal_result"] = result
                        st.session_state.pop("cal_live_spot", None)

                except Exception as e:
                    st.error(f"Calibration failed: {e}")

        if "cal_result" in st.session_state:
            r = st.session_state["cal_result"]

            live_s = st.session_state.get("cal_live_spot")
            if live_s:
                st.caption(f"Live spot from ORATS: **${live_s:,.2f}**")

            feller_ok = r.get("feller_satisfied", True)
            if not feller_ok:
                st.warning(
                    f"Feller condition violated: 2κθ = {2*r['kappa']*r['theta']:.4f} "
                    f"< σ² = {r['sigma']**2:.4f}. Variance may approach zero. "
                    "Full-truncation MC handles this numerically — result is still valid. (§8.2)",
                    icon="⚠️",
                )

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Status",    "Converged" if r["converged"] else "Did Not Converge")
            m2.metric("RMSE",      f"{r['rmse']:.6f}")
            m3.metric("IV Points", str(r["n_points"]))
            m4.metric("Feller",    "Satisfied" if feller_ok else "Violated")

            st.divider()
            st.markdown("##### Calibrated Parameters")

            params = {
                "v₀  (initial variance)":         f"{r['v0']:.6f}",
                "κ   (mean-reversion speed)":      f"{r['kappa']:.6f}",
                "θ   (long-run variance)":         f"{r['theta']:.6f}",
                "σ   (vol of vol)":                f"{r['sigma']:.6f}",
                "ρ   (asset / variance corr.)":    f"{r['rho']:.6f}",
            }
            st.dataframe(
                pd.DataFrame.from_dict(params, orient="index", columns=["Value"]),
                use_container_width=True,
            )
            st.caption(
                f"Calibrated to {r['n_points']} surface points  ·  "
                f"Saved → data/calibrated/{r['underlier']}.json"
            )

        else:
            st.info("Select a ticker and click **Run Calibration** to fit Heston parameters.")

# ===========================================================================
# TAB 4 — WORST-OF PRICER
# ===========================================================================

with tab_wo:
    st.markdown("#### Worst-Of Basket Pricer")
    st.caption(
        "Phoenix autocallable on a 2- or 3-underlier basket. "
        "All barrier checks apply to the worst-performing stock at each observation date."
    )

    col_wo_in, col_wo_out = st.columns([1, 1.6])

    with col_wo_in:
        n_assets = st.radio(
            "Basket Size", [2, 3], horizontal=True, key="wo_n",
            format_func=lambda x: f"{x} Underliers",
        )

        st.markdown("#### Basket Components")

        wo_t1 = st.selectbox("Underlier 1", UNDERLIERS, index=0, key="wo_t1")
        wo_s1 = st.number_input(
            "Spot 1 ($)", value=float(DEFAULT_SPOTS[wo_t1]),
            min_value=1.0, step=0.01, format="%.2f", key=f"wo_s1_{wo_t1}",
        )

        wo_t2 = st.selectbox("Underlier 2", UNDERLIERS, index=1, key="wo_t2")
        wo_s2 = st.number_input(
            "Spot 2 ($)", value=float(DEFAULT_SPOTS[wo_t2]),
            min_value=1.0, step=0.01, format="%.2f", key=f"wo_s2_{wo_t2}",
        )

        wo_t3, wo_s3 = None, None
        if n_assets == 3:
            wo_t3 = st.selectbox("Underlier 3", UNDERLIERS, index=2, key="wo_t3")
            wo_s3 = st.number_input(
                "Spot 3 ($)", value=float(DEFAULT_SPOTS[wo_t3]),
                min_value=1.0, step=0.01, format="%.2f", key=f"wo_s3_{wo_t3}",
            )

        st.divider()
        st.markdown("#### Pairwise Correlations")

        rho_12 = st.slider(
            f"ρ  ({wo_t1} / {wo_t2})",
            min_value=-0.99, max_value=0.99, value=0.55, step=0.01, key="wo_r12",
        )
        rho_13, rho_23 = 0.0, 0.0
        if n_assets == 3:
            rho_13 = st.slider(
                f"ρ  ({wo_t1} / {wo_t3})",
                min_value=-0.99, max_value=0.99, value=0.50, step=0.01, key="wo_r13",
            )
            rho_23 = st.slider(
                f"ρ  ({wo_t2} / {wo_t3})",
                min_value=-0.99, max_value=0.99, value=0.50, step=0.01, key="wo_r23",
            )
            st.caption("Correlation matrix is projected to PSD before simulation.")

        st.divider()
        st.markdown("#### Note Parameters")

        wo_face  = st.number_input("Face Value ($)", min_value=100.0, value=1000.0,
                                    step=100.0, key="wo_face")
        wo_issue = st.date_input("Issue Date",    value=date(2026, 6, 3),  key="wo_issue")
        wo_mat   = st.date_input("Maturity Date", value=date(2027, 12, 3), key="wo_mat")
        wo_freq  = st.selectbox("Observation Frequency",
                                 ["Quarterly", "Monthly", "Semi-Annual"], key="wo_freq")

        st.divider()

        wo_autocall = st.slider("Autocall Barrier", 80, 115, 100, step=5, format="%d%%", key="wo_autocall")
        wo_coupon   = st.slider("Coupon Barrier",   50,  95,  75, step=5, format="%d%%", key="wo_coupon")
        wo_knockin  = st.slider("Knock-In Barrier", 40,  80,  65, step=5, format="%d%%", key="wo_knockin")

        st.divider()

        wo_cpn  = st.number_input("Annual Coupon (%)", min_value=0.0,
                                   max_value=50.0, value=12.0, step=0.5, key="wo_cpn")
        wo_rfr  = st.number_input("Risk-Free Rate (%)", min_value=0.0,
                                   max_value=20.0, value=3.75, step=0.25, key="wo_rfr")
        wo_cs   = st.number_input(
            "Issuer Credit Spread (bps)", min_value=0, max_value=500, value=0,
            step=5, key="wo_cs",
            help="§6.1 — Adds to discount rate. Fair value drops by ~100–300 bps.",
        )
        wo_paths = st.select_slider(
            "Monte Carlo Paths",
            options=[10_000, 50_000, 100_000],
            value=50_000,
            format_func=lambda x: f"{x:,}",
            key="wo_npaths",
        )

        wo_btn = st.button("Price Worst-Of", type="primary",
                           use_container_width=True, key="wo_btn")

    with col_wo_out:
        st.markdown("#### Results")

        if wo_btn:
            if n_assets == 2:
                tickers = [wo_t1, wo_t2]
                spots   = [wo_s1, wo_s2]
                corr    = [[1.0, rho_12], [rho_12, 1.0]]
            else:
                tickers = [wo_t1, wo_t2, wo_t3]
                spots   = [wo_s1, wo_s2, wo_s3]
                corr    = [
                    [1.0,    rho_12, rho_13],
                    [rho_12, 1.0,    rho_23],
                    [rho_13, rho_23, 1.0   ],
                ]

            wo_note = _build_wo_note_dict(
                tickers, spots, corr, wo_face, wo_issue, wo_mat,
                wo_freq, wo_autocall, wo_coupon, wo_knockin, wo_cpn, wo_rfr,
                credit_spread_bps=wo_cs,
            )

            if not wo_note["observation_dates"]:
                st.error("No observation dates — check that Maturity Date is after Issue Date.")
            else:
                basket_label = " / ".join(tickers)
                with st.spinner(
                    f"Pricing {basket_label} worst-of · {wo_paths:,} paths …"
                ):
                    try:
                        from pricer.pricer import price_worst_of, price_note_dict

                        wo_result = price_worst_of(wo_note, n_paths=wo_paths)

                        singles = []
                        base = {k: v for k, v in wo_note.items()
                                if k not in ("underliers", "spots", "correlation_matrix")}
                        for ticker, s in zip(tickers, spots):
                            sn = {**base, "underlier": ticker, "spot": s}
                            singles.append(price_note_dict(sn, n_paths=wo_paths))

                        st.session_state["wo_result"]  = wo_result
                        st.session_state["wo_note"]    = wo_note
                        st.session_state["wo_singles"] = singles

                    except Exception as e:
                        st.error(f"Pricing failed: {e}")
                        st.session_state.pop("wo_result", None)

        if "wo_result" in st.session_state:
            wo_r    = st.session_state["wo_result"]
            wo_n    = st.session_state["wo_note"]
            singles = st.session_state["wo_singles"]

            m1, m2, m3 = st.columns(3)
            m1.metric("Worst-Of Fair Value",         f"{wo_r['npv_pct']:.2f}%")
            m2.metric(f"Per ${wo_r['face_value']:,.0f} Face", f"${wo_r['npv_dollar']:,.2f}")
            m3.metric("MC Std Error",                f"±{wo_r['se_bps']:.1f} bps")

            st.divider()
            st.markdown("##### Single vs. Worst-Of Comparison")

            comp_rows = []
            for s in singles:
                comp_rows.append({
                    "Structure":  f"{s['underlier']} (single-underlier)",
                    "Fair Value":  f"{s['npv_pct']:.2f}%",
                    "Dollar FV":  f"${s['npv_dollar']:,.2f}",
                })
            comp_rows.append({
                "Structure": f"Worst-Of Basket  ({' / '.join(wo_n['underliers'])})",
                "Fair Value": f"{wo_r['npv_pct']:.2f}%",
                "Dollar FV":  f"${wo_r['npv_dollar']:,.2f}",
            })

            st.dataframe(
                pd.DataFrame(comp_rows),
                use_container_width=True,
                hide_index=True,
            )

            best_single_npv = min(s["npv_pct"] for s in singles)
            discount = best_single_npv - wo_r["npv_pct"]
            st.caption(
                f"Worst-of discount vs best single-underlier: **{discount:.2f}%** — "
                "the additional risk the investor bears in exchange for a higher coupon."
            )

            st.divider()
            st.markdown("##### Correlation Matrix")
            corr_df = pd.DataFrame(
                wo_n["correlation_matrix"],
                index=wo_n["underliers"],
                columns=wo_n["underliers"],
            )
            st.dataframe(corr_df.style.format("{:.2f}"), use_container_width=True)

            st.divider()
            st.markdown("##### Term Sheet Summary")
            obs = wo_n["observation_dates"]
            cs  = wo_n.get("credit_spread", 0)
            summary = {
                "Basket":             " / ".join(wo_n["underliers"]),
                "Spots":              "  ·  ".join(f"${s:,.2f}" for s in wo_n["spots"]),
                "Face Value":         f"${wo_n['face_value']:,.0f}",
                "Issue Date":         wo_n["issue_date"],
                "Maturity Date":      wo_n["maturity_date"],
                "Observation Dates":  f"{len(obs)} dates  ({obs[0]} → {obs[-1]})",
                "Autocall Barrier":   f"{wo_n['autocall_barrier']*100:.0f}% of each spot",
                "Coupon Barrier":     f"{wo_n['coupon_barrier']*100:.0f}% of each spot",
                "Knock-In Barrier":   f"{wo_n['knockin_barrier']*100:.0f}% of each spot",
                "Annual Coupon":      f"{wo_n['coupon_rate']*100:.2f}%",
                "Risk-Free Rate":     f"{wo_n['risk_free_rate']*100:.3f}%",
                "Credit Spread":      f"{cs*10000:.0f} bps" if cs else "None",
                "MC Paths":           f"{wo_r['n_paths']:,}",
            }
            st.dataframe(
                pd.DataFrame.from_dict(summary, orient="index", columns=["Value"]),
                use_container_width=True,
            )

        else:
            st.info(
                "Configure the basket and note parameters on the left, "
                "then click **Price Worst-Of**."
            )

# ===========================================================================
# TAB 5 — PORTFOLIO  (§10 — mark-to-model vs issuer marks)
# ===========================================================================

with tab_port:
    st.markdown("#### Portfolio Mark-to-Model")
    st.caption(
        "Prices every note in data/portfolio.json against the model and compares to issuer marks.  "
        "Thresholds (§10):  |dev| ≤ 100 bps = Within Model Noise  ·  ≤ 300 bps = Review  ·  "
        "> 300 bps = Flag"
    )

    PORTFOLIO_PATH = Path(__file__).parent / "data" / "portfolio.json"

    col_po1, col_po2 = st.columns([0.28, 0.72])

    with col_po1:
        port_paths = st.select_slider(
            "MC Paths per Note",
            options=[5_000, 10_000, 30_000, 50_000],
            value=10_000,
            format_func=lambda x: f"{x:,}",
            key="po_npaths",
        )
        port_btn = st.button("Run Portfolio Pricing", type="primary",
                             use_container_width=True, key="po_btn")

        if PORTFOLIO_PATH.exists():
            try:
                import json as _json
                _pdata = _json.loads(PORTFOLIO_PATH.read_text())
                _n = len([_note for _note in _pdata.get('notes', [])
                          if not _note.get('_comment')])
                st.caption(f"Portfolio: **{_n} notes** loaded from data/portfolio.json")
            except Exception:
                pass
        else:
            st.warning("data/portfolio.json not found.")

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
            ok_rows = [r for r in rows if 'error' not in r]

            if ok_rows:
                total_face = sum(r['face_value'] for r in ok_rows)
                avg_model  = sum(r['model_fv'] * r['face_value'] for r in ok_rows) / total_face
                flagged    = sum(1 for r in ok_rows if r['flag'] not in ('OK', 'N/A'))
                total_pnl  = sum(r['pnl_vs_purchase'] or 0 for r in ok_rows)

                sm1, sm2, sm3, sm4 = st.columns(4)
                sm1.metric("Notes Priced",           str(len(ok_rows)))
                sm2.metric("Wtd Avg Model FV",        f"{avg_model:.2f}%")
                sm3.metric("Review / Flag",           str(flagged))
                sm4.metric("Total P&L vs Purchase",   f"${total_pnl:+,.0f}")

                st.divider()

            table_rows = []
            for r in rows:
                if 'error' in r:
                    table_rows.append({
                        "CUSIP": r['cusip'], "Issuer": r['issuer'],
                        "Structure": "ERROR", "Underlier(s)": r['underliers'],
                        "Issuer Mark": "—", "Model FV": "—",
                        "Dev (bps)": "—", "SE (bps)": "—", "Flag": "ERROR",
                    })
                else:
                    dev_str = (f"{r['deviation_bps']:+.0f}" if r['deviation_bps'] is not None
                               else "—")
                    table_rows.append({
                        "CUSIP":        r['cusip'],
                        "Issuer":       r['issuer'],
                        "Structure":    r['structure'],
                        "Underlier(s)": r['underliers'],
                        "Issuer Mark":  f"{r['issuer_mark']:.2f}%" if r['issuer_mark'] else "—",
                        "Model FV":     f"{r['model_fv']:.2f}%",
                        "Dev (bps)":    dev_str,
                        "SE (bps)":     f"±{r.get('se_bps', 0):.1f}",
                        "Flag":         r['flag'],
                    })

            st.dataframe(
                pd.DataFrame(table_rows),
                use_container_width=True,
                hide_index=True,
            )
            st.caption(
                "Deviation = (Model FV − Issuer Mark) × 100.  "
                "Positive = model prices the note richer than the issuer.  "
                "SE = Monte Carlo standard error (1σ)."
            )

        else:
            st.info(
                "Click **Run Portfolio Pricing** to price all notes in data/portfolio.json "
                "and compare against issuer marks."
            )

# ===========================================================================
# TAB 6 — OFFERING EVALUATOR  (§6.4)
# ===========================================================================

with tab_offer:
    st.markdown("#### New Offering Evaluator")
    st.caption(
        "Enter the term sheet for a note being offered in the primary market. "
        "The model prices it independently and compares to the issuer's offer price. "
        "Buy signal: model FV > offer + 1.5%  ·  Skip: model FV < offer − 1.5%  ·  Gray Zone: within 1.5% (§6.4)"
    )

    col_oe_in, col_oe_out = st.columns([1, 1.6])

    with col_oe_in:
        oe_type = st.radio("Structure", ["Single Underlier", "Worst-Of Basket"],
                           horizontal=True, key="oe_type")

        st.markdown("#### Term Sheet")

        if oe_type == "Single Underlier":
            oe_ul  = st.selectbox("Underlier", UNDERLIERS, key="oe_ul")
            oe_sp  = st.number_input("Spot ($)", value=float(DEFAULT_SPOTS[oe_ul]),
                                     min_value=1.0, step=0.01, format="%.2f",
                                     key=f"oe_sp_{oe_ul}")
        else:
            oe_n_assets = st.radio("Basket Size", [2, 3], horizontal=True, key="oe_n",
                                   format_func=lambda x: f"{x} Underliers")
            oe_t1 = st.selectbox("Underlier 1", UNDERLIERS, index=0, key="oe_t1")
            oe_s1 = st.number_input("Spot 1 ($)", value=float(DEFAULT_SPOTS[oe_t1]),
                                     min_value=1.0, step=0.01, format="%.2f",
                                     key=f"oe_s1_{oe_t1}")
            oe_t2 = st.selectbox("Underlier 2", UNDERLIERS, index=1, key="oe_t2")
            oe_s2 = st.number_input("Spot 2 ($)", value=float(DEFAULT_SPOTS[oe_t2]),
                                     min_value=1.0, step=0.01, format="%.2f",
                                     key=f"oe_s2_{oe_t2}")
            oe_t3, oe_s3 = None, None
            if oe_n_assets == 3:
                oe_t3 = st.selectbox("Underlier 3", UNDERLIERS, index=2, key="oe_t3")
                oe_s3 = st.number_input("Spot 3 ($)", value=float(DEFAULT_SPOTS[oe_t3]),
                                         min_value=1.0, step=0.01, format="%.2f",
                                         key=f"oe_s3_{oe_t3}")
            oe_rho12 = st.slider("ρ (Asset 1 / 2)", -0.99, 0.99, 0.55, step=0.01, key="oe_r12")
            oe_rho13 = oe_rho23 = 0.0
            if oe_n_assets == 3:
                oe_rho13 = st.slider("ρ (Asset 1 / 3)", -0.99, 0.99, 0.50, step=0.01, key="oe_r13")
                oe_rho23 = st.slider("ρ (Asset 2 / 3)", -0.99, 0.99, 0.50, step=0.01, key="oe_r23")

        st.divider()

        oe_face  = st.number_input("Face Value ($)", value=1000.0, step=100.0, key="oe_face")
        oe_issue = st.date_input("Issue Date",    value=date(2026, 6, 3),  key="oe_issue")
        oe_mat   = st.date_input("Maturity Date", value=date(2027, 12, 3), key="oe_mat")
        oe_freq  = st.selectbox("Observation Frequency",
                                 ["Quarterly", "Monthly", "Semi-Annual"], key="oe_freq")

        st.divider()

        oe_autocall = st.slider("Autocall Barrier", 80, 115, 100, step=5, format="%d%%", key="oe_autocall")
        oe_coupon   = st.slider("Coupon Barrier",   50,  95,  75, step=5, format="%d%%", key="oe_coupon")
        oe_knockin  = st.slider("Knock-In Barrier", 40,  80,  65, step=5, format="%d%%", key="oe_knockin")

        st.divider()

        oe_cpn    = st.number_input("Annual Coupon (%)", value=12.0, step=0.5, key="oe_cpn")
        oe_rfr    = st.number_input("Risk-Free Rate (%)", value=3.75, step=0.25, key="oe_rfr")
        oe_cs     = st.number_input("Credit Spread (bps)", value=100, step=5,
                                     min_value=0, max_value=500, key="oe_cs",
                                     help="Issuer credit spread. 100 bps is typical for A-rated bank issuers.")
        oe_offer  = st.number_input(
            "Issuer Offer Price (% of Face)",
            min_value=50.0, max_value=110.0, value=100.0, step=0.1,
            key="oe_offer",
            help="New issuances are almost always offered at par (100%). "
                 "Use actual secondary price for seasoned notes.",
        )
        oe_paths  = st.select_slider(
            "Monte Carlo Paths",
            options=[10_000, 50_000, 100_000],
            value=50_000,
            format_func=lambda x: f"{x:,}",
            key="oe_npaths",
        )

        oe_btn = st.button("Evaluate Offering", type="primary",
                           use_container_width=True, key="oe_btn")

    with col_oe_out:
        st.markdown("#### Evaluation Results")

        if oe_btn:
            # Build the note dict
            if oe_type == "Single Underlier":
                oe_note = _build_note_dict(
                    oe_ul, oe_sp, oe_face, oe_issue, oe_mat,
                    oe_freq, oe_autocall, oe_coupon, oe_knockin, oe_cpn, oe_rfr,
                    credit_spread_bps=oe_cs,
                )
            else:
                if oe_n_assets == 2:
                    oe_tickers = [oe_t1, oe_t2]; oe_spots = [oe_s1, oe_s2]
                    oe_corr = [[1.0, oe_rho12], [oe_rho12, 1.0]]
                else:
                    oe_tickers = [oe_t1, oe_t2, oe_t3]
                    oe_spots   = [oe_s1, oe_s2, oe_s3]
                    oe_corr    = [
                        [1.0,       oe_rho12, oe_rho13],
                        [oe_rho12,  1.0,      oe_rho23],
                        [oe_rho13,  oe_rho23, 1.0     ],
                    ]
                oe_note = _build_wo_note_dict(
                    oe_tickers, oe_spots, oe_corr, oe_face, oe_issue, oe_mat,
                    oe_freq, oe_autocall, oe_coupon, oe_knockin, oe_cpn, oe_rfr,
                    credit_spread_bps=oe_cs,
                )

            if not oe_note["observation_dates"]:
                st.error("No observation dates — check Maturity Date is after Issue Date.")
            else:
                with st.spinner(f"Evaluating offering · {oe_paths:,} paths …"):
                    try:
                        from pricer.offering import evaluate_offering
                        oe_result = evaluate_offering(oe_note, offer_pct=oe_offer,
                                                      n_paths=oe_paths)
                        st.session_state["oe_result"] = oe_result
                    except Exception as e:
                        st.error(f"Evaluation failed: {e}")
                        st.session_state.pop("oe_result", None)

        if "oe_result" in st.session_state:
            oe_r = st.session_state["oe_result"]

            # ── Recommendation banner ──
            rec   = oe_r['recommendation']
            conf  = oe_r['confidence']
            dev   = oe_r['deviation_bps']
            se    = oe_r['se_bps']

            st.markdown(
                f"<div style='background:#f8fafc;border:1px solid #e2e8f0;"
                f"border-radius:8px;padding:1.25rem 1.5rem;margin-bottom:1rem;'>"
                f"<p style='margin:0 0 0.5rem;font-size:0.75rem;font-weight:600;"
                f"text-transform:uppercase;letter-spacing:0.06em;color:#64748b;'>"
                f"Model Recommendation</p>"
                f"{_recommendation_badge(rec)}"
                f"<p style='margin:0.75rem 0 0;font-size:0.875rem;color:#374151;'>"
                f"Confidence: <strong>{conf}</strong> — deviation ({dev:+.0f} bps) "
                f"{'is distinguishable from' if conf == 'High' else 'is within'} "
                f"MC noise band (±{se*2:.0f} bps, 2σ).</p>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # ── Key metrics ──
            m1, m2, m3 = st.columns(3)
            m1.metric("Model Fair Value",  f"{oe_r['model_fv']:.2f}%",
                      delta=f"{oe_r['deviation_pct']:+.2f}% vs offer")
            m2.metric("Issuer Offer",      f"{oe_r['offer_pct']:.2f}%")
            m3.metric("Deviation",
                      f"{dev:+.0f} bps",
                      help="+ve = model prices it richer than issuer (note is cheap to buy).")

            m4, m5 = st.columns(2)
            m4.metric("Model FV ($)",     f"${oe_r['model_dollar']:,.2f}")
            m5.metric("MC Std Error",     f"±{se:.1f} bps")

            st.divider()
            st.markdown("##### Interpretation")
            st.markdown(
                f"The model prices this note at **{oe_r['model_fv']:.2f}%** of face, "
                f"versus the issuer's offer of **{oe_r['offer_pct']:.2f}%** of face. "
                f"This is a deviation of **{dev:+.0f} bps** ({oe_r['deviation_pct']:+.3f}%).\n\n"
                f"- **Buy** if deviation > +150 bps (note is cheap vs model). "
                f"Currently: {'+' if dev > 150 else ''}{'✓ Buy threshold met' if dev > 150 else '✗ Below Buy threshold'}.\n"
                f"- **Skip** if deviation < −150 bps (note is expensive vs model). "
                f"Currently: {'✓ Skip threshold met' if dev < -150 else '✗ Above Skip threshold'}.\n"
                f"- **Gray Zone** ({abs(dev):.0f} bps deviation within the ±150 bps band): "
                f"{'within noise — no strong signal.' if rec == 'Gray Zone' else 'outside band — signal present.'}"
            )

            if oe_cs > 0:
                st.info(
                    f"Credit spread of {oe_cs} bps applied to discount curve (§6.1). "
                    "Without the credit adjustment, fair value would be approximately "
                    f"{oe_r['model_fv'] + oe_cs * len(oe_note.get('observation_dates', [])) / 100 * 0.05:.2f}% "
                    "(rough estimate — re-run with credit_spread=0 for exact comparison).",
                    icon="ℹ️",
                )

        else:
            st.info(
                "Enter the offering's term sheet on the left and click "
                "**Evaluate Offering** to get a model-based buy/skip recommendation."
            )
