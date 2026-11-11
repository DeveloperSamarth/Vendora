from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(page_title="VENDORA", page_icon="🥤", layout="centered")
st.markdown(
    "<style>.block-container{padding-top:2rem;max-width:860px}"
    "div[data-testid='stMetricValue']{font-size:1.7rem}</style>",
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

top = st.columns([5, 1], vertical_alignment="center")
top[0].title("VENDORA")
if top[1].button("Refresh", help="Reload the latest data from the machine"):
    st.cache_data.clear()
    st.rerun()

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
            hovertemplate="%{x}: %{y} sales<extra></extra>",
        )
    )
    fig.update_yaxes(dtick=1 if max(values) <= 6 else None)
    show(style(fig, 230), key)
    return peak


def ranking_chart(frame, value, label_format, key, height=None):
    data = frame.sort_values(value, ascending=True)
    fig = go.Figure(
        go.Bar(
            x=data[value],
            y=data["product"],
            orientation="h",
            marker_color=BLUE,
            text=[label_format(row) for _, row in data.iterrows()],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x}<extra></extra>",
        )
    )
    fig.update_xaxes(visible=False, range=[0, float(data[value].max()) * 1.45 or 1])
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    show(style(fig, height or max(150, 52 * len(data))), key)


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
        st.markdown(line)
        if typical:
            st.progress(min(revenue / typical, 1.0))

        c1, c2, c3 = st.columns(3)
        c1.metric("Revenue", money(revenue))
        c2.metric("Sales", sales)
        c3.metric("Average order", money(revenue / sales) if sales else "–")

        with st.container(border=True):
            st.markdown("**Needs attention**")
            if alerts:
                for _, text in alerts:
                    st.markdown(text)
            else:
                st.markdown("✅ Nothing to do right now.")

        if today:
            st.markdown("**When are people buying today?**")
            peak = hourly_chart(with_hours(tx_for(today)), "today_hours")
            if peak is not None:
                st.caption(f"Busiest so far: {hour_label(peak)}.")
        if not liveprod.empty and liveprod["units"].sum() > 0:
            st.markdown("**What is selling?**")
            ranking_chart(
                liveprod[["product", "units"]],
                "units",
                lambda row: f"{int(row['units'])}",
                "today_products",
            )

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
        fig = go.Figure(
            go.Bar(
                x=series["date"],
                y=series["revenue"],
                marker_color=colors,
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

        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Revenue",
            money(revenue),
            None
            if previous_row is None
            else money(revenue - int(previous_row["revenue"])).replace("₹-", "-₹"),
        )
        c2.metric("Sales", sales, None if previous_row is None else sales - int(previous_row["sales"]))
        c3.metric("Average order", money(revenue / sales) if sales else "–")

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
