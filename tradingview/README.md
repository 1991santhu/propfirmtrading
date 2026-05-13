# TradingView Pine Script — PropFirm Bot Signals [MNQ]

This single Pine Script serves three purposes simultaneously:
- **Live alerts** — fires webhook JSON to the Python bot when a signal triggers
- **Visual indicator** — renders Ripster EMA clouds and signal arrows on the chart
- **Strategy backtesting** — TradingView Strategy Tester shows P&L, win rate, and drawdown

---

## 1. Adding the Script to TradingView

1. Open TradingView and load an MNQ or MES chart.
2. Set the chart timeframe to **5 minutes**.
3. Click **Pine Editor** at the bottom of the screen.
4. Paste the full contents of `bot_signals.pine` into the editor.
5. Click **Save**, then click **Add to chart**.
6. The EMA clouds and signal arrows will appear on the chart immediately.

---

## 2. Setting Up Webhook Alerts

> **Requirement:** TradingView Pro, Pro+, or Premium plan (webhooks are not available on the free plan).

1. With the script on the chart, click the **Alerts** button (bell icon) or press `Alt+A`.
2. Click **Create Alert**.
3. Set **Condition** to `PropFirm Bot Signals [MNQ]` and choose either:
   - `Long Signal` for long entries
   - `Short Signal` for short entries
4. Set **Trigger** to `Once Per Bar Close` (recommended) or `Once Per Bar`.
5. Under **Notifications**, enable **Webhook URL** and paste your Python bot's webhook endpoint:
   ```
   http://YOUR_SERVER_IP:8080/webhook
   ```
6. Leave the **Message** field blank — the alert message is pre-built by the script and sent automatically as JSON:
   ```json
   {"signal":"long","symbol":"MNQM5","price":12345.00,"secret":"your-secret"}
   ```
7. Open the script **Settings** (double-click the script name on the chart):
   - Set **Webhook Secret** to match the `WEBHOOK_SECRET` environment variable in your Python bot.
   - Set **Symbol** to the active contract (e.g., `MNQM5`, `MNQU5`).
8. Click **Create** to save the alert. Repeat steps 1–7 for the opposite direction.

---

## 3. Backtesting with Strategy Tester

1. After adding the script to the chart, click the **Strategy Tester** tab at the bottom.
2. TradingView will automatically run the backtest on the visible chart history.
3. Review the **Overview** tab for net profit, win rate, max drawdown, and profit factor.
4. Open **Settings** on the script to adjust parameters before re-running:
   - **Stop Loss (points):** default `30` — matches the live bot's 30-point stop.
   - **default_qty_value** is set to `3` contracts in the script header (edit in Pine Editor to change).
5. Use the **Properties** tab in Strategy Tester to verify:
   - Initial capital: $50,000
   - Commission: $0.50/contract
   - Slippage: 2 ticks

---

## 4. Input Parameters

| Input | Default | Group | Description |
|---|---|---|---|
| `Stop Loss (points)` | `30` | Risk | Points from entry to stop. Also drives 1R trail activation and 2R take profit. |
| `Webhook Secret` | `change-me` | Alerts | Must match `WEBHOOK_SECRET` in the Python bot's environment. |
| `Symbol` | `MNQM5` | Alerts | Futures contract symbol sent in the webhook JSON payload. Update each rollover. |
| `Show EMA Clouds` | `true` | Display | Toggle visibility of the Ripster EMA cloud fills. |

---

## Signal Logic Summary

- **Long:** EMA(8) > EMA(9) AND EMA(5) > EMA(12) on hl2 — first bar where both clouds flip green.
- **Short:** EMA(8) < EMA(9) AND EMA(5) < EMA(12) on hl2 — first bar where both clouds flip red.
- **RTH filter:** Signals only fire between 9:30 AM and 4:20 PM America/New_York.
- **EOD close:** Any open position is force-closed at 4:30 PM ET.

---

## Exit Logic

| Event | Action |
|---|---|
| Entry | Open position at signal bar close |
| 1R hit | Trailing stop activates with 1R offset (effectively moves stop to breakeven) |
| 2R hit | Take profit limit order fills |
| Stop hit | Stop loss fills |
| 4:30 PM ET | Position force-closed regardless of P&L |
