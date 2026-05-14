from dataclasses import dataclass, field
from typing import List
from backtest.simulator import DayStats

@dataclass
class EvalResult:
    eval_number: int
    days_traded: int
    profit: float
    passed: bool
    fail_reason: str = ""  # "drawdown", "consistency", "timeout"

@dataclass
class PayoutResult:
    payout_number: int
    gross_profit: float
    payout_amount: float  # 90% of profit, capped at $2000

@dataclass
class FundedResult:
    funded_number: int
    days_traded: int
    qualifying_days: int
    payout_cycles: int
    total_profit: float
    blown: bool

@dataclass
class PropFirmReport:
    evals: List[EvalResult] = field(default_factory=list)
    funded: List[FundedResult] = field(default_factory=list)
    payouts: List[PayoutResult] = field(default_factory=list)
    total_eval_fees: float = 0.0
    total_payouts: float = 0.0
    net_profit: float = 0.0

def simulate_lucid_flex(
    day_stats: List[DayStats],
    eval_fee: float = 150.0,        # LucidFlex 50k eval fee (approximate)
    profit_target: float = 3000.0,
    max_eod_drawdown: float = 2000.0,
    consistency_ratio: float = 0.50,  # No single day > 50% of total profit (eval only)
    min_payout_days: int = 5,         # Funded: need 5 days with >=150 profit
    min_day_profit: float = 150.0,    # Min profit per day to count toward payout
    payout_split: float = 0.90,       # 90% to trader
    max_payout: float = 2000.0,       # Capped per payout cycle
) -> PropFirmReport:
    """
    Simulate LucidFlex 50k eval -> funded -> payout cycle using daily P&L data.
    """
    report = PropFirmReport()
    eval_number = 0
    payout_number = 0
    day_index = 0
    total_days = len(day_stats)

    while day_index < total_days:
        # -- Start a new eval --
        eval_number += 1
        report.total_eval_fees += eval_fee
        cumulative_profit = 0.0
        peak_profit = 0.0
        eval_days = 0
        eval_passed = False
        fail_reason = ""
        best_day_profit = 0.0

        eval_start = day_index
        while day_index < total_days:
            day = day_stats[day_index]
            day_index += 1
            eval_days += 1

            cumulative_profit += day.pnl

            # Track best single day for consistency rule
            if day.pnl > best_day_profit:
                best_day_profit = day.pnl

            # EOD trailing drawdown check
            if cumulative_profit > peak_profit:
                peak_profit = cumulative_profit
            drawdown_from_peak = peak_profit - cumulative_profit
            if drawdown_from_peak >= max_eod_drawdown:
                fail_reason = "drawdown"
                break

            # Also check if we've gone so negative that we can't recover
            if cumulative_profit <= -max_eod_drawdown:
                fail_reason = "drawdown"
                break

            # Profit target check
            if cumulative_profit >= profit_target:
                # Consistency check: no single day > 50% of total profit
                if best_day_profit > cumulative_profit * consistency_ratio:
                    fail_reason = "consistency"
                    break
                eval_passed = True
                break

        result = EvalResult(
            eval_number=eval_number,
            days_traded=eval_days,
            profit=round(cumulative_profit, 2),
            passed=eval_passed,
            fail_reason=fail_reason,
        )
        report.evals.append(result)

        if not eval_passed:
            continue  # restart new eval

        # -- Funded phase --
        funded_cumulative = 0.0
        qualifying_days = 0
        payout_cycle_days = 0
        funded_peak = 0.0
        funded_days_total = 0
        funded_payout_cycles = 0
        funded_blown = False
        funded_profit_total = 0.0

        while day_index < total_days:
            day = day_stats[day_index]
            day_index += 1
            payout_cycle_days += 1
            funded_days_total += 1

            funded_cumulative += day.pnl
            funded_profit_total += day.pnl
            if funded_cumulative > funded_peak:
                funded_peak = funded_cumulative

            # Drawdown check on funded (EOD trailing from peak)
            if funded_peak - funded_cumulative >= max_eod_drawdown:
                funded_blown = True
                break

            # Count qualifying payout days
            if day.pnl >= min_day_profit:
                qualifying_days += 1

            # Payout trigger
            if qualifying_days >= min_payout_days and funded_cumulative > 0:
                payout_number += 1
                funded_payout_cycles += 1
                gross = funded_cumulative
                payout_amount = min(gross * payout_split, max_payout)
                report.payouts.append(PayoutResult(
                    payout_number=payout_number,
                    gross_profit=round(gross, 2),
                    payout_amount=round(payout_amount, 2),
                ))
                report.total_payouts += payout_amount
                # Reset for next payout cycle
                funded_cumulative = 0.0
                funded_peak = 0.0
                qualifying_days = 0
                payout_cycle_days = 0

        report.funded.append(FundedResult(
            funded_number=eval_number,
            days_traded=funded_days_total,
            qualifying_days=qualifying_days,
            payout_cycles=funded_payout_cycles,
            total_profit=round(funded_profit_total, 2),
            blown=funded_blown,
        ))

    report.net_profit = round(report.total_payouts - report.total_eval_fees, 2)
    return report
