"""
LucidFlex 50k prop firm simulation — accurate full account lifecycle.

Models the complete sequence: eval → funded (up to 5 payouts) → live candidate.

Key rules captured (from docs/lucidflex_rules.md):
  - Eval: $3k target, $2k EOD trailing drawdown, 50% consistency (eval only)
  - Funded: EOD trailing MLL, no DLL, no consistency rule
  - MLL lock: MLL trails until balance > $52,100; then permanently locks at $50,100
  - Payout trigger also locks MLL immediately (even before $52,100)
  - Payout amount: min(50% × cycle_profit, $2,000) × 90% to trader
  - Balance decreases by the full withdrawal (90% + 10% both leave your account)
  - 5 payouts max per funded account → live candidate
  - Zero-payout blown funded account → eval fee refunded
"""
from dataclasses import dataclass, field
from typing import List
from backtest.simulator import DayStats


@dataclass
class EvalResult:
    eval_number: int
    days_traded: int
    profit: float
    passed: bool
    fail_reason: str = ""   # "drawdown", "consistency", ""


@dataclass
class FundedResult:
    funded_number: int
    days_traded: int
    payouts: int
    total_withdrawn: float   # total withdrawn from account (100% side)
    trader_received: float   # 90% of total_withdrawn
    peak_balance: float
    final_balance: float
    live_candidate: bool     # True if hit 5 payouts
    blown: bool
    eval_refunded: bool      # True if 0 payouts before blow → eval fee refunded


@dataclass
class PayoutResult:
    payout_number: int       # global sequence
    funded_number: int       # which funded account
    cycle_profit: float      # profit in this payout cycle
    withdrawal: float        # amount deducted from account (= payout_amount before 90%)
    trader_amount: float     # withdrawal × 0.90
    balance_after: float
    mll_after: float


@dataclass
class LucidFlexReport:
    evals: List[EvalResult] = field(default_factory=list)
    funded_accounts: List[FundedResult] = field(default_factory=list)
    payouts: List[PayoutResult] = field(default_factory=list)
    total_eval_fees: float = 0.0
    total_payouts: float = 0.0     # sum of trader_amount across all payouts
    total_refunds: float = 0.0     # eval fees refunded on zero-payout blows
    live_candidates: int = 0
    net_profit: float = 0.0


