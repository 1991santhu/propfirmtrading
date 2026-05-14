"""
Payout funnel analysis: shows the full eval → funded → payout sequence
and compares RR vs win rate for payout maximization.

Usage:
    python -m backtest.payout_funnel backtest/data/MNQ_5min.csv
    python -m backtest.payout_funnel backtest/data/MNQ_5min.csv --month 2026-04
"""
import argparse
from itertools import product

import pandas as pd

from backtest.signals import load_csv, add_key_levels, add_ema_clouds, filter_rth
from backtest.simulator import simulate_trades, DayStats
from backtest.prop_firm import simulate_lucid_flex
from backtest.strategies import ALL_STRATEGIES


def _get_strategy(prefix: str):
    for s in ALL_STRATEGIES:
        if s.name.startswith(prefix):
            return s
    raise ValueError(f"No strategy starting with {prefix!r}")


def print_funnel(label: str, rr: float, be_buf: int, trades, day_stats: list[DayStats]) -> dict:
    pf = simulate_lucid_flex(day_stats)

    total_days   = len(day_stats)
    green_days   = sum(1 for d in day_stats if d.pnl > 0)
    qual_days    = sum(1 for d in day_stats if d.pnl >= 150)
    avg_daily    = sum(d.pnl for d in day_stats) / total_days if total_days else 0

    total_trades = len(trades)
    tp_exits     = [t for t in trades if t.exit_reason == "tp"]
    be_exits     = [t for t in trades if t.exit_reason == "be_stop"]
    wins         = [t for t in trades if t.pnl > 0]
    win_pct      = len(wins) / total_trades * 100 if total_trades else 0

    print(f"\n{'─'*68}")
    print(f"  {label}  |  RR={rr}  BE-buffer={be_buf}pts")
    print(f"{'─'*68}")
    print(f"  Period: {day_stats[0].date} → {day_stats[-1].date}  ({total_days} trading days)")
    print(f"  Trades: {total_trades}  |  Win%: {win_pct:.1f}%  "
          f"(TP: {len(tp_exits)/total_trades*100:.1f}%  BE: {len(be_exits)/total_trades*100:.1f}%)")
    print(f"  Days — Green: {green_days}/{total_days}  "
          f"Qualifying(≥$150): {qual_days}/{total_days}  "
          f"Avg daily P&L: ${avg_daily:,.0f}")

    print(f"\n  EVAL PHASE  ({len(pf.evals)} attempts, $150/ea = ${len(pf.evals)*150:,} spent)")
    print(f"  {'#':<4} {'Days':>5} {'Profit':>9} {'Result':<20}")
    for e in pf.evals:
        result = "PASSED ✓" if e.passed else f"BLOWN — {e.fail_reason}"
        print(f"  {e.eval_number:<4} {e.days_traded:>5} ${e.profit:>8,.0f}  {result}")

    passed = sum(1 for e in pf.evals if e.passed)
    blown  = sum(1 for e in pf.evals if not e.passed and e.fail_reason == "drawdown")
    print(f"\n  → Passed: {passed}  |  Blown: {blown}  |  "
          f"Pass rate: {passed/len(pf.evals)*100:.0f}%  "
          f"(at 30% pass rate assumption: ~${150/0.3:.0f} avg cost per funded account)")

    print(f"\n  FUNDED PHASE  ({len(pf.funded)} funded accounts reached)")
    for f_ in pf.funded:
        status = "BLOWN" if f_.blown else "still active"
        print(f"  Funded #{f_.funded_number}: {f_.days_traded} days traded  |  "
              f"Qual days: {f_.qualifying_days}  |  "
              f"Payout cycles: {f_.payout_cycles}  |  "
              f"Total P&L: ${f_.total_profit:,.0f}  |  {status}")

    print(f"\n  PAYOUTS  ({len(pf.payouts)} total, capped at $2k each)")
    if pf.payouts:
        for p in pf.payouts:
            print(f"  Payout #{p.payout_number}: gross=${p.gross_profit:,.0f}  "
                  f"→ you receive ${p.payout_amount:,.0f}")
    else:
        print("  None triggered.")

    print(f"\n  SUMMARY")
    print(f"  Total payouts:  ${pf.total_payouts:>8,.0f}")
    print(f"  Eval fees paid: ${pf.total_eval_fees:>8,.0f}")
    print(f"  Net profit:     ${pf.net_profit:>8,.0f}")

    return {
        "rr": rr, "be_buf": be_buf,
        "win_pct": round(win_pct, 1),
        "qual_days": qual_days,
        "total_days": total_days,
        "qual_rate": round(qual_days / total_days * 100, 1),
        "evals": len(pf.evals),
        "passed": passed,
        "blown": blown,
        "payout_cycles": sum(f_.payout_cycles for f_ in pf.funded),
        "payouts": round(pf.total_payouts),
        "fees": round(pf.total_eval_fees),
        "net": round(pf.net_profit),
    }


