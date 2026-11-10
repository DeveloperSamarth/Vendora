from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import streamlit as st


IST = ZoneInfo("Asia/Kolkata")
SHEET_TABS = {
    "Daily": ["date", "machine", "total_sales", "total_revenue"],
    "ProductDaily": ["date", "machine", "product", "price", "units", "revenue", "stock_end"],
    "Transactions": ["date", "machine", "time", "product", "amount"],
    "Live": ["updated", "date", "machine", "total_sales", "total_revenue"],
    "LiveProducts": ["date", "machine", "product", "price", "units", "revenue", "stock"],
}

st.set_page_config(page_title="VENDORA Analytics", page_icon="🥤", layout="wide")
st.title("VENDORA Business Analytics")
st.caption("Machine runs offline-first; cloud data updates every 10 minutes and finalizes at midnight.")


def empty_frame(columns):
    return pd.DataFrame(columns=columns)


@st.cache_data(ttl=60)
def read_sheet_tab(sheet_id, tab):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab}"
    try:
        frame = pd.read_csv(url)
    except (OSError, ValueError, pd.errors.ParserError):
        return empty_frame(SHEET_TABS[tab])
    return frame.reindex(columns=SHEET_TABS[tab], fill_value=pd.NA)


def normalize(data):
    for name in ("Daily", "ProductDaily", "Live", "LiveProducts"):
        data[name]["date"] = pd.to_datetime(data[name]["date"], errors="coerce").dt.date
    data["Live"]["updated"] = pd.to_datetime(data["Live"]["updated"], errors="coerce")
    data["Transactions"]["date"] = pd.to_datetime(data["Transactions"]["date"], errors="coerce").dt.date
    data["Transactions"]["time"] = pd.to_datetime(data["Transactions"]["time"], errors="coerce")
    for name in ("Daily", "ProductDaily", "Live", "LiveProducts"):
        for column in ("total_sales", "total_revenue", "price", "units", "revenue", "stock_end", "stock"):
            if column in data[name]:
                data[name][column] = pd.to_numeric(data[name][column], errors="coerce").fillna(0)
    data["Transactions"]["amount"] = pd.to_numeric(data["Transactions"]["amount"], errors="coerce").fillna(0)
    return data


def show_empty():
    st.info("Waiting for machine data")


def machine_options(*frames):
    values = set()
    for frame in frames:
        if "machine" in frame and not frame.empty:
            values.update(frame["machine"].dropna().astype(str))
    return sorted(values)


try:
    sheet_id = st.secrets["1YFiLW-iSre378B0dXzDpiq9sC4JhnK6KLpTkqbKxAOY"]
except (FileNotFoundError, KeyError):
    sheet_id = ""
data = {tab: read_sheet_tab(sheet_id, tab) for tab in SHEET_TABS} if sheet_id else {
    tab: empty_frame(columns) for tab, columns in SHEET_TABS.items()
}
data = normalize(data)

today = datetime.now(IST).date()
today_tab, history_tab, hourly_tab, restock_tab, data_tab = st.tabs(
    ["Today", "History", "Hourly patterns", "Restock planner", "Data"]
)

with today_tab:
    live = data["Live"]
    live_products = data["LiveProducts"]
    if live.empty:
        show_empty()
    else:
        latest = live.sort_values("updated").iloc[-1]
        sales = int(latest["total_sales"])
        revenue = float(latest["total_revenue"])
        product_units = live_products.groupby("product", as_index=False)["units"].sum()
        top = product_units.loc[product_units["units"].idxmax(), "product"] if not product_units.empty else "—"
        updated = latest["updated"]
        updated_text = updated.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(updated) else "unknown"
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Sales", sales)
        c2.metric("Revenue (Rs)", f"{revenue:,.0f}")
        c3.metric("Avg order (Rs)", f"{revenue / sales:,.1f}" if sales else "0.0")
        c4.metric("Top product", top)
        c5.metric("Last updated", updated_text)
        if not product_units.empty:
            st.plotly_chart(px.bar(product_units, x="product", y="units", text="units",
                                   title="Units by product"), use_container_width=True)
        if not live_products.empty:
            stock = live_products[["product", "stock", "units", "revenue"]].copy()
            stock["Warning"] = stock["stock"].apply(
                lambda value: "RED" if value <= 2 else ("AMBER" if value <= 5 else "")
            )
            st.subheader("Current stock")
            st.dataframe(stock, use_container_width=True, hide_index=True)
            st.caption("Stock warnings: RED is 2 or fewer; AMBER is 5 or fewer.")
    if st.button("Refresh cloud data", key="today_refresh"):
        st.cache_data.clear()
        st.rerun()
    if hasattr(st, "autorefresh"):
        st.autorefresh(interval=60_000, key="today_auto_refresh")