def simulate_lucid_flex(
    day_stats: List[DayStats],
    # ── Account sizing ───────────────────────────────────────────────
    account_size: float = 50_000.0,
    eval_fee: float = 150.0,
    # ── Eval rules ───────────────────────────────────────────────────
    profit_target: float = 3_000.0,
    max_drawdown: float = 2_000.0,
    consistency_ratio: float = 0.50,
    # ── MLL lock mechanics ───────────────────────────────────────────
    # MLL trails until balance exceeds (account_size + max_drawdown + 100)
    # then locks permanently at (account_size + 100)
    mll_lock_trigger: float = 52_100.0,   # balance above this → MLL locks
    mll_lock_floor: float = 50_100.0,     # MLL permanently set to this on lock
    # ── Payout rules ─────────────────────────────────────────────────
    min_payout_days: int = 5,
    min_day_profit: float = 150.0,
    payout_max_pct: float = 0.50,         # max 50% of cycle profit per payout
    payout_cap: float = 2_000.0,          # hard cap per cycle
    payout_split: float = 0.90,           # 90% to trader
    max_funded_payouts: int = 5,          # after 5 payouts → live candidate
) -> LucidFlexReport:
    """
    Simulate full LucidFlex lifecycle over the provided day_stats.

    Sequentially works through day_stats:
      1. Eval phase: accumulate profit, check drawdown + consistency + target
      2. On eval pass → funded phase: EOD trailing MLL, payout cycles
      3. After 5 payouts → mark as live candidate, start new eval
      4. On blow → zero-payout refund if applicable, start new eval
    """
    report = LucidFlexReport()
    eval_number = 0
    funded_number = 0
    global_payout_number = 0
    day_index = 0
    total_days = len(day_stats)

    while day_index < total_days:

        # ────────────────────────────── EVAL PHASE ──────────────────────────────
        eval_number += 1
        report.total_eval_fees += eval_fee

        cumul = 0.0
        peak = 0.0
        best_day = 0.0   # biggest single profitable day
        eval_days = 0
        eval_passed = False
        fail_reason = ""

        while day_index < total_days:
            day = day_stats[day_index]
            day_index += 1
            eval_days += 1

            cumul += day.pnl
            if day.pnl > 0 and day.pnl > best_day:
                best_day = day.pnl

            # EOD trailing drawdown
            if cumul > peak:
                peak = cumul
            if peak - cumul >= max_drawdown or cumul <= -max_drawdown:
                fail_reason = "drawdown"
                break

            # Profit target hit
            if cumul >= profit_target:
                if best_day > cumul * consistency_ratio:
                    fail_reason = "consistency"
                    break
                eval_passed = True
                break

        report.evals.append(EvalResult(
            eval_number=eval_number,
            days_traded=eval_days,
            profit=round(cumul, 2),
            passed=eval_passed,
            fail_reason=fail_reason,
        ))

        if not eval_passed:
            continue

        # ────────────────────────────── FUNDED PHASE ────────────────────────────
        funded_number += 1
        sim_balance = account_size
        mll = account_size - max_drawdown     # $48,000 initially
        mll_locked = False
        peak_balance = account_size

        payout_count = 0
        cycle_profit = 0.0
        qual_days = 0
        total_withdrawn = 0.0
        total_trader = 0.0
        funded_days = 0
        live_candidate = False
        blown = False

        while day_index < total_days:
            day = day_stats[day_index]
            day_index += 1
            funded_days += 1

            sim_balance += day.pnl
            cycle_profit += day.pnl

            # EOD: update trailing MLL (only if not locked)
            if sim_balance > peak_balance:
                peak_balance = sim_balance
                if not mll_locked:
                    mll = peak_balance - max_drawdown
                    if sim_balance >= mll_lock_trigger:
                        mll_locked = True
                        mll = mll_lock_floor

            # Breach check
            if sim_balance <= mll:
                blown = True
                break

            # Count qualifying days (current cycle)
            if day.pnl >= min_day_profit:
                qual_days += 1

            # Payout trigger
            if qual_days >= min_payout_days and cycle_profit > 0:
                withdrawal = min(cycle_profit * payout_max_pct, payout_cap)
                trader_amount = round(withdrawal * payout_split, 2)
                withdrawal = round(withdrawal, 2)

                sim_balance -= withdrawal
                total_withdrawn += withdrawal
                total_trader += trader_amount
                report.total_payouts += trader_amount

                # Payout always locks MLL
                if not mll_locked:
                    mll_locked = True
                    mll = mll_lock_floor

                global_payout_number += 1
                payout_count += 1
                report.payouts.append(PayoutResult(
                    payout_number=global_payout_number,
                    funded_number=funded_number,
                    cycle_profit=round(cycle_profit, 2),
                    withdrawal=withdrawal,
                    trader_amount=trader_amount,
                    balance_after=round(sim_balance, 2),
                    mll_after=round(mll, 2),
                ))

                # Reset cycle
                cycle_profit = 0.0
                qual_days = 0

                if payout_count >= max_funded_payouts:
                    live_candidate = True
                    report.live_candidates += 1
                    break

        # Zero-payout blow → refund eval fee
        eval_refunded = blown and payout_count == 0
        if eval_refunded:
            report.total_refunds += eval_fee
            report.total_eval_fees -= eval_fee

        report.funded_accounts.append(FundedResult(
            funded_number=funded_number,
            days_traded=funded_days,
            payouts=payout_count,
            total_withdrawn=round(total_withdrawn, 2),
            trader_received=round(total_trader, 2),
            peak_balance=round(peak_balance, 2),
            final_balance=round(sim_balance, 2),
            live_candidate=live_candidate,
            blown=blown,
            eval_refunded=eval_refunded,
        ))

    report.net_profit = round(
        report.total_payouts - report.total_eval_fees, 2
    )
    return report
