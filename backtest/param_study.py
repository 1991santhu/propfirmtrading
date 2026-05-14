"""
Full parameterized strategy comparison study.

Runs all strategies (or a subset) across all parameter combos and saves
a markdown report to docs/backtest_results/

Usage:
    # All strategies, full data period
    python -m backtest.param_study backtest/data/MNQ_5min.csv

    # April only
    python -m backtest.param_study backtest/data/MNQ_5min.csv --month 2026-04

    # Date range
    python -m backtest.param_study backtest/data/MNQ_5min.csv --from 2025-01-01 --to 2025-12-31

    # Single strategy, custom param grid
    python -m backtest.param_study backtest/data/MNQ_5min.csv --strategy G \
        --rr 1.0 1.5 2.0 --be-buffer 0 10 20 --stop 40 60 80

    # All strategies, fixed params (quick scan)
    python -m backtest.param_study backtest/data/MNQ_5min.csv --rr 2.0 --be-buffer 0 --no-save
"""
import argparse
import os
from datetime import datetime
from itertools import product

import pandas as pd

from backtest.signals import load_csv, add_key_levels, add_ema_clouds, filter_rth
from backtest.simulator import simulate_trades, Trade, DayStats
from backtest.prop_firm import simulate_lucid_flex
from backtest.strategies import ALL_STRATEGIES

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "backtest_results")


def _eval_stats(day_stats: list[DayStats]) -> dict:
    pf = simulate_lucid_flex(day_stats)
    blown = sum(1 for e in pf.evals if not e.passed and e.fail_reason == "drawdown")
    cons_fail = sum(1 for e in pf.evals if not e.passed and e.fail_reason == "consistency")
    passed = sum(1 for e in pf.evals if e.passed)
    return {
        "evals":     len(pf.evals),
        "passed":    passed,
        "blown":     blown,
        "cons_fail": cons_fail,
        "payouts":   round(pf.total_payouts),
        "fees":      round(pf.total_eval_fees),
        "net":       round(pf.net_profit),
    }


def run_combo(
    df_sig: pd.DataFrame,
    stop_pts: int | None,
    rr: float,
    be_buf: int,
    max_tr: int,
    contracts: int,
    max_losses: int,
    no_first_30min: bool = True,
    stop_pct: float | None = None,  # % of entry price; overrides stop_pts if set
) -> dict | None:
    trades, day_stats = simulate_trades(
        df_sig,
        contracts=contracts,
        stop_points=stop_pts or 60,
        stop_pct=stop_pct,
        rr_ratio=rr,
        be_buffer_points=be_buf,
        max_daily_losses=max_losses,
        max_daily_trades=max_tr,
        no_first_30min=no_first_30min,
    )
    if not trades:
        return None

    total    = len(trades)
    tp_exits = [t for t in trades if t.exit_reason == "tp"]
    be_exits = [t for t in trades if t.exit_reason == "be_stop"]
    losses   = [t for t in trades if t.pnl < 0 and t.exit_reason == "sl"]
    wins     = [t for t in trades if t.pnl > 0]
    avg_stop = round(sum(t.stop_points for t in trades) / total, 1)

    stop_label = f"{stop_pct:.2f}%" if stop_pct else f"{stop_pts}pt"
    ev = _eval_stats(day_stats)
    return {
        "stop":      stop_label,
        "rr":        rr,
        "be_buf":    be_buf,
        "max_tr":    max_tr,
        "avg_stop":  avg_stop,
        "trades":    total,
        "win_pct":   round(len(wins) / total * 100, 1),
        "tp_pct":    round(len(tp_exits) / total * 100, 1),
        "be_pct":    round(len(be_exits) / total * 100, 1),
        "sl_pct":    round(len(losses)   / total * 100, 1),
        "pnl":       round(sum(t.pnl for t in trades)),
        "green":     sum(1 for d in day_stats if d.pnl > 0),
        "red":       sum(1 for d in day_stats if d.pnl < 0),
        "qual":      sum(1 for d in day_stats if d.pnl >= 150),
        "days":      len(day_stats),
        **ev,
    }


