from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(page_title="VENDORA", page_icon="🥤", layout="centered")
st.markdown(
    """
    <style>
    :root {
      --navy: #0f2441;
      --blue: #2a78d6;
      --green: #1a9e6a;
      --amber: #eda100;
      --red: #e34948;
      --card: rgba(255,255,255,.92);
      --ink: #172235;
      --muted: #68758a;
      --line: rgba(104,117,138,.18);
    }
    .block-container { max-width: 860px; padding-top: 1.5rem; }
    .vendora-hero {
      align-items: center; background: var(--navy); border-radius: 16px;
      box-shadow: 0 12px 30px rgba(15,36,65,.2); display: flex;
      justify-content: space-between; margin-bottom: 1.25rem; padding: 1rem 1.2rem;
    }
    .vendora-title { color: white; font-size: 1.8rem; font-weight: 800; letter-spacing: .08em; }
    .status-chip { align-items: center; border: 1px solid rgba(255,255,255,.22);
      border-radius: 999px; color: white; display: flex; font-size: .78rem;
      gap: .45rem; padding: .35rem .7rem; }
    .status-dot { background: var(--amber); border-radius: 50%; height: 8px; width: 8px; }
    .status-live .status-dot { animation: pulse 2s infinite; background: var(--green); }
    .headline, .metric-card, .attention-box { animation: slide-up .55s both; }
    .metric-card { background: var(--card); border-radius: 14px; box-shadow: 0 5px 18px rgba(15,36,65,.1);
      color: var(--ink); min-height: 82px; padding: .85rem 1rem; transition: transform .2s, box-shadow .2s; }
    .metric-grid { display: grid; gap: .75rem; grid-template-columns: repeat(3, 1fr); margin: .9rem 0 1rem; }
    .metric-card:hover { box-shadow: 0 9px 24px rgba(15,36,65,.16); transform: translateY(-2px); }
    .metric-card:nth-child(1) { border-top: 4px solid var(--blue); }
    .metric-card:nth-child(2) { border-top: 4px solid var(--green); }
    .metric-card:nth-child(3) { border-top: 4px solid var(--amber); }
    .metric-label { color: var(--muted); font-size: .78rem; font-weight: 700; }
    .metric-value { font-size: 1.7rem; font-weight: 800; margin-top: .25rem; }
    .attention-box { border-radius: 14px; margin: 1rem 0; padding: .85rem 1rem; }
    .attention-urgent { background: rgba(227,73,72,.12); border: 1px solid rgba(227,73,72,.3); }
    .attention-watch { background: rgba(237,161,0,.13); border: 1px solid rgba(237,161,0,.35); }
    .attention-good { background: rgba(26,158,106,.12); border: 1px solid rgba(26,158,106,.3); }
    [data-testid="stProgress"] > div > div > div { background: var(--blue); transition: width .7s ease; }
    @keyframes slide-up { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(26,158,106,.65); } 50% { box-shadow: 0 0 0 5px rgba(26,158,106,0); } }
    @media (max-width: 640px) {
      .vendora-hero { padding: .85rem 1rem; }
      .metric-grid { grid-template-columns: 1fr; }
      .metric-card { margin-bottom: .65rem; }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; scroll-behavior: auto !important; transition-duration: .01ms !important; }
    }
    @media (prefers-color-scheme: dark) {
      :root { --card: rgba(30,43,61,.96); --ink: #edf3fb; --muted: #aebbd0; --line: rgba(237,243,251,.16); }
      .metric-card { box-shadow: 0 5px 18px rgba(0,0,0,.24); }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

BLUE, BLUE_LIGHT, GRAY = "#2a78d6", "#9dc0ee", "#8d8c87"
TABS = ["Live", "LiveProducts", "Daily", "ProductDaily", "Transactions", "TodayTransactions"]


# ------------------------------------------------------------------ data
def get_sheet_id():
    try:
        sid = st.secrets["SHEET_ID"]
    except Exception:
        sid = ""
    if not sid:
        sid = st.sidebar.text_input("Google Sheet ID")
    return str(sid).strip()


SID = get_sheet_id()


@st.cache_data(ttl=30, show_spinner=False)
def fetch(sid, tab):
    df = pd.read_csv(
        f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&sheet={tab}"
    )
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


errors = {}


def get(tab):
    if not SID:
        return pd.DataFrame()
    try:
        return fetch(SID, tab)
    except Exception as error:
        errors[tab] = str(error)
        return pd.DataFrame()


def to_dt(series):
    try:
        return pd.to_datetime(series, errors="coerce", format="mixed")
    except Exception:
        return pd.to_datetime(series, errors="coerce")


def num(df, columns):
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
    return df


def money(value):
    return f"₹{value:,.0f}"


def hour_label(hour):
    return f"{hour % 12 or 12}{'am' if hour < 12 else 'pm'}"


live, liveprod = get("Live"), get("LiveProducts")
daily, prodaily = get("Daily"), get("ProductDaily")
tx_done, tx_today = get("Transactions"), get("TodayTransactions")

if not SID:
    st.warning(
        "Add SHEET_ID in the app's Secrets (or type it in the sidebar) to connect your Google Sheet."
    )
    st.stop()

live = num(live, ["total_sales", "total_revenue"])
liveprod = num(liveprod, ["price", "units", "revenue", "stock"])
daily = num(daily, ["total_sales", "total_revenue"])
prodaily = num(prodaily, ["price", "units", "revenue", "stock_end"])

for frame in (daily, prodaily):
    if "date" in frame.columns:
        frame["date"] = to_dt(frame["date"])

# totals are cumulative within a day, so the row with the most sales is the latest snapshot
if not daily.empty and {"date", "machine"} <= set(daily.columns):
    daily = (
        daily.sort_values("total_sales")
        .drop_duplicates(subset=["date", "machine"], keep="last")
    )
if not prodaily.empty and {"date", "machine", "product"} <= set(prodaily.columns):
    prodaily = (
        prodaily.sort_values(["units", "revenue"])
        .drop_duplicates(subset=["date", "machine", "product"], keep="last")
    )

# Daily totals across machines, one row per date. Today's row is a running total.
if not daily.empty and "date" in daily.columns:
    daily_totals = (
        daily.dropna(subset=["date"])
        .assign(date=lambda frame: frame["date"].dt.normalize())
        .groupby("date")[["total_sales", "total_revenue"]]
        .sum()
        .reset_index()
    )
    daily_totals.columns = ["date", "sales", "revenue"]
else:
    daily_totals = pd.DataFrame(columns=["date", "sales", "revenue"])

today = None
if not live.empty and "date" in live.columns:
    timestamps = to_dt(live["date"]).dropna()
    today = timestamps.iloc[0].date() if len(timestamps) else None
if today is None and not daily_totals.empty:
    today = daily_totals["date"].max().date()

history = daily_totals[daily_totals["date"].dt.date < today] if today else daily_totals
typical = history.tail(7)["revenue"].mean() if len(history) else None


def tx_for(day):
    for source in (tx_done, tx_today):
        if not source.empty and "date" in source.columns:
            matching = source[to_dt(source["date"]).dt.date == day]
            if not matching.empty:
                return matching.copy()
    return pd.DataFrame()


def with_hours(frame):
    if frame.empty or "time" not in frame.columns:
        return pd.DataFrame()
    result = frame.copy()
    result["time"] = to_dt(result["time"])
    result = result.dropna(subset=["time"])
    result["hour"] = result["time"].dt.hour
    if "amount" in result.columns:
        result["amount"] = pd.to_numeric(result["amount"], errors="coerce").fillna(0)
    return result


def units_per_day():
    if (
        prodaily.empty
        or "product" not in prodaily.columns
        or "date" not in prodaily.columns
    ):
        return {}
    product_daily = prodaily[prodaily["date"].dt.date < today] if today else prodaily
    dates = sorted(product_daily["date"].dropna().unique())[-7:]
    return (
        product_daily[product_daily["date"].isin(dates)]
        .groupby("product")["units"]
        .mean()
        .to_dict()
    )


# ------------------------------------------------------------------ chart helpers
def style(fig, height=260):
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=6, b=0),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        bargap=0.35,
        font=dict(size=13),
        transition={"duration": 600, "easing": "cubic-in-out"},
    )
    fig.update_xaxes(showgrid=False, zeroline=False, title=None)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.18)", zeroline=False, title=None)
    return fig


def show(fig, key):
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=key)


def hourly_chart(frame, key):
    if frame.empty:
        st.caption("Hour-by-hour detail appears once sales are recorded with a clock time.")
        return None
    counts = frame.groupby("hour").size()
    low, high = min(int(counts.index.min()), 8), max(int(counts.index.max()), 20)
    hours = list(range(low, high + 1))
    values = [int(counts.get(hour, 0)) for hour in hours]
    peak = hours[values.index(max(values))]
    fig = go.Figure(
        go.Bar(
            x=[hour_label(hour) for hour in hours],
            y=values,
            marker_color=[BLUE if hour == peak else BLUE_LIGHT for hour in hours],
            marker_line=dict(
                color=[BLUE if hour == peak else "rgba(42,120,214,.35)" for hour in hours],
                width=[3 if hour == peak else 1 for hour in hours],
            ),
            hovertemplate="%{x}: %{y} sales<extra></extra>",
        )
    )
    fig.update_yaxes(dtick=1 if max(values) <= 6 else None)
    show(style(fig, 230), key)
    return peak


def ranking_chart(frame, value, label_format, key, height=None):
    data = frame.sort_values(value, ascending=True)
    if "stock" in data.columns:
        outline = [
            "#e34948" if stock <= 2 else "#eda100" if stock <= 5 else "#1a9e6a"
            for stock in data["stock"]
        ]
    else:
        outline = ["#1a9e6a"] * len(data)
    fig = go.Figure(
        go.Bar(
            x=data[value],
            y=data["product"],
            orientation="h",
            marker_color=BLUE,
            marker_line=dict(color=outline, width=2),
            text=[label_format(row) for _, row in data.iterrows()],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x}<extra></extra>",
        )
    )
    fig.update_xaxes(visible=False, range=[0, float(data[value].max()) * 1.45 or 1])
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    show(style(fig, height or max(150, 52 * len(data))), key)


def sales_revenue_chart(frame, key):
    if frame.empty:
        return
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=frame["date"],
            y=frame["revenue"],
            mode="lines+markers",
            name="Revenue",
            line=dict(color=BLUE, width=3),
            marker=dict(color=BLUE, size=7),
            hovertemplate="%{x|%a %d %b}: ₹%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=frame["date"],
            y=frame["sales"],
            mode="lines+markers",
            name="Sales",
            yaxis="y2",
            line=dict(color="#1a9e6a", width=2),
            marker=dict(color="#1a9e6a", size=6),
            hovertemplate="%{x|%a %d %b}: %{y} sales<extra></extra>",
        )
    )
    fig.update_layout(
        yaxis=dict(title="Revenue (₹)", showgrid=True, gridcolor="rgba(128,128,128,.18)"),
        yaxis2=dict(title="Sales", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", y=1.12, x=0),
    )
    styled = style(fig, 280)
    styled.update_layout(showlegend=True)
    show(styled, key)


def weekday_chart(frame, key):
    if frame.empty:
        return
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    grouped = (
        frame.assign(weekday=frame["date"].dt.day_name())
        .groupby("weekday")["revenue"]
        .mean()
        .reindex(order)
        .dropna()
        .reset_index()
    )
    if grouped.empty:
        return
    best = grouped["revenue"].idxmax()
    fig = go.Figure(
        go.Bar(
            x=grouped["weekday"],
            y=grouped["revenue"],
            marker_color=[("#1a9e6a" if index == best else BLUE) for index in grouped.index],
            hovertemplate="%{x}: ₹%{y:,.0f} average<extra></extra>",
        )
    )
    show(style(fig, 240), key)


def inventory_chart(frame, key):
    if frame.empty or "product" not in frame.columns or "stock" not in frame.columns:
        return
    data = frame.sort_values("stock", ascending=True)
    colors = [
        "#e34948" if stock <= 2 else "#eda100" if stock <= 5 else "#1a9e6a"
        for stock in data["stock"]
    ]
    fig = go.Figure(
        go.Bar(
            x=data["stock"],
            y=data["product"],
            orientation="h",
            marker_color=colors,
            hovertemplate="%{y}: %{x} units remaining<extra></extra>",
        )
    )
    fig.update_xaxes(dtick=1)
    show(style(fig, max(150, 48 * len(data))), key)


def product_mix_chart(frame, key):
    if frame.empty or frame["revenue"].sum() <= 0:
        return
    data = frame.groupby("product", as_index=False)["revenue"].sum()
    fig = go.Figure(
        go.Pie(
            labels=data["product"],
            values=data["revenue"],
            hole=0.58,
            textinfo="label+percent",
            hovertemplate="%{label}: ₹%{value:,.0f} (%{percent})<extra></extra>",
            marker=dict(colors=[BLUE, "#1a9e6a", "#eda100", "#e34948"]),
        )
    )
    fig.update_layout(showlegend=False)
    show(style(fig, 280), key)


def freshness():
    if live.empty or "updated" not in live.columns:
        return "No update received yet"
    updates = to_dt(live["updated"]).dropna()
    if updates.empty:
        return f"Last update: {live['updated'].iloc[0]}"
    updated = updates.iloc[0]
    now = datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None)
    minutes = (now - updated.to_pydatetime()).total_seconds() / 60
    stamp = updated.strftime("%d %b, %I:%M %p")
    if 0 <= minutes <= 15:
        return f"🟢 Live · updated {max(int(minutes), 0)} min ago"
    if 15 < minutes < 24 * 60:
        return f"🟠 No update for {int(minutes)} min (machine may be offline) · last at {stamp}"
    return f"Last update: {stamp}"


status_live = False
if not live.empty and "updated" in live.columns:
    update_times = to_dt(live["updated"]).dropna()
    if not update_times.empty:
        status_live = (
            datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None)
            - update_times.iloc[0].to_pydatetime()
        ).total_seconds() <= 15 * 60

status_class = "status-live" if status_live else "status-stale"
status_label = "Live" if status_live else "No update"
st.markdown(
    f"<div class='vendora-hero'><div class='vendora-title'>VENDORA</div>"
    f"<div class='status-chip {status_class}'><span class='status-dot'></span>{status_label}</div></div>",
    unsafe_allow_html=True,
)
if st.button("Refresh", help="Reload the latest data from the machine"):
    st.cache_data.clear()
    st.rerun()


def metric_cards(items):
    cards = "".join(
        f"<div class='metric-card' style='animation-delay:{index * .08:.2f}s'>"
        f"<div class='metric-label'>{label}</div><div class='metric-value'>{value}</div></div>"
        for index, (label, value) in enumerate(items)
    )
    st.markdown(f"<div class='metric-grid'>{cards}</div>", unsafe_allow_html=True)


def attention_box(alerts):
    if not alerts:
        tone, content = "attention-good", "✅ Nothing to do right now."
    elif alerts[0][0] == 0:
        tone = "attention-urgent"
        content = "<br>".join(
            text.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
            for _, text in alerts
        )
    else:
        tone = "attention-watch"
        content = "<br>".join(
            text.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
            for _, text in alerts
        )
    st.markdown(
        f"<div class='attention-box {tone}'><strong>Needs attention</strong>"
        f"<div style='margin-top:.45rem'>{content}</div></div>",
        unsafe_allow_html=True,
    )


tab_today, tab_trends, tab_day = st.tabs(["Today", "Trends", "Day report"])

# ================================================================== TODAY
with tab_today:
    if live.empty or "total_sales" not in live.columns:
        st.info(
            "Waiting for the machine's first upload. It sends data about once a minute when it has internet."
        )
    else:
        row = live.iloc[0]
        sales, revenue = int(row["total_sales"]), int(row["total_revenue"])
        st.caption(freshness())

        stock_now = {}
        if not liveprod.empty and "product" in liveprod.columns:
            stock_now = liveprod.set_index("product")["stock"].to_dict()
        rate = units_per_day()
        alerts = []
        for product, stock in stock_now.items():
            daily_rate = rate.get(product)
            days_left = stock / daily_rate if daily_rate and daily_rate > 0 else None
            if stock <= 2 or (days_left is not None and days_left < 1):
                detail = (
                    f" · sells about {daily_rate:.0f}/day → refill today"
                    if daily_rate
                    else " → refill today"
                )
                alerts.append((0, f"🔴 **{product}**: {int(stock)} left{detail}"))
            elif stock <= 5 or (days_left is not None and days_left < 2):
                detail = f" · about {days_left:.1f} days of stock" if days_left else " → refill soon"
                alerts.append((1, f"🟠 **{product}**: {int(stock)} left{detail}"))
        alerts.sort(key=lambda alert: alert[0])

        best = None
        if not liveprod.empty and liveprod["units"].sum() > 0:
            best = liveprod.sort_values("units", ascending=False).iloc[0]["product"]

        line = f"**{money(revenue)} from {sales} sale{'s' if sales != 1 else ''} so far today.**"
        if typical:
            line += f" That is {revenue / typical:.0%} of a typical day ({money(typical)})."
        if best:
            line += f" **{best}** is selling best."
        line += (
            f" **{len(alerts)} product{'s' if len(alerts) != 1 else ''} need"
            f"{'s' if len(alerts) == 1 else ''} a refill.**"
            if alerts
            else " Stock looks fine."
        )
        st.markdown(f"<div class='headline'>{line}</div>", unsafe_allow_html=True)
        if typical:
            st.progress(min(revenue / typical, 1.0))

        metric_cards(
            [
                ("Revenue", money(revenue)),
                ("Sales", sales),
                ("Average order", money(revenue / sales) if sales else "–"),
            ]
        )
        attention_box(alerts)

        if today:
            st.markdown("**When are people buying today?**")
            peak = hourly_chart(with_hours(tx_for(today)), "today_hours")
            if peak is not None:
                st.caption(f"Busiest so far: {hour_label(peak)}.")
        if not liveprod.empty and liveprod["units"].sum() > 0:
            st.markdown("**What is selling?**")
            ranking_frame = liveprod[["product", "units"]].copy()
            if "stock" in liveprod.columns:
                ranking_frame["stock"] = liveprod["stock"]
            products_left, stock_left = st.columns(2)
            with products_left:
                ranking_chart(
                    ranking_frame,
                    "units",
                    lambda row: f"{int(row['units'])}",
                    "today_products",
                )
            with stock_left:
                st.markdown("**Stock remaining**")
                inventory_chart(liveprod, "today_stock")

# ================================================================== TRENDS
with tab_trends:
    if len(daily_totals) < 2:
        st.info("Trends need at least two days of data. They will appear automatically as days are recorded.")
    else:
        view = st.radio(
            "View",
            ["Daily", "Weekly", "Monthly"],
            horizontal=True,
            label_visibility="collapsed",
        )
        last7, previous7 = history.tail(7), history.iloc[-14:-7]
        messages = []
        if len(last7) >= 2:
            total = last7["revenue"].sum()
            if len(previous7) >= 3:
                change = (
                    (total - previous7["revenue"].sum()) / previous7["revenue"].sum() * 100
                    if previous7["revenue"].sum()
                    else 0
                )
                messages.append(
                    f"**Last {len(last7)} days: {money(total)}**, "
                    f"{'up' if change >= 0 else 'down'} {abs(change):.0f}% "
                    f"on the {len(previous7)} days before."
                )
            else:
                messages.append(
                    f"**Last {len(last7)} days: {money(total)}**, "
                    f"about {money(last7['revenue'].mean())} a day."
                )
        if len(history) >= 14:
            weekdays = history.assign(weekday=history["date"].dt.day_name()).groupby("weekday")[
                "revenue"
            ].mean()
            messages.append(
                f"Best day of the week: **{weekdays.idxmax()}** "
                f"(about {money(weekdays.max())})."
            )
        all_transactions = (
            with_hours(pd.concat([tx_done, tx_today], ignore_index=True))
            if (not tx_done.empty or not tx_today.empty)
            else pd.DataFrame()
        )
        if len(all_transactions) >= 20:
            hourly_counts = all_transactions.groupby("hour").size()
            messages.append(
                f"Busiest hour: **{hour_label(int(hourly_counts.idxmax()))}** "
                f"({hourly_counts.max() / hourly_counts.sum():.0%} of sales)."
            )
        if messages:
            st.markdown(" ".join(messages))

        series = daily_totals.set_index("date")
        if view == "Daily":
            series = series.tail(30)
            title, since = "Revenue per day", series.index.min()
        elif view == "Weekly":
            series = series.resample("W-MON", label="left", closed="left")[
                ["sales", "revenue"]
            ].sum().tail(12)
            title, since = "Revenue per week", series.index.min()
        else:
            series = series.resample("MS")[["sales", "revenue"]].sum().tail(12)
            title, since = "Revenue per month", series.index.min()
        series = series.reset_index()
        st.markdown(f"**{title}**")
        colors = [
            BLUE_LIGHT if (today and view == "Daily" and date.date() == today) else BLUE
            for date in series["date"]
        ]
        highest_index = series["revenue"].idxmax()
        fig = go.Figure(
            go.Bar(
                x=series["date"],
                y=series["revenue"],
                marker_color=colors,
                marker_line=dict(
                    color=[
                        "rgba(42,120,214,.9)" if index == highest_index else "rgba(42,120,214,.3)"
                        for index in series.index
                    ],
                    width=[3 if index == highest_index else 1 for index in series.index],
                ),
                hovertemplate="%{x|%a %d %b}: ₹%{y:,.0f}<extra></extra>",
            )
        )
        if view == "Daily" and len(series) >= 4:
            moving_average = (
                daily_totals.set_index("date")["revenue"]
                .rolling(7, min_periods=3)
                .mean()
                .reindex(series["date"])
            )
            fig.add_trace(
                go.Scatter(
                    x=series["date"],
                    y=moving_average.values,
                    mode="lines",
                    line=dict(color=GRAY, width=2),
                    hovertemplate="7-day average: ₹%{y:,.0f}<extra></extra>",
                )
            )
        show(style(fig, 260), "trend_revenue")
        if view == "Daily" and today and today in set(series["date"].dt.date):
            st.caption("Lighter bar = today so far. Grey line = 7-day average.")

        st.markdown("**Sales and revenue together**")
        sales_revenue_chart(series, "trend_sales_revenue")
        if len(history) >= 3:
            st.markdown("**Average revenue by weekday**")
            weekday_chart(history, "trend_weekdays")

        if not prodaily.empty and "product" in prodaily.columns:
            product_totals = (
                prodaily[prodaily["date"] >= since]
                .groupby("product")[["units", "revenue"]]
                .sum()
                .reset_index()
            )
            if product_totals["revenue"].sum() > 0:
                st.markdown("**Which products earn the most?**")
                total_revenue = product_totals["revenue"].sum()
                ranking_chart(
                    product_totals,
                    "revenue",
                    lambda row: f"{money(row['revenue'])} · {row['revenue'] / total_revenue:.0%}",
                    "trend_products",
                )

# ================================================================== DAY REPORT
with tab_day:
    if daily_totals.empty:
        st.info("No days recorded yet.")
    else:
        days = sorted({date.date() for date in daily_totals["date"]}, reverse=True)
        day = st.selectbox(
            "Day",
            days,
            format_func=lambda value: value.strftime("%A, %d %b %Y"),
            label_visibility="collapsed",
        )
        row = daily_totals[daily_totals["date"].dt.date == day].iloc[0]
        sales, revenue = int(row["sales"]), int(row["revenue"])
        earlier = [date for date in days if date < day]
        previous_row = (
            daily_totals[daily_totals["date"].dt.date == earlier[0]].iloc[0]
            if (earlier and day != today)
            else None
        )
        transactions = tx_for(day)
        transaction_hours = with_hours(transactions)

        summary = f"**{money(revenue)} from {sales} sale{'s' if sales != 1 else ''}.**"
        if previous_row is not None:
            difference = revenue - int(previous_row["revenue"])
            summary += (
                f" That is {money(abs(difference))} "
                f"{'more' if difference >= 0 else 'less'} than {earlier[0].strftime('%d %b')}."
            )
        if day == today:
            summary += " The day is still in progress"
            summary += f" (a typical day is {money(typical)})." if typical else "."
        st.markdown(summary)

        metric_cards(
            [
                ("Revenue", money(revenue)),
                ("Sales", sales),
                ("Average order", money(revenue / sales) if sales else "–"),
            ]
        )

        product_day = (
            prodaily[prodaily["date"].dt.date == day]
            if "date" in prodaily.columns
            else pd.DataFrame()
        )
        if not product_day.empty and "product" in product_day.columns and product_day["units"].sum() > 0:
            product_table = (
                product_day.groupby("product")
                .agg(units=("units", "sum"), revenue=("revenue", "sum"), left=("stock_end", "last"))
                .reset_index()
            )
            product_table["share"] = product_table["revenue"] / product_table["revenue"].sum() * 100
            product_table = product_table.sort_values("units", ascending=False)
            st.markdown("**Products**")
            st.dataframe(
                product_table.rename(
                    columns={
                        "product": "Product",
                        "units": "Sold",
                        "revenue": "Revenue",
                        "left": "Left",
                        "share": "Share",
                    }
                ),
                width="stretch",
                hide_index=True,
                column_config={
                    "Revenue": st.column_config.NumberColumn(format="₹%d"),
                    "Share": st.column_config.ProgressColumn(
                        format="%.0f%%", min_value=0, max_value=100
                    ),
                },
            )
            st.markdown("**Revenue mix**")
            product_mix_chart(product_day, "day_product_mix")

        st.markdown("**When did people buy?**")
        peak = hourly_chart(transaction_hours, "day_hours")
        if peak is not None:
            st.caption(f"Busiest hour: {hour_label(peak)}.")
        if not transactions.empty:
            if len(transactions) < sales:
                st.caption(
                    f"Showing {len(transactions)} of {sales} sales "
                    "(the machine keeps the latest 100 per day). Totals above are complete."
                )
            with st.expander(f"All transactions ({len(transactions)})"):
                st.dataframe(transactions, width="stretch", hide_index=True)
                st.download_button(
                    "Download this day (CSV)",
                    transactions.to_csv(index=False),
                    f"vendora_{day}.csv",
                )


# ------------------------------------------------------------------ data check (kept out of the way)
with st.expander("Data check"):
    for tab, frame in zip(TABS, [live, liveprod, daily, prodaily, tx_done, tx_today]):
        st.write(
            f"**{tab}**: {len(frame)} rows"
            + (f" · error: {errors[tab]}" if tab in errors else "")
        )
    if errors:
        st.caption(
            "Errors usually mean the sheet is not shared as 'Anyone with the link: Viewer' "
            "or the Sheet ID is wrong."
        )
