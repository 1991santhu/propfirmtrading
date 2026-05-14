"""
Detailed per-strategy analysis report.

Usage:
    python -m backtest.analysis backtest/data/MNQ_5min.csv
    python -m backtest.analysis backtest/data/MNQ_5min.csv --contracts 5 --stop 60 --rr 2.0
"""
import argparse
import sys

import pandas as pd

from backtest.signals import load_csv, add_key_levels, add_ema_clouds, filter_rth
from backtest.simulator import simulate_trades, Trade, DayStats
from backtest.prop_firm import simulate_lucid_flex
from backtest.strategies import ALL_STRATEGIES


def analyze_strategy(
    trades: list[Trade],
    day_stats: list[DayStats],
    strategy_name: str,
    reentry: bool,
) -> dict:
    total     = len(trades)
    if total == 0:
        return {"strategy": strategy_name, "reentry": reentry, "trades": 0}

    wins      = [t for t in trades if t.pnl > 0]
    losses    = [t for t in trades if t.pnl < 0 and t.exit_reason == "sl"]
    be_exits  = [t for t in trades if t.exit_reason == "be_stop"]
    tp_exits  = [t for t in trades if t.exit_reason == "tp"]
    eod_exits = [t for t in trades if t.exit_reason == "eod"]
    longs     = [t for t in trades if t.side == "long"]
    shorts    = [t for t in trades if t.side == "short"]

    total_pnl     = sum(t.pnl for t in trades)
    win_pct       = len(wins) / total * 100
    avg_win       = sum(t.pnl for t in wins) / len(wins)   if wins   else 0
    avg_loss      = sum(t.pnl for t in losses) / len(losses) if losses else 0
    profit_factor = (sum(t.pnl for t in wins) / abs(sum(t.pnl for t in losses))
                     if losses and sum(t.pnl for t in wins) > 0 else 0)

    active_days      = len(day_stats)
    green_days       = sum(1 for d in day_stats if d.pnl > 0)
    red_days         = sum(1 for d in day_stats if d.pnl < 0)
    stopped_days     = sum(1 for d in day_stats if d.stopped_early)
    qualifying_days  = sum(1 for d in day_stats if d.pnl >= 150)
    pf               = simulate_lucid_flex(day_stats)

    return {
        "strategy":       strategy_name,
        "reentry":        "Y" if reentry else "N",
        "trades":         total,
        "longs":          len(longs),
        "shorts":         len(shorts),
        "win_pct":        round(win_pct, 1),
        "avg_win":        round(avg_win),
        "avg_loss":       round(avg_loss),
        "profit_factor":  round(profit_factor, 2),
        "tp_pct":         round(len(tp_exits)  / total * 100, 1),
        "sl_pct":         round(len(losses)    / total * 100, 1),
        "be_pct":         round(len(be_exits)  / total * 100, 1),
        "eod_pct":        round(len(eod_exits) / total * 100, 1),
        "total_pnl":      round(total_pnl),
        "green_days":     green_days,
        "red_days":       red_days,
        "stopped_days":   stopped_days,
        "qualifying_days": qualifying_days,
        "active_days":    active_days,
        "evals_pass":     f"{sum(1 for e in pf.evals if e.passed)}/{len(pf.evals)}",
        "payouts":        round(pf.total_payouts),
        "net":            round(pf.net_profit),
    }


def print_summary_table(rows: list[dict]) -> None:
    rows = sorted(rows, key=lambda r: r.get("net", 0), reverse=True)

    header = (
        f"{'#':<3} {'Strategy':<30} {'Re':<3} {'Trd':<5} {'Win%':<6} "
        f"{'AvgW':>6} {'AvgL':>6} {'PF':>5} "
        f"{'TP%':>5} {'SL%':>5} {'BE%':>5} {'EOD%':>5} "
        f"{'P&L':>8} {'GrnDy':>6} {'RedDy':>6} {'StopDy':>7} {'Qual':>5} "
        f"{'Evals':<7} {'Payouts':>8} {'Net':>8}"
    )
    print("\n" + "=" * len(header))
    print("  STRATEGY COMPARISON — sorted by Net Profit (best params per strategy)")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for i, r in enumerate(rows, 1):
        if r.get("trades", 0) == 0:
            print(f"{i:<3} {r['strategy']:<30} {r['reentry']:<3}  — no trades —")
            continue
        print(
            f"{i:<3} {r['strategy']:<30} {r['reentry']:<3} "
            f"{r['trades']:<5} {r['win_pct']:<6} "
            f"{r['avg_win']:>6} {r['avg_loss']:>6} {r['profit_factor']:>5} "
            f"{r['tp_pct']:>5} {r['sl_pct']:>5} {r['be_pct']:>5} {r['eod_pct']:>5} "
            f"${r['total_pnl']:>7,} {r['green_days']:>6} {r['red_days']:>6} "
            f"{r['stopped_days']:>7} {r['qualifying_days']:>5} "
            f"{r['evals_pass']:<7} ${r['payouts']:>7,} ${r['net']:>7,}"
        )
    print("=" * len(header))