def format_table(rows: list[dict], label: str, per_strategy: bool = False) -> str:
    if not rows:
        return f"\n*No trades generated.*\n"

    rows_sorted = sorted(rows, key=lambda r: r["net"], reverse=True)

    if per_strategy:
        hdr = (
            f"| {'Strategy':<32} | {'Stop':>6} | {'AvgPt':>5} | {'RR':>4} | {'BE':>4} | "
            f"{'Trd':>4} | {'Win%':>5} | {'TP%':>5} | {'BE%':>5} | {'SL%':>5} | "
            f"{'P&L':>8} | {'Grn':>4} | {'Red':>4} | {'Qual':>5} | "
            f"{'Evls':>4} | {'Pass':>4} | {'Blow':>4} | {'Payouts':>8} | {'Net':>8} |"
        )
    else:
        hdr = (
            f"| {'Stop':>6} | {'AvgPt':>5} | {'RR':>4} | {'BE':>4} | "
            f"{'Trd':>4} | {'Win%':>5} | {'TP%':>5} | {'BE%':>5} | {'SL%':>5} | "
            f"{'P&L':>8} | {'Grn':>4} | {'Red':>4} | {'Qual':>5} | "
            f"{'Evls':>4} | {'Pass':>4} | {'Blow':>4} | {'Payouts':>8} | {'Net':>8} |"
        )

    parts = hdr.split("|")
    sep = "|" + "|".join("-" * (len(p)) for p in parts[1:-1]) + "|"

    lines = [hdr, sep]
    for r in rows_sorted:
        strat_col = f"| {r.get('strategy',''):<32} " if per_strategy else ""
        lines.append(
            f"{strat_col}"
            f"| {r['stop']:>6} | {r.get('avg_stop', '-'):>5} | {r['rr']:>4} | {r['be_buf']:>4} | "
            f"{r['trades']:>4} | {r['win_pct']:>5} | {r['tp_pct']:>5} | {r['be_pct']:>5} | {r['sl_pct']:>5} | "
            f"${r['pnl']:>7,} | {r['green']:>4} | {r['red']:>4} | {r['qual']:>5} | "
            f"{r['evals']:>4} | {r['passed']:>4} | {r['blown']:>4} | "
            f"${r['payouts']:>7,} | ${r['net']:>7,} |"
        )
    return "\n".join(lines)


