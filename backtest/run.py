import sys
import os
from backtest.signals import load_csv, add_signals, filter_rth
from backtest.simulator import simulate_trades
from backtest.prop_firm import simulate_lucid_flex

def run(csv_path: str, contracts: int = 3, stop_points: int = 30):
    print(f"\nLoading data from: {csv_path}")
    df = load_csv(csv_path)
    df = filter_rth(df)
    df = add_signals(df)

    print(f"Date range: {df.index[0]} -> {df.index[-1]}")
    print(f"Total bars (RTH only): {len(df)}")

    trades, day_stats = simulate_trades(df, contracts=contracts, stop_points=stop_points)

    if not trades:
        print("No trades generated.")
        return

    # -- Trade stats --
    total = len(trades)
    wins  = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl < 0]
    scratch = [t for t in trades if t.pnl == 0]
    total_pnl = sum(t.pnl for t in trades)

    print(f"\n{'='*50}")
    print(f"  TRADE STATISTICS")
    print(f"{'='*50}")
    print(f"  Total trades    : {total}")
    print(f"  Wins            : {len(wins)}  ({len(wins)/total*100:.1f}%)")
    print(f"  Losses (SL)     : {len(losses)}  ({len(losses)/total*100:.1f}%)")
    print(f"  Breakeven stops : {len(scratch)}")
    print(f"  Total P&L       : ${total_pnl:,.2f}")
    if wins:
        print(f"  Avg win         : ${sum(t.pnl for t in wins)/len(wins):,.2f}")
    else:
        print(f"  Avg win         : N/A")
    if losses:
        print(f"  Avg loss        : ${sum(t.pnl for t in losses)/len(losses):,.2f}")
    else:
        print(f"  Avg loss        : N/A")
    by_reason = {}
    for t in trades:
        by_reason[t.exit_reason] = by_reason.get(t.exit_reason, 0) + 1
    print(f"  Exit reasons    : {by_reason}")

    # -- Day stats --
    trading_days = [d for d in day_stats if d.trades > 0]
    stopped_days = [d for d in day_stats if d.stopped_early]
    print(f"\n{'='*50}")
    print(f"  DAY STATISTICS")
    print(f"{'='*50}")
    print(f"  Trading days    : {len(trading_days)}")
    print(f"  Days stopped early (2-loss limit): {len(stopped_days)}")
    print(f"  Avg trades/day  : {total/max(len(trading_days),1):.1f}")

    # -- Prop firm simulation --
    report = simulate_lucid_flex(day_stats)

    print(f"\n{'='*50}")
    print(f"  LUCID FLEX 50K SIMULATION")
    print(f"{'='*50}")
    print(f"  Evals attempted : {len(report.evals)}")
    evals_passed = [e for e in report.evals if e.passed]
    evals_failed = [e for e in report.evals if not e.passed]
    print(f"  Evals passed    : {len(evals_passed)}")
    print(f"  Evals failed    : {len(evals_failed)}")
    if evals_failed:
        reasons = {}
        for e in evals_failed:
            reasons[e.fail_reason] = reasons.get(e.fail_reason, 0) + 1
        print(f"  Fail reasons    : {reasons}")
    print(f"  Total eval fees : ${report.total_eval_fees:,.2f}")
    print(f"  Total payouts   : ${report.total_payouts:,.2f}")
    print(f"  Net profit      : ${report.net_profit:,.2f}")
    if report.payouts:
        print(f"\n  Payout history:")
        for p in report.payouts:
            print(f"    Payout #{p.payout_number}: ${p.payout_amount:,.2f} (from ${p.gross_profit:,.2f} profit)")

    print(f"\n{'='*50}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m backtest.run <path_to_csv> [contracts] [stop_points]")
        print("Example: python -m backtest.run backtest/data/MNQ_5min.csv 3 30")
        sys.exit(1)
    csv_path = sys.argv[1]
    contracts = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    stop_points = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    run(csv_path, contracts, stop_points)
