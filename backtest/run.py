import sys
import pandas as pd
from backtest.signals import load_csv, add_signals, add_key_levels, add_ema_clouds, filter_rth
from backtest.simulator import simulate_trades
from backtest.prop_firm import simulate_lucid_flex
from backtest.strategies import ALL_STRATEGIES


def run(csv_path: str, contracts: int = 3, stop_points: int = 30):
    print(f"\nLoading data: {csv_path}")
    df_raw = load_csv(csv_path)

    # Add key levels BEFORE filtering to RTH (needs pre-market data)
    df_raw = add_key_levels(df_raw)
    df_raw = add_ema_clouds(df_raw)

    # Filter to RTH for actual signal generation + trading
    df = filter_rth(df_raw)

    print(f"Date range: {df.index[0]} -> {df.index[-1]}")
    print(f"RTH bars: {len(df)}\n")

    results = []

    for strategy in ALL_STRATEGIES:
        for reentry in [False, True]:
            df_signals = strategy.generate_signals(df, reentry=reentry)
            trades, day_stats = simulate_trades(
                df_signals, contracts=contracts, stop_points=stop_points, rr_ratio=2.0
            )
            pf_report = simulate_lucid_flex(day_stats)

            total = len(trades)
            wins  = sum(1 for t in trades if t.pnl > 0)
            total_pnl = sum(t.pnl for t in trades)
            evals_passed = sum(1 for e in pf_report.evals if e.passed)
            stopped_days = sum(1 for d in day_stats if d.stopped_early)

            results.append({
                'strategy': strategy.name,
                'reentry': 'Yes' if reentry else 'No',
                'trades': total,
                'win_pct': f"{wins/total*100:.1f}%" if total > 0 else "N/A",
                'pnl': f"${total_pnl:,.0f}",
                'evals': f"{evals_passed}/{len(pf_report.evals)}",
                'payouts': f"${pf_report.total_payouts:,.0f}",
                'net': f"${pf_report.net_profit:,.0f}",
                'stopped_days': stopped_days,
            })

    # Print comparison table
    print("=" * 100)
    print(f"  STRATEGY COMPARISON  ({contracts} contracts, {stop_points}-pt stop)")
    print("=" * 100)
    header = f"{'Strategy':<30} {'Re-entry':<10} {'Trades':<8} {'Win%':<7} {'P&L':<10} {'Evals':<8} {'Payouts':<10} {'Net':<10} {'Stop Days'}"
    print(header)
    print("-" * 100)
    for r in results:
        print(
            f"{r['strategy']:<30} {r['reentry']:<10} {r['trades']:<8} "
            f"{r['win_pct']:<7} {r['pnl']:<10} {r['evals']:<8} "
            f"{r['payouts']:<10} {r['net']:<10} {r['stopped_days']}"
        )
    print("=" * 100)

    # Best strategy by net profit
    best = max(results, key=lambda r: float(r['net'].replace('$', '').replace(',', '')))
    print(f"\n  Best: {best['strategy']} (re-entry={best['reentry']}) -> Net {best['net']}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m backtest.run <csv_path> [contracts] [stop_points]")
        sys.exit(1)
    csv_path = sys.argv[1]
    contracts   = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    stop_points = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    run(csv_path, contracts, stop_points)