def run_study(
    csv_path: str,
    month: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    strategy_prefix: str | None = None,
    rr_ratios: list[float] | None = None,
    be_buffers: list[int] | None = None,
    stop_pts_list: list[int] | None = None,
    stop_pct_list: list[float] | None = None,   # e.g. [0.15, 0.20, 0.25] for % of price
    max_trades_list: list[int] | None = None,
    contracts: int = 5,
    max_losses: int = 2,
    reentry_modes: list[bool] | None = None,
    save_report: bool = True,
) -> None:
    # Defaults — use 0.20% of entry price if no stop specified
    # This keeps risk comparable across price eras (MNQ 14k→29k)
    rr_ratios       = rr_ratios       or [1.5, 2.0]
    be_buffers      = be_buffers      or [0, 10]
    if not stop_pts_list and not stop_pct_list:
        stop_pct_list = [0.20]
    stop_pts_list   = stop_pts_list   or []
    stop_pct_list   = stop_pct_list   or []
    max_trades_list = max_trades_list or [5]
    reentry_modes   = reentry_modes   or [False]
    # combined stop specs: (label_suffix, pts, pct)
    all_stops = [(s, None) for s in stop_pts_list] + [(None, p) for p in stop_pct_list]

    # Load and filter data
    df_raw = load_csv(csv_path)
    df_raw = add_key_levels(df_raw)
    df_raw = add_ema_clouds(df_raw)
    df_rth = filter_rth(df_raw)

    if month:
        df_rth = df_rth[df_rth.index.to_period("M") == month]
        label = month
    elif date_from or date_to:
        if date_from:
            df_rth = df_rth[df_rth.index >= date_from]
        if date_to:
            df_rth = df_rth[df_rth.index <= date_to + " 23:59:59"]
        label = f"{date_from or '?'} to {date_to or '?'}"
    else:
        label = f"{df_rth.index[0].date()} → {df_rth.index[-1].date()}"

    if len(df_rth) == 0:
        print(f"No data for period: {label}")
        return

    print(f"\nData: {label}  ({len(df_rth)} RTH bars, "
          f"{df_rth.index[0].date()} → {df_rth.index[-1].date()})")

    # Select strategies
    strategies = ALL_STRATEGIES
    if strategy_prefix:
        strategies = [s for s in strategies if s.name.startswith(strategy_prefix)]
        if not strategies:
            print(f"No strategy found starting with {strategy_prefix!r}")
            return

    # Run all combinations
    all_rows: list[dict] = []             # all combos, all strategies
    per_strategy: dict[str, list[dict]] = {}

    total_combos = (
        len(strategies) * len(reentry_modes) *
        len(all_stops) * len(rr_ratios) *
        len(be_buffers) * len(max_trades_list)
    )
    print(f"Running {total_combos} combinations across {len(strategies)} strategies...")

    done = 0
    for strategy in strategies:
        per_strategy[strategy.name] = []
        for reentry in reentry_modes:
            df_sig = strategy.generate_signals(df_rth, reentry=reentry)
            for (stop_pts, stop_pct), rr, be_buf, max_tr in product(
                all_stops, rr_ratios, be_buffers, max_trades_list
            ):
                row = run_combo(df_sig, stop_pts, rr, be_buf, max_tr, contracts, max_losses,
                               no_first_30min=True, stop_pct=stop_pct)
                done += 1
                if row:
                    row["strategy"] = strategy.name
                    row["reentry"]  = reentry
                    all_rows.append(row)
                    per_strategy[strategy.name].append(row)

    print(f"Done. {len(all_rows)} non-empty results.")

    # Best per strategy (max net)
    best_per_strategy: list[dict] = []
    for name, rows in per_strategy.items():
        if rows:
            best = max(rows, key=lambda r: r["net"])
            best_per_strategy.append(best)

    # Print terminal summary
    print(f"\n{'='*60}")
    print(f"  TOP 15 — Best Net across ALL strategies × params")
    print(f"{'='*60}")
    top15 = sorted(all_rows, key=lambda r: r["net"], reverse=True)[:15]
    for i, r in enumerate(top15, 1):
        re_str = "re" if r["reentry"] else "no-re"
        avg = f"(~{r.get('avg_stop','?')}pt)" if "%" in str(r['stop']) else ""
        print(
            f"  {i:>2}. {r['strategy']:<32} ({re_str}) "
            f"stop={r['stop']}{avg} rr={r['rr']} be={r['be_buf']} "
            f"→ win={r['win_pct']}% pnl=${r['pnl']:,} net=${r['net']:,}"
        )

    print(f"\n{'='*60}")
    print(f"  BEST PER STRATEGY (sorted by net)")
    print(f"{'='*60}")
    for r in sorted(best_per_strategy, key=lambda r: r["net"], reverse=True):
        re_str = "re" if r["reentry"] else "no-re"
        avg = f"(~{r.get('avg_stop','?')}pt)" if "%" in str(r['stop']) else ""
        print(
            f"  {r['strategy']:<32} ({re_str}) "
            f"stop={r['stop']}{avg} rr={r['rr']} be={r['be_buf']} "
            f"win={r['win_pct']}% pnl=${r['pnl']:,} net=${r['net']:,}"
        )

    if not save_report:
        return

    # Save markdown report
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    safe_label = label.replace(" ", "_").replace("→", "to").replace("/", "-")
    filename = f"{ts}_{safe_label}.md"
    filepath = os.path.join(RESULTS_DIR, filename)

    lines = [
        f"# Backtest Parameter Study — {label}",
        f"",
        f"**Run date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"**Data:** {df_rth.index[0].date()} → {df_rth.index[-1].date()} ({len(df_rth)} RTH bars)  ",
        f"**Instrument:** /MNQ, ${2}/point, {contracts} contracts  ",
        f"**Parameter grid:** stop_pt={stop_pts_list} stop_pct={stop_pct_list} | rr={rr_ratios} | be_buffer={be_buffers} | max_trades={max_trades_list}  ",
        f"**Total combinations tested:** {done}",
        f"",
        f"---",
        f"",
        f"## Top 15 — Best Net Across All Strategies & Params",
        f"",
        format_table(top15, label, per_strategy=True),
        f"",
        f"---",
        f"",
        f"## Best Configuration Per Strategy",
        f"",
        format_table(sorted(best_per_strategy, key=lambda r: r["net"], reverse=True), label, per_strategy=True),
        f"",
        f"---",
        f"",
        f"## Per-Strategy Detail",
        f"",
    ]

    for name, rows in sorted(per_strategy.items()):
        if not rows:
            continue
        lines.append(f"### {name}")
        lines.append("")
        lines.append(format_table(sorted(rows, key=lambda r: r["net"], reverse=True)[:10], name))
        lines.append("")

    lines += [
        "---",
        "",
        "## Column Definitions",
        "",
        "| Column | Meaning |",
        "|--------|---------|",
        "| Stop | Stop loss in points (60 = $600 risk per contract) |",
        "| RR | Risk:reward ratio for take profit |",
        "| BEbuf | After 1R hit, stop moves to entry + N points |",
        "| MaxT | Max trades per day |",
        "| Win% | % of trades with positive P&L (TP + profitable BE exits) |",
        "| TP% | % of trades that hit take profit |",
        "| BE% | % of trades stopped at breakeven (after 1R hit) |",
        "| SL% | % of trades that hit full stop loss |",
        "| Qual | Days with ≥$150 profit (needed for LucidFlex payout) |",
        "| Evls | Total LucidFlex eval attempts simulated |",
        "| Pass | Evals passed ($3k target, drawdown, consistency) |",
        "| Blow | Evals blown due to $2k drawdown |",
        "| Net | Total payouts − eval fees |",
    ]

    with open(filepath, "w") as f:
        f.write("\n".join(lines))

    print(f"\nReport saved → {filepath}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parameterized strategy comparison study")
    parser.add_argument("csv_path")
    parser.add_argument("--month",      default=None, help="Single month, e.g. 2026-04")
    parser.add_argument("--from",       dest="date_from", default=None, help="Start date YYYY-MM-DD")
    parser.add_argument("--to",         dest="date_to",   default=None, help="End date YYYY-MM-DD")
    parser.add_argument("--strategy",   default=None, help="Strategy prefix, e.g. G or 'G:'")
    parser.add_argument("--rr",         nargs="+", type=float, default=[1.5, 2.0])
    parser.add_argument("--be-buffer",  nargs="+", type=int,   default=[0, 10])
    parser.add_argument("--stop",       nargs="+", type=int,   default=None, help="Fixed stop in points, e.g. 40 60 80")
    parser.add_argument("--stop-pct",   nargs="+", type=float, default=None, help="Stop as %% of entry price, e.g. 0.15 0.20 0.25")
    parser.add_argument("--max-trades", nargs="+", type=int,   default=[5])
    parser.add_argument("--contracts",  type=int,   default=5)
    parser.add_argument("--max-losses", type=int,   default=2)
    parser.add_argument("--reentry",    nargs="+", type=lambda x: x.lower() == "true",
                        default=[False], help="true false (space separated)")
    parser.add_argument("--no-save",    action="store_true", help="Don't save markdown report")
    args = parser.parse_args()

    run_study(
        csv_path        = args.csv_path,
        month           = args.month,
        date_from       = args.date_from,
        date_to         = args.date_to,
        strategy_prefix = args.strategy,
        rr_ratios       = args.rr,
        be_buffers      = args.be_buffer,
        stop_pts_list   = args.stop,
        stop_pct_list   = args.stop_pct,
        max_trades_list = args.max_trades,
        contracts       = args.contracts,
        max_losses      = args.max_losses,
        reentry_modes   = args.reentry,
        save_report     = not args.no_save,
    )