def print_detail(r: dict, trades: list[Trade], day_stats: list[DayStats]) -> None:
    print(f"\n{'─'*60}")
    print(f"  DETAIL: {r['strategy']}  (re-entry={r['reentry']})")
    print(f"{'─'*60}")

    # Monthly P&L buckets
    monthly: dict[str, float] = {}
    for t in trades:
        m = t.entry_time.strftime("%Y-%m")
        monthly[m] = monthly.get(m, 0) + t.pnl

    print("  Monthly P&L:")
    for m, pnl in sorted(monthly.items()):
        bar = "█" * int(abs(pnl) / 200)
        sign = "+" if pnl >= 0 else "-"
        print(f"    {m}  {sign}${abs(pnl):>7,.0f}  {bar}")

    # Exit reason breakdown
    print(f"\n  Exit reasons: TP={r['tp_pct']}%  SL={r['sl_pct']}%  "
          f"BE-stop={r['be_pct']}%  EOD={r['eod_pct']}%")
    print(f"  Longs: {r['longs']}  Shorts: {r['shorts']}")
    print(f"  Days — Green: {r['green_days']}  Red: {r['red_days']}  "
          f"Stopped early: {r['stopped_days']}  Qualifying(≥$150): {r['qualifying_days']}")
    print(f"  LucidFlex evals passed: {r['evals_pass']}  "
          f"Total payouts: ${r['payouts']:,}  Net: ${r['net']:,}")

    # Worst 3 days
    worst = sorted(day_stats, key=lambda d: d.pnl)[:3]
    print("\n  Worst 3 days:")
    for d in worst:
        flag = " ← stopped early" if d.stopped_early else ""
        print(f"    {d.date}  ${d.pnl:>8,.0f}  trades={d.trades}{flag}")

    # Best 3 days
    best = sorted(day_stats, key=lambda d: d.pnl, reverse=True)[:3]
    print("\n  Best 3 days:")
    for d in best:
        print(f"    {d.date}  ${d.pnl:>8,.0f}  trades={d.trades}")


def run_analysis(
    csv_path: str,
    contracts: int = 5,
    stop_points: int = 60,
    rr_ratio: float = 2.0,
    max_daily_losses: int = 2,
    max_daily_trades: int = 5,
    detail_top: int = 3,
) -> None:
    print(f"Loading: {csv_path}")
    df_raw = load_csv(csv_path)
    df_raw = add_key_levels(df_raw)
    df_raw = add_ema_clouds(df_raw)
    df     = filter_rth(df_raw)
    print(f"RTH bars: {len(df)}  |  {df.index[0].date()} → {df.index[-1].date()}")
    print(f"Parameters: {contracts} contracts | {stop_points}pt stop | "
          f"{rr_ratio}R TP | max {max_daily_losses} losses/day\n")

    summary_rows = []
    detail_data  = []

    for strategy in ALL_STRATEGIES:
        for reentry in [False, True]:
            df_sig = strategy.generate_signals(df, reentry=reentry)
            trades, day_stats = simulate_trades(
                df_sig,
                contracts=contracts,
                stop_points=stop_points,
                max_daily_losses=max_daily_losses,
                max_daily_trades=max_daily_trades,
                rr_ratio=rr_ratio,
            )
            row = analyze_strategy(trades, day_stats, strategy.name, reentry)
            summary_rows.append(row)
            detail_data.append((row, trades, day_stats))

    print_summary_table(summary_rows)

    # Detailed breakdown for top N strategies by net profit
    ranked = sorted(detail_data, key=lambda x: x[0].get("net", 0), reverse=True)
    print(f"\n{'='*60}")
    print(f"  DETAILED BREAKDOWN — TOP {detail_top} STRATEGIES")
    for row, trades, day_stats in ranked[:detail_top]:
        if row.get("trades", 0) > 0:
            print_detail(row, trades, day_stats)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detailed strategy analysis")
    parser.add_argument("csv_path")
    parser.add_argument("--contracts",   type=int,   default=5)
    parser.add_argument("--stop",        type=int,   default=60)
    parser.add_argument("--rr",          type=float, default=2.0)
    parser.add_argument("--max-losses",  type=int,   default=2)
    parser.add_argument("--max-trades",  type=int,   default=5)
    parser.add_argument("--detail",      type=int,   default=3,
                        help="Number of top strategies to show full detail for")
    args = parser.parse_args()

    run_analysis(
        csv_path=args.csv_path,
        contracts=args.contracts,
        stop_points=args.stop,
        rr_ratio=args.rr,
        max_daily_losses=args.max_losses,
        max_daily_trades=args.max_trades,
        detail_top=args.detail,
    )
