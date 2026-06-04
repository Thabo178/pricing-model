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
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Structured Note Pricer",
    layout="wide",
    initial_sidebar_state="collapsed",
)

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
) -> dict:
    return {
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


def _build_wo_note_dict(
    tickers, spots, corr_matrix,
    face_value, issue_date, maturity_date,
    obs_freq, autocall_pct, coupon_pct, knockin_pct, coupon_rate, rfr,
) -> dict:
    return {
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


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("Structured Note Pricer")
st.caption(
    "Phoenix Autocallable · Single-Underlier & Worst-Of Basket · "
    "Heston Stochastic Vol · ORATS Live Data"
)

tab_price, tab_vol, tab_cal, tab_wo, tab_port = st.tabs(
    ["Note Pricer", "Vol Surface", "Calibration", "Worst-Of Pricer", "Portfolio"]
)

# ===========================================================================
# TAB 1 — NOTE PRICER  (single underlier)
# ===========================================================================

with tab_price:
    col_in, col_out = st.columns([1, 1.5])

    with col_in:
        st.subheader("Term Sheet")

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

        autocall_pct = st.slider("Autocall Barrier", 80, 115, 100, step=5, format="%d%%", key="p_autocall")
        coupon_pct   = st.slider("Coupon Barrier",   50,  95,  75, step=5, format="%d%%", key="p_coupon")
        knockin_pct  = st.slider("Knock-In Barrier", 40,  80,  65, step=5, format="%d%%", key="p_knockin")

        st.divider()

        coupon_rate = st.number_input("Annual Coupon Rate (%)", min_value=0.0,
                                      max_value=50.0, value=12.0, step=0.5, key="p_cpn")
        rfr         = st.number_input("Risk-Free Rate (%)", min_value=0.0,
                                      max_value=20.0, value=3.75, step=0.25, key="p_rfr")
        n_paths     = st.select_slider(
            "Monte Carlo Paths",
            options=[10_000, 50_000, 100_000],
            value=50_000,
            format_func=lambda x: f"{x:,}",
            key="p_npaths",
        )

        price_btn = st.button("Price Note", type="primary",
                              use_container_width=True, key="p_btn")

    with col_out:
        st.subheader("Results")

        if price_btn:
            note_dict = _build_note_dict(
                underlier, spot, face_value, issue_date, maturity_date,
                obs_freq, autocall_pct, coupon_pct, knockin_pct, coupon_rate, rfr,
            )
            if not note_dict["observation_dates"]:
                st.error("No observation dates — check that Maturity Date is after Issue Date.")
            else:
                with st.spinner(f"Pricing {underlier} · {n_paths:,} paths …"):
                    try:
                        from pricer.pricer import price_note_dict
                        result = price_note_dict(note_dict, n_paths=n_paths)
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
                      help="Monte Carlo standard error (1σ). 2σ confidence band = ±" +
                           f"{r['se_bps']*2:.1f} bps. Target: < 30 bps for production.")

            st.divider()
            st.caption("Term Sheet Summary")

            obs = n["observation_dates"]
            summary = {
                "Underlier":         n["underlier"],
                "Spot":              f"${n['spot']:,.2f}",
                "Face Value":        f"${n['face_value']:,.0f}",
                "Issue Date":        n["issue_date"],
                "Maturity Date":     n["maturity_date"],
                "Observation Dates": f"{len(obs)} dates  ({obs[0]} → {obs[-1]})",
                "Autocall Barrier":  f"{n['autocall_barrier']*100:.0f}% of spot",
                "Coupon Barrier":    f"{n['coupon_barrier']*100:.0f}% of spot",
                "Knock-In Barrier":  f"{n['knockin_barrier']*100:.0f}% of spot",
                "Annual Coupon":     f"{n['coupon_rate']*100:.2f}%",
                "Risk-Free Rate":    f"{n['risk_free_rate']*100:.3f}%",
                "MC Paths":          f"{r['n_paths']:,}",
            }
            st.table(pd.DataFrame.from_dict(summary, orient="index", columns=["Value"]))

        else:
            st.info("Set the parameters on the left and click **Price Note** to run the pricer.")

# ===========================================================================
# TAB 2 — VOL SURFACE
# ===========================================================================

with tab_vol:
    st.subheader("ORATS Live Vol Surface")

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
                s4.metric("Impl. Move", f"{float(row.get('impliedMove', 0))*100:.1f}%")

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
                st.caption("ATM Implied Volatility (%) by Expiry")

        else:
            st.info("Select a ticker and click **Fetch from ORATS** to load the live vol surface.")

# ===========================================================================
# TAB 3 — CALIBRATION
# ===========================================================================

with tab_cal:
    st.subheader("Heston Calibration")

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
        cal_btn = st.button("Calibrate", type="primary",
                            use_container_width=True, key="c_btn")

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
                st.caption(f"Live spot fetched from ORATS: **${live_s:,.2f}**")

            feller_ok = r.get("feller_satisfied", True)
            if not feller_ok:
                st.warning(
                    f"Feller condition violated: 2κθ = {2*r['kappa']*r['theta']:.4f} "
                    f"< σ² = {r['sigma']**2:.4f}. Variance may reach zero. "
                    "Full-truncation MC handles this numerically — result is still valid.",
                    icon="⚠️",
                )

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Status",    "Converged ✓" if r["converged"] else "Did not converge")
            m2.metric("RMSE",      f"{r['rmse']:.6f}")
            m3.metric("IV Points", str(r["n_points"]))
            m4.metric("Feller",    "✓ OK" if feller_ok else "✗ Violated")

            st.divider()

            params = {
                "v₀  — initial variance":       f"{r['v0']:.6f}",
                "κ   — mean-reversion speed":    f"{r['kappa']:.6f}",
                "θ   — long-run variance":       f"{r['theta']:.6f}",
                "σ   — vol of vol":              f"{r['sigma']:.6f}",
                "ρ   — stock / vol correlation": f"{r['rho']:.6f}",
            }
            st.table(pd.DataFrame.from_dict(params, orient="index", columns=["Value"]))
            st.caption(
                f"Calibrated to {r['n_points']} surface points  ·  "
                f"Saved → data/calibrated/{r['underlier']}.json"
            )

        else:
            st.info("Select a ticker and click **Calibrate** to fit the Heston parameters.")

# ===========================================================================
# TAB 4 — WORST-OF PRICER
# ===========================================================================

with tab_wo:
    st.subheader("Worst-Of Pricer")
    st.caption(
        "Phoenix autocallable on 2 or 3 underliers. "
        "All barrier checks (autocall, coupon, knock-in) apply to the worst-performing "
        "stock at each observation date."
    )

    col_wo_in, col_wo_out = st.columns([1, 1.5])

    with col_wo_in:

        n_assets = st.radio(
            "Basket Size", [2, 3], horizontal=True, key="wo_n",
            format_func=lambda x: f"{x} Underliers",
        )

        st.subheader("Basket")

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
        st.subheader("Correlations")

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
            st.caption("Correlation matrix is automatically projected to PSD before simulation.")

        st.divider()
        st.subheader("Note Parameters")

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

        wo_cpn   = st.number_input("Annual Coupon Rate (%)", min_value=0.0,
                                    max_value=50.0, value=12.0, step=0.5, key="wo_cpn")
        wo_rfr   = st.number_input("Risk-Free Rate (%)", min_value=0.0,
                                    max_value=20.0, value=3.75, step=0.25, key="wo_rfr")
        wo_paths = st.select_slider(
            "Monte Carlo Paths",
            options=[10_000, 50_000, 100_000],
            value=50_000,
            format_func=lambda x: f"{x:,}",
            key="wo_npaths",
        )

        wo_btn = st.button("Price Worst-Of", type="primary",
                           use_container_width=True, key="wo_btn")

    # ---- results column ----
    with col_wo_out:
        st.subheader("Results")

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
            )

            if not wo_note["observation_dates"]:
                st.error("No observation dates — check that Maturity Date is after Issue Date.")
            else:
                basket_label = " / ".join(tickers)
                with st.spinner(
                    f"Pricing {basket_label} worst-of · {wo_paths:,} paths "
                    f"(+ {n_assets} single-underlier runs for comparison) …"
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
            m1.metric("Worst-Of Fair Value",     f"{wo_r['npv_pct']:.2f}%")
            m2.metric(f"Per ${wo_r['face_value']:,.0f} Face", f"${wo_r['npv_dollar']:,.2f}")
            m3.metric("MC Std Error",            f"±{wo_r['se_bps']:.1f} bps")

            st.divider()
            st.caption("Single-Underlier vs Worst-Of Comparison")

            comp_rows = []
            for s in singles:
                comp_rows.append({
                    "Structure":  f"{s['underlier']} (single)",
                    "NPV %":      f"{s['npv_pct']:.2f}%",
                    "NPV $":      f"${s['npv_dollar']:,.2f}",
                })
            comp_rows.append({
                "Structure": f"Worst-Of Basket ({' / '.join(wo_n['underliers'])})",
                "NPV %":     f"{wo_r['npv_pct']:.2f}%",
                "NPV $":     f"${wo_r['npv_dollar']:,.2f}",
            })

            st.dataframe(
                pd.DataFrame(comp_rows),
                use_container_width=True,
                hide_index=True,
            )

            best_single_npv = min(s["npv_pct"] for s in singles)
            discount = best_single_npv - wo_r["npv_pct"]
            st.caption(
                f"Worst-of discount vs best single-underlier: **{discount:.2f}%**  —  "
                "the additional risk Ryan takes on in exchange for a higher coupon."
            )

            st.divider()
            st.caption("Correlation Matrix")

            corr_df = pd.DataFrame(
                wo_n["correlation_matrix"],
                index=wo_n["underliers"],
                columns=wo_n["underliers"],
            )
            st.dataframe(corr_df.style.format("{:.2f}"), use_container_width=True)

            st.divider()
            st.caption("Term Sheet Summary")

            obs = wo_n["observation_dates"]
            summary = {
                "Basket":            " / ".join(wo_n["underliers"]),
                "Spots":             "  /  ".join(f"${s:,.2f}" for s in wo_n["spots"]),
                "Face Value":        f"${wo_n['face_value']:,.0f}",
                "Issue Date":        wo_n["issue_date"],
                "Maturity Date":     wo_n["maturity_date"],
                "Observation Dates": f"{len(obs)} dates  ({obs[0]} → {obs[-1]})",
                "Autocall Barrier":  f"{wo_n['autocall_barrier']*100:.0f}% of each spot",
                "Coupon Barrier":    f"{wo_n['coupon_barrier']*100:.0f}% of each spot",
                "Knock-In Barrier":  f"{wo_n['knockin_barrier']*100:.0f}% of each spot",
                "Annual Coupon":     f"{wo_n['coupon_rate']*100:.2f}%",
                "Risk-Free Rate":    f"{wo_n['risk_free_rate']*100:.3f}%",
                "MC Paths":          f"{wo_r['n_paths']:,}",
            }
            st.table(pd.DataFrame.from_dict(summary, orient="index", columns=["Value"]))

        else:
            st.info(
                "Configure the basket and note parameters on the left, "
                "then click **Price Worst-Of**."
            )

# ===========================================================================
# TAB 5 — PORTFOLIO  (§10 — mark-to-model vs issuer marks)
# ===========================================================================

with tab_port:
    st.subheader("Portfolio Mark-to-Model")
    st.caption(
        "Prices every note in data/portfolio.json against the model and flags "
        "deviations from issuer marks.  |dev| ≤ 100 bps = OK · ≤ 300 bps = Review · "
        "> 300 bps = Flag ⚠  (§10)"
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
                _n = len([n for n in _pdata.get('notes', []) if not n.get('_comment')])
                st.caption(f"Portfolio file: **{_n} notes**")
            except Exception:
                pass
        else:
            st.warning("data/portfolio.json not found. Create it to use this tab.")

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
                # — Summary metrics —
                total_face   = sum(r['face_value'] for r in ok_rows)
                avg_model    = sum(r['model_fv'] * r['face_value'] for r in ok_rows) / total_face
                flagged      = sum(1 for r in ok_rows if r['flag'] not in ('OK', 'N/A'))
                total_pnl    = sum(r['pnl_vs_purchase'] or 0 for r in ok_rows)

                sm1, sm2, sm3, sm4 = st.columns(4)
                sm1.metric("Notes Priced",        str(len(ok_rows)))
                sm2.metric("Wtd Avg Model FV",    f"{avg_model:.2f}%")
                sm3.metric("Flagged / Review",    str(flagged))
                sm4.metric("Total P&L vs Purchase", f"${total_pnl:+,.0f}")

                st.divider()

            # — Deviation table —
            table_rows = []
            for r in rows:
                if 'error' in r:
                    table_rows.append({
                        "CUSIP": r['cusip'], "Issuer": r['issuer'],
                        "Structure": "ERROR", "Underlier(s)": r['underliers'],
                        "Issuer Mark": "—", "Model FV": "—",
                        "Dev (bps)": "—", "SE (bps)": "—", "Flag": "ERROR ✗",
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
                "Positive deviation means model prices the note richer than the issuer.  "
                "SE = Monte Carlo standard error (1σ)."
            )

        else:
            st.info(
                "Click **Run Portfolio Pricing** to price all notes in data/portfolio.json "
                "and compare against issuer marks."
            )
