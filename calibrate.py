"""
Calibrate Heston parameters for one or all of the 12 underliers.

Usage:
    python calibrate.py              # calibrate all 12 using live ORATS data
    python calibrate.py NVDA         # calibrate a single name (live)
    python calibrate.py NVDA TSLA    # calibrate multiple names (live)
    python calibrate.py --mock       # calibrate all using synthetic surface (no API)
    python calibrate.py NVDA --mock  # single name, synthetic surface

For each name this script:
  Live mode  — fetches the current vol surface from ORATS, converts delta → strike,
               calibrates with QuantLib LevenbergMarquardt, saves JSON.
  Mock mode  — builds a synthetic surface from the default Heston params and
               calibrates with scipy L-BFGS-B (zero RMSE — correctness test only).

The pricer automatically picks up calibrated files the next time it runs.
"""
import sys
import time
import numpy as np
import QuantLib as ql

from pricer.calibration import (
    generate_mock_surface, calibrate_heston,
    calibrate_heston_orats, save_calibrated,
)
from pricer.orats import build_calibration_set, live_spot

# Fallback spots — used only when ORATS is unavailable.
# Live mode fetches the real spot from ORATS automatically.
UNDERLIERS = {
    'NVDA':  219.16,
    'TSLA':  180.00,
    'AMD':   160.00,
    'META':  510.00,
    'GOOGL': 175.00,
    'AMZN':  190.00,
    'HOOD':   22.00,
    'LULU':   85.00,
    'NOW':   820.00,
    'PLTR':   25.00,
    'WFC':    57.00,
    'SPY':   525.00,
}

RISK_FREE_RATE = 0.0375
TODAY = ql.Date.todaysDate()


# ---------------------------------------------------------------------------
# Live calibration — real ORATS surface + QuantLib LevenbergMarquardt
# ---------------------------------------------------------------------------

def calibrate_name_live(ticker: str, fallback_spot: float) -> dict | None:
    t0 = time.time()

    # Fetch live spot from ORATS; fall back to hardcoded approximation
    try:
        spot = live_spot(ticker)
    except Exception:
        spot = fallback_spot

    cal_set = build_calibration_set(ticker, TODAY, spot, r=RISK_FREE_RATE)

    if not cal_set:
        print(f"  {ticker:<6} !! No ORATS surface data — skipping")
        return None

    result = calibrate_heston_orats(ticker, TODAY, spot, RISK_FREE_RATE, cal_set)
    save_calibrated(result)
    elapsed = time.time() - t0

    status  = 'OK' if result['converged'] else '~~'
    feller  = '✓' if result.get('feller_satisfied', True) else '✗ Feller'
    print(
        f"  {ticker:<6} {status}  "
        f"v0={result['v0']:.4f}  kappa={result['kappa']:.3f}  "
        f"theta={result['theta']:.4f}  sigma={result['sigma']:.3f}  "
        f"rho={result['rho']:.3f}  "
        f"rmse={result['rmse']:.5f}  ({elapsed:.1f}s)  "
        f"[{result['n_points']} pts]  Feller:{feller}"
    )
    return result


# ---------------------------------------------------------------------------
# Mock calibration — synthetic surface + scipy L-BFGS-B (correctness test)
# ---------------------------------------------------------------------------

def calibrate_name_mock(ticker: str, spot: float) -> dict:
    t0 = time.time()
    surface = generate_mock_surface(ticker, spot, RISK_FREE_RATE, today=TODAY)
    result  = calibrate_heston(ticker, spot, RISK_FREE_RATE, surface, today=TODAY)
    save_calibrated(result)
    elapsed = time.time() - t0

    status = 'OK' if result['converged'] else '~~'
    print(
        f"  {ticker:<6} {status}  "
        f"v0={result['v0']:.4f}  kappa={result['kappa']:.3f}  "
        f"theta={result['theta']:.4f}  sigma={result['sigma']:.3f}  "
        f"rho={result['rho']:.3f}  "
        f"rmse={result['rmse']:.5f}  ({elapsed:.1f}s)"
    )
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    raw_args  = [a for a in sys.argv[1:]]
    use_mock  = '--mock' in raw_args or '--MOCK' in raw_args
    tickers   = [a.upper() for a in raw_args if not a.startswith('--')]

    if not tickers:
        tickers = list(UNDERLIERS)

    unknown = [n for n in tickers if n not in UNDERLIERS]
    if unknown:
        print(f"Unknown tickers: {unknown}")
        print(f"Valid options: {list(UNDERLIERS)}")
        sys.exit(1)

    mode = 'synthetic surface (mock)' if use_mock else 'live ORATS surface'
    print(f"\nCalibrating {len(tickers)} underlier(s) [{mode}] ...")
    print(f"  {'Ticker':<6}  {'v0':>7}  {'kappa':>6}  {'theta':>7}  {'sigma':>6}  {'rho':>6}  {'rmse':>9}")
    print(f"  {'-'*68}")

    calibrate_fn = calibrate_name_mock if use_mock else calibrate_name_live

    for ticker in tickers:
        calibrate_fn(ticker, UNDERLIERS[ticker])

    print(f"\nCalibrated parameters saved to data/calibrated/")
