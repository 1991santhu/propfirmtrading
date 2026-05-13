# Original Indicator Source Code

These are the Pine Script sources for the indicators used in the trading strategy,
as provided by the user.

---

## 1. Daily Levels: PD / PM / OR (RTH/Pre)

TradingView link: https://www.tradingview.com/pine/?id=PUB%3Bf77b55a637c04ecbb9beccdab1a23aa2

```pine
//@version=5
// Updated sample ticker (SPY) to only show indicator described.
indicator("Daily Levels: PD / PM / OR (RTH/Pre)", overlay = true)

// ---------------- CONFIG ----------------
tz = "America/New_York"

// Session windows (ET)
rthSession = "0930-1600"
pmSession  = "0400-0930"

// Opening Range duration
orDuration = input.string("30", "Opening Range Duration (minutes)", options=["30", "60"], group="Settings")
orSession = orDuration == "30" ? "0930-1000" : "0930-1030"

// Display settings
showPD  = input.bool(true, "Show Previous Day (PDH/PDL)", group="Display")
showPDC = input.bool(true, "Show Previous Day Close (PDC)", group="Display")
showPM  = input.bool(true, "Show Pre-Market (PMH/PML)", group="Display")
showOR  = input.bool(true, "Show Opening Range (ORH/ORL)", group="Display")

// Colors
colPD  = color.new(color.blue, 0)
colPM  = color.new(color.green, 0)
colOR  = color.new(color.red, 0)
colPDC = color.new(color.orange, 0)

// ---------------- HELPERS ----------------
inSession(session) => not na(time(timeframe.period, session, tz))

// Detect RTH open (9:30 AM ET)
rthOpen = inSession(rthSession) and not inSession(rthSession)[1]

// Detect OR end (10:00 AM ET)
orJustEnded = not inSession(orSession) and inSession(orSession)[1]

// ---------------- STORAGE ----------------
var float PDH = na
var float PDL = na
var float PDC = na

var float PMH = na
var float PML = na

var float ORH = na
var float ORL = na

var float savedRTHH = na
var float savedRTHL = na
var float savedRTHC = na

var float tmpRTHH = na
var float tmpRTHL = na
var float tmpRTHC = na
var float tmpPMH = na
var float tmpPML = na
var float tmpORH = na
var float tmpORL = na

var bool collectingRTH = false
var bool collectingPM = false

var int rthOpenBar = na

// ---------------- PREVIOUS DAY RTH (09:30 - 16:00 ET) ----------------
inRTH = inSession(rthSession)

if rthOpen
    collectingRTH := true
    tmpRTHH := high
    tmpRTHL := low
    tmpRTHC := close
    rthOpenBar := bar_index

if inRTH and collectingRTH
    tmpRTHH := math.max(tmpRTHH, high)
    tmpRTHL := math.min(tmpRTHL, low)
    tmpRTHC := close

if not inRTH and inRTH[1] and collectingRTH
    savedRTHH := tmpRTHH
    savedRTHL := tmpRTHL
    savedRTHC := tmpRTHC
    collectingRTH := false

// ---------------- PRE-MARKET (04:00 - 09:30 ET) ----------------
inPM = inSession(pmSession)

if inPM and not inPM[1]
    collectingPM := true
    tmpPMH := high
    tmpPML := low

if inPM and collectingPM
    tmpPMH := math.max(tmpPMH, high)
    tmpPML := math.min(tmpPML, low)

if rthOpen
    if collectingPM
        PMH := tmpPMH
        PML := tmpPML
        collectingPM := false
    if not na(savedRTHH)
        PDH := savedRTHH
        PDL := savedRTHL
        PDC := savedRTHC
    ORH := na
    ORL := na
    tmpORH := na
    tmpORL := na

// ---------------- OPENING RANGE (09:30 - 10:00 ET) ----------------
inOR = inSession(orSession)

if inOR and not inOR[1]
    tmpORH := high
    tmpORL := low

if inOR
    tmpORH := math.max(tmpORH, high)
    tmpORL := math.min(tmpORL, low)

if orJustEnded and not na(tmpORH)
    ORH := tmpORH
    ORL := tmpORL

// ---------------- DRAW HELPERS ----------------
f_line(float y, color col) =>
    var line id = na
    if not na(y) and not na(rthOpenBar)
        if na(id)
            id := line.new(x1=rthOpenBar, y1=y, x2=bar_index + 1, y2=y, xloc=xloc.bar_index, extend=extend.right, color=col, width=2)
        else
            line.set_xy1(id, rthOpenBar, y)
            line.set_xy2(id, bar_index + 1, y)
            line.set_color(id, col)
    else
        if not na(id)
            line.delete(id)
    id

f_label_right(float y, string txt, color col) =>
    var label id = na
    if not na(y)
        priceStr = str.format("{0} {1}", txt, str.tostring(y, format.mintick))
        if na(id)
            id := label.new(x=bar_index, y=y, xloc=xloc.bar_index, yloc=yloc.price, text=priceStr, style=label.style_label_right, color=col, textcolor=color.white, size=size.normal)
        else
            label.set_xy(id, bar_index, y)
            label.set_text(id, priceStr)
            label.set_color(id, col)
            label.set_textcolor(id, color.white)
    else
        if not na(id)
            label.delete(id)
    id

// ---------------- OBJECTS ----------------
var line lPDH = na
var line lPDL = na
var line lPDC = na
var line lPMH = na
var line lPML = na
var line lORH = na
var line lORL = na
var label labPDH = na
var label labPDL = na
var label labPDC = na
var label labPMH = na
var label labPML = na
var label labORH = na
var label labORL = na

lPDH := showPD ? f_line(PDH, colPD) : na
lPDL := showPD ? f_line(PDL, colPD) : na
lPDC := showPDC ? f_line(PDC, colPDC) : na
lPMH := showPM ? f_line(PMH, colPM) : na
lPML := showPM ? f_line(PML, colPM) : na
lORH := showOR ? f_line(ORH, colOR) : na
lORL := showOR ? f_line(ORL, colOR) : na

labPDH := showPD ? f_label_right(PDH, "PDH", colPD) : na
labPDL := showPD ? f_label_right(PDL, "PDL", colPD) : na
labPDC := showPDC ? f_label_right(PDC, "PDC", colPDC) : na
labPMH := showPM ? f_label_right(PMH, "PMH", colPM) : na
labPML := showPM ? f_label_right(PML, "PML", colPM) : na
labORH := showOR ? f_label_right(ORH, "ORH", colOR) : na
labORL := showOR ? f_label_right(ORL, "ORL", colOR) : na
```

