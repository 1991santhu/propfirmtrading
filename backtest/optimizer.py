"""
Parameter optimizer — runs all strategy x parameter combinations and ranks by net profit.

Usage:
    python -m backtest.optimizer backtest/data/MNQ_5min.csv
    python -m backtest.optimizer backtest/data/MNQ_5min.csv --top 30
"""
import sys
import argparse
import pandas as pd
from backtest.signals import load_csv, add_key_levels, add_ema_clouds, filter_rth
from backtest.simulator import simulate_trades
from backtest.prop_firm import simulate_lucid_flex
from backtest.strategies import ALL_STRATEGIES

# ── Default parameter grid ──────────────────────────────────────────────────
DEFAULT_STOP_POINTS    = [20, 30, 40, 50, 60]
DEFAULT_RR_RATIOS      = [1.5, 2.0, 2.5, 3.0]
DEFAULT_CONTRACTS      = [3, 5]
DEFAULT_MAX_LOSSES     = [1, 2]
DEFAULT_MAX_TRADES     = [5]
DEFAULT_REENTRY        = [False, True]


def run_optimizer(
    csv_path: str,
    stop_points_list: list  = DEFAULT_STOP_POINTS,
    rr_ratios: list         = DEFAULT_RR_RATIOS,
    contracts_list: list    = DEFAULT_CONTRACTS,
    max_losses_list: list   = DEFAULT_MAX_LOSSES,
    max_trades_list: list   = DEFAULT_MAX_TRADES,
    reentry_list: list      = DEFAULT_REENTRY,
    top_n: int              = 20,
):
    # ── Load + enrich data once ─────────────────────────────────────────────
    print(f"Loading data: {csv_path}")
    df_raw = load_csv(csv_path)
    df_raw = add_key_levels(df_raw)
    df_raw = add_ema_clouds(df_raw)
    df     = filter_rth(df_raw)
    print(f"RTH bars: {len(df)}  |  Date range: {df.index[0].date()} -> {df.index[-1].date()}")

    total_combos = (
        len(ALL_STRATEGIES) * len(reentry_list) *
        len(stop_points_list) * len(rr_ratios) *
        len(contracts_list) * len(max_losses_list) * len(max_trades_list)
    )
    print(f"Running {total_combos} combinations across {len(ALL_STRATEGIES)} strategies...\n")

    # ── Pre-compute signals for each (strategy, reentry) pair ───────────────
    signal_cache = {}
    for strategy in ALL_STRATEGIES:
        for reentry in reentry_list:
            key = (strategy.name, reentry)
            signal_cache[key] = strategy.generate_signals(df, reentry=reentry)

    # ── Grid search ─────────────────────────────────────────────────────────
    results = []
    done = 0

    for strategy in ALL_STRATEGIES:
        for reentry in reentry_list:
            df_signals = signal_cache[(strategy.name, reentry)]
            for stop in stop_points_list:
                for rr in rr_ratios:
                    for contracts in contracts_list:
                        for max_losses in max_losses_list:
                            for max_trades in max_trades_list:
                                trades, day_stats = simulate_trades(
                                    df_signals,
                                    contracts=contracts,
                                    stop_points=stop,
                                    max_daily_losses=max_losses,
                                    max_daily_trades=max_trades,
                                    rr_ratio=rr,
                                )
                                pf = simulate_lucid_flex(day_stats)

                                total  = len(trades)
                                wins   = sum(1 for t in trades if t.pnl > 0)
                                pnl    = sum(t.pnl for t in trades)
                                ep     = sum(1 for e in pf.evals if e.passed)
                                ea     = len(pf.evals)
                                stopped = sum(1 for d in day_stats if d.stopped_early)

                                results.append({
                                    'strategy':    strategy.name,
                                    'reentry':     'Y' if reentry else 'N',
                                    'stop':        stop,
                                    'rr':          rr,
                                    'contracts':   contracts,
                                    'max_losses':  max_losses,
                                    'max_trades':  max_trades,
                                    'trades':      total,
                                    'win_pct':     round(wins / total * 100, 1) if total > 0 else 0,
                                    'pnl':         round(pnl),
                                    'evals_pass':  f"{ep}/{ea}",
                                    'payouts':     round(pf.total_payouts),
                                    'net':         round(pf.net_profit),
                                    'stop_days':   stopped,
                                })

                                done += 1
                                if done % 100 == 0:
                                    print(f"  {done}/{total_combos} done...", flush=True)

    # ── Sort and display top N ───────────────────────────────────────────────
    results.sort(key=lambda r: r['net'], reverse=True)
    top = results[:top_n]

    print(f"\n{'='*120}")
    print(f"  TOP {top_n} COMBINATIONS (ranked by net profit = payouts - eval fees)")
    print(f"{'='*120}")
    hdr = (f"{'#':<3} {'Strategy':<28} {'Re':<3} {'Stop':<5} {'R:R':<5} "
           f"{'Cts':<4} {'ML':<3} {'Trd':<5} {'Win%':<6} {'P&L':>8} "
           f"{'Evals':<7} {'Payouts':>8} {'Net':>8} {'StopDays'}")
    print(hdr)
    print("-" * 120)
    for i, r in enumerate(top, 1):
        print(
            f"{i:<3} {r['strategy']:<28} {r['reentry']:<3} {r['stop']:<5} {r['rr']:<5} "
            f"{r['contracts']:<4} {r['max_losses']:<3} {r['trades']:<5} {r['win_pct']:<6} "
            f"${r['pnl']:>7,} {r['evals_pass']:<7} ${r['payouts']:>7,} ${r['net']:>7,} "
            f"{r['stop_days']}"
        )
    print(f"{'='*120}")

    if results:
        best = results[0]
        print(f"\n  BEST: {best['strategy']} | Re-entry={best['reentry']} | "
              f"Stop={best['stop']}pts | R:R={best['rr']} | Contracts={best['contracts']} | "
              f"MaxLoss={best['max_losses']} | Net=${best['net']:,}\n")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--top",  type=int, default=20)
    args = parser.parse_args()
    run_optimizer(args.csv_path, top_n=args.top)