def run_funnel(csv_path: str, month: str | None = None) -> None:
    df_raw = load_csv(csv_path)
    df_raw = add_key_levels(df_raw)
    df_raw = add_ema_clouds(df_raw)
    df_rth = filter_rth(df_raw)

    if month:
        df_rth = df_rth[df_rth.index.to_period("M") == month]
        period_label = month
    else:
        period_label = f"{df_rth.index[0].date()} → {df_rth.index[-1].date()}"

    strategy_g = _get_strategy("G:")
    df_sig = strategy_g.generate_signals(df_rth, reentry=False)

    print(f"\n{'='*68}")
    print(f"  PAYOUT FUNNEL ANALYSIS — Strategy G: Breakout + Retest")
    print(f"  Period: {period_label}")
    print(f"  LucidFlex 50k: $3k eval target | $2k drawdown | 5 qual-days → payout")
    print(f"  5 contracts | 60pt stop | $2/pt/contract")
    print(f"{'='*68}")

    combos = [
        (2.0, 0,  "2R  / exact BE (current default)"),
        (1.5, 0,  "1.5R / exact BE"),
        (1.5, 10, "1.5R / BE+10pt buffer"),
        (1.0, 0,  "1R  / exact BE (max win rate)"),
    ]

    rows = []
    for rr, be_buf, label in combos:
        trades, day_stats = simulate_trades(
            df_sig,
            contracts=5, stop_points=60,
            rr_ratio=rr, be_buffer_points=be_buf,
            max_daily_losses=2, max_daily_trades=5,
        )
        if not trades:
            print(f"\n  {label}: no trades.")
            continue
        row = print_funnel(label, rr, be_buf, trades, day_stats)
        rows.append(row)

    # Comparison table
    print(f"\n\n{'='*68}")
    print(f"  COMPARISON — What actually drives payouts?")
    print(f"{'='*68}")
    print(f"  {'Setting':<22} {'Win%':>5} {'QualDays':>9} {'Qual%':>6} "
          f"{'Cycles':>7} {'Payouts':>9} {'Fees':>6} {'Net':>8}")
    print(f"  {'-'*68}")
    for r in rows:
        label = f"{r['rr']}R + BE{r['be_buf']}pt"
        print(
            f"  {label:<22} {r['win_pct']:>5}% {r['qual_days']:>4}/{r['total_days']:<4} "
            f"{r['qual_rate']:>5}% "
            f"{r['payout_cycles']:>7} ${r['payouts']:>8,} ${r['fees']:>5,} ${r['net']:>7,}"
        )

    print(f"\n  KEY INSIGHT FOR LUCID FLEX PAYOUTS:")
    print(f"  • Payout cap = $2,000/cycle → you never benefit from raw P&L above $2,222")
    print(f"  • What matters most: # of qualifying days (≥$150) to trigger the 5-day threshold")
    print(f"  • More qualifying days = more payout cycles = more $2k chunks")
    print(f"  • High win rate gets you to 5 qual-days FASTER on funded account")
    print(f"  • But lower R:R = smaller per-trade profit = risk of not hitting $150/day threshold")
    print(f"  • Sweet spot: 1.5R gives enough per-trade profit for most wins to be ≥$150")
    print(f"    while dramatically improving qualifying day frequency vs 2R")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--month", default=None)
    args = parser.parse_args()
    run_funnel(args.csv_path, args.month)