---

## 2. Ripster EMA Clouds

TradingView link: https://www.tradingview.com/pine/?id=PUB%3BWDTgkTfs2ef2dOLptwW5Ch4WYZoNlmq5

```pine
// This source code is subject to the terms of the Mozilla Public License 2.0
// © ripster47

//@version=4
study("Ripster EMA Clouds","Ripster EMA Clouds", overlay=true)
matype = input(title="MA Type", type=input.string, defval="EMA", options=["EMA", "SMA"])

ma_len1 = input(title="Short EMA1 Length", type=input.integer, defval=8)
ma_len2 = input(title="Long EMA1 Length", type=input.integer, defval=9)
ma_len3 = input(title="Short EMA2 Length", type=input.integer, defval=5)
ma_len4 = input(title="Long EMA2 Length", type=input.integer, defval=12)
ma_len5 = input(title="Short EMA3 Length", type=input.integer, defval=34)
ma_len6 = input(title="Long EMA3 Length", type=input.integer, defval=50)
ma_len7 = input(title="Short EMA4 Length", type=input.integer, defval=72)
ma_len8 = input(title="Long EMA4 Length", type=input.integer, defval=89)
ma_len9 = input(title="Short EMA5 Length", type=input.integer, defval=180)
ma_len10 = input(title="Long EMA5 Length", type=input.integer, defval=200)

src = input(title="Source", type=input.source, defval=hl2)
ma_offset = input(title="Offset", type=input.integer, defval=0)

f_ma(malen) =>
    float result = 0
    if (matype == "EMA")
        result := ema(src, malen)
    if (matype == "SMA")
        result := sma(src, malen)
    result

htf_ma1  = f_ma(ma_len1)
htf_ma2  = f_ma(ma_len2)
htf_ma3  = f_ma(ma_len3)
htf_ma4  = f_ma(ma_len4)
htf_ma5  = f_ma(ma_len5)
htf_ma6  = f_ma(ma_len6)
htf_ma7  = f_ma(ma_len7)
htf_ma8  = f_ma(ma_len8)
htf_ma9  = f_ma(ma_len9)
htf_ma10 = f_ma(ma_len10)

showlong  = input(false, title="Show Long Alerts")
showshort = input(false, title="Show Short Alerts")
showLine  = input(false, title="Display EMA Line")
ema1 = input(true,  title="Show EMA Cloud-1")
ema2 = input(true,  title="Show EMA Cloud-2")
ema3 = input(true,  title="Show EMA Cloud-3")
ema4 = input(false, title="Show EMA Cloud-4")
ema5 = input(false, title="Show EMA Cloud-5")

emacloudleading = input(0, minval=0, title="Leading Period For EMA Cloud")

mashort1 = htf_ma1
malong1  = htf_ma2
mashort2 = htf_ma3
malong2  = htf_ma4
mashort3 = htf_ma5
malong3  = htf_ma6
mashort4 = htf_ma7
malong4  = htf_ma8
mashort5 = htf_ma9
malong5  = htf_ma10

cloudcolour1 = mashort1 >= malong1 ? #036103 : #880e4f
cloudcolour2 = mashort2 >= malong2 ? #4caf50 : #f44336
cloudcolour3 = mashort3 >= malong3 ? #2196f3 : #ffb74d
cloudcolour4 = mashort4 >= malong4 ? #009688 : #f06292
cloudcolour5 = mashort5 >= malong5 ? #05bed5 : #e65100

mashortline1 = plot(ema1 ? mashort1 : na, color=showLine ? color.olive  : na, linewidth=1, offset=emacloudleading, title="Short Leading EMA1")
mashortline2 = plot(ema2 ? mashort2 : na, color=showLine ? color.olive  : na, linewidth=1, offset=emacloudleading, title="Short Leading EMA2")
mashortline3 = plot(ema3 ? mashort3 : na, color=showLine ? color.olive  : na, linewidth=1, offset=emacloudleading, title="Short Leading EMA3")
mashortline4 = plot(ema4 ? mashort4 : na, color=showLine ? color.olive  : na, linewidth=1, offset=emacloudleading, title="Short Leading EMA4")
mashortline5 = plot(ema5 ? mashort5 : na, color=showLine ? color.rgb(179, 179, 43) : na, linewidth=1, offset=emacloudleading, title="Short Leading EMA5")

malongline1 = plot(ema1 ? malong1 : na, color=showLine ? color.green : na, linewidth=3, offset=emacloudleading, title="Long Leading EMA1")
malongline2 = plot(ema2 ? malong2 : na, color=showLine ? color.green : na, linewidth=3, offset=emacloudleading, title="Long Leading EMA2")
malongline3 = plot(ema3 ? malong3 : na, color=showLine ? color.green : na, linewidth=3, offset=emacloudleading, title="Long Leading EMA3")
malongline4 = plot(ema4 ? malong4 : na, color=showLine ? color.green : na, linewidth=3, offset=emacloudleading, title="Long Leading EMA4")
malongline5 = plot(ema5 ? malong5 : na, color=showLine ? color.green : na, linewidth=3, offset=emacloudleading, title="Long Leading EMA5")

fill(mashortline1, malongline1, color=color.new(cloudcolour1, 45), title="MA Cloud1")
fill(mashortline2, malongline2, color=color.new(cloudcolour2, 65), title="MA Cloud2")
fill(mashortline3, malongline3, color=color.new(cloudcolour3, 70), title="MA Cloud3")
fill(mashortline4, malongline4, color=color.new(cloudcolour4, 65), title="MA Cloud4")
fill(mashortline5, malongline5, color=color.new(cloudcolour5, 65), title="MA Cloud5")
```