with history_tab:
    daily = data["Daily"].copy()
    live = data["Live"].copy()
    if not daily.empty and not live.empty:
        live_rows = live.rename(columns={"total_sales": "total_sales", "total_revenue": "total_revenue"})
        daily = pd.concat([daily, live_rows[daily.columns]], ignore_index=True)
        daily = daily.sort_values("date").drop_duplicates(["date", "machine"], keep="last")
    if daily.empty:
        show_empty()
    else:
        machines = machine_options(daily)
        selected_machine = st.selectbox("Machine", ["All"] + machines)
        min_day, max_day = min(daily["date"]), max(daily["date"])
        selected_range = st.date_input("Date range", value=(min_day, max_day), min_value=min_day, max_value=max_day)
        if isinstance(selected_range, tuple) and len(selected_range) == 2:
            start_day, end_day = selected_range
        else:
            start_day = end_day = selected_range
        filtered = daily[(daily["date"] >= start_day) & (daily["date"] <= end_day)]
        if selected_machine != "All":
            filtered = filtered[filtered["machine"] == selected_machine]
        if filtered.empty:
            st.info("No data matches those filters.")
        else:
            d1, d2 = st.columns(2)
            d1.plotly_chart(px.line(filtered, x="date", y="total_revenue", markers=True,
                                    title="Daily revenue"), use_container_width=True)
            d2.plotly_chart(px.line(filtered, x="date", y="total_sales", markers=True,
                                    title="Daily sales"), use_container_width=True)
            product_daily = data["ProductDaily"]
            product_daily = product_daily[(product_daily["date"] >= start_day) & (product_daily["date"] <= end_day)]
            if selected_machine != "All":
                product_daily = product_daily[product_daily["machine"] == selected_machine]
            if not product_daily.empty:
                by_product = product_daily.groupby("product", as_index=False).agg(
                    units=("units", "sum"), revenue=("revenue", "sum")
                )
                h1, h2 = st.columns(2)
                h1.plotly_chart(px.bar(by_product, x="product", y="units", title="Units by product"),
                                use_container_width=True)
                h2.plotly_chart(px.pie(by_product, names="product", values="revenue",
                                       title="Revenue share", hole=0.4), use_container_width=True)
            best = filtered.loc[filtered["total_revenue"].idxmax()]
            worst = filtered.loc[filtered["total_revenue"].idxmin()]
            st.write(f"**Best day:** {best['date']} (Rs {best['total_revenue']:,.0f})  |  "
                     f"**Worst day:** {worst['date']} (Rs {worst['total_revenue']:,.0f})")
            series = filtered.sort_values("date").copy()
            series["7-day moving average"] = series["total_revenue"].rolling(7, min_periods=1).mean()
            st.plotly_chart(px.line(series, x="date", y=["total_revenue", "7-day moving average"],
                                    title="Revenue and 7-day moving average"), use_container_width=True)
            ordered = daily.sort_values("date")
            if len(ordered) >= 8:
                recent = ordered.tail(7)["total_revenue"].sum()
                previous = ordered.iloc[-14:-7]["total_revenue"].sum()
                change = ((recent - previous) / previous * 100) if previous else 0
                st.metric("Week-over-week revenue", f"{change:+.1f}%")

with hourly_tab:
    tx = data["Transactions"]
    if tx.empty or tx["time"].isna().all():
        show_empty()
    else:
        tx = tx.dropna(subset=["time"]).copy()
        tx["weekday"] = tx["time"].dt.day_name()
        tx["hour"] = tx["time"].dt.hour
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        heat = tx.pivot_table(index="weekday", columns="hour", values="amount", aggfunc="count",
                              fill_value=0).reindex(weekdays, fill_value=0)
        st.plotly_chart(px.imshow(heat, labels={"x": "Hour", "y": "Weekday", "color": "Sales"},
                                  aspect="auto", title="Sales by weekday and hour"),
                        use_container_width=True)
        by_hour = tx.groupby("hour").size()
        peak_hour = int(by_hour.idxmax())
        st.metric("Peak hour", f"{peak_hour:02d}:00")
        st.info(f"Recommendation: refill before {peak_hour:02d}:00.")

with restock_tab:
    product_daily = data["ProductDaily"]
    live_products = data["LiveProducts"]
    if product_daily.empty or live_products.empty:
        show_empty()
    else:
        recent_start = today - timedelta(days=6)
        recent = product_daily[product_daily["date"] >= recent_start]
        avg = recent.groupby("product", as_index=False)["units"].mean().rename(columns={"units": "avg_units_per_day"})
        plan = live_products.groupby("product", as_index=False)["stock"].last().merge(avg, on="product", how="left")
        plan["avg_units_per_day"] = plan["avg_units_per_day"].fillna(0)
        plan["days_of_stock_left"] = plan.apply(
            lambda row: row["stock"] / row["avg_units_per_day"] if row["avg_units_per_day"] else float("inf"),
            axis=1,
        )
        plan["Flag"] = plan["days_of_stock_left"].apply(lambda days: "RESTOCK" if days < 2 else "")
        st.dataframe(plan.sort_values("days_of_stock_left"), use_container_width=True, hide_index=True)

with data_tab:
    for tab_name, frame in data.items():
        with st.expander(tab_name, expanded=tab_name == "Live"):
            if frame.empty:
                st.info("Waiting for machine data")
            else:
                st.dataframe(frame, use_container_width=True, hide_index=True)
                st.download_button(
                    f"Download {tab_name}.csv", frame.to_csv(index=False), f"vendora_{tab_name.lower()}.csv",
                    mime="text/csv", key=f"download_{tab_name}",
                )
