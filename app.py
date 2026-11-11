import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="VENDORA Analytics", page_icon="🥤", layout="wide")
st.title("VENDORA Business Analytics")
st.caption("Cloud data updates about every minute and right after each sale. History is finalized at midnight (India time).")

TABS = ["Live", "LiveProducts", "Daily", "ProductDaily", "Transactions"]


def get_sheet_id():
    try:
        sid = st.secrets["SHEET_ID"]
    except Exception:
        sid = ""
    if not sid:
        sid = st.sidebar.text_input(
            "Google Sheet ID",
            help="Long text between /d/ and /edit in the sheet address",
        )
    return str(sid).strip()


SID = get_sheet_id()
if st.sidebar.button("Refresh cloud data"):
    st.cache_data.clear()
    st.rerun()


def url_for(tab):
    return f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={tab}"


@st.cache_data(ttl=30, show_spinner=False)
def fetch(sid, tab):
    df = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&sheet={tab}")
    df.columns = [str(column).strip().lower() for column in df.columns]
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


live = get("Live")
liveprod = get("LiveProducts")
daily = get("Daily")
prodaily = get("ProductDaily")
tx = get("Transactions")

if not SID:
    st.warning("Add SHEET_ID in Streamlit Secrets (or type it in the sidebar) to connect your Google Sheet.")
    st.stop()

if errors:
    for tab, error in errors.items():
        st.error(f"{tab}: {error}")
    st.caption("Check that the sheet is shared as 'Anyone with the link: Viewer' and that SHEET_ID is correct.")

live = num(live, ["total_sales", "total_revenue"])
liveprod = num(liveprod, ["price", "units", "revenue", "stock"])
daily = num(daily, ["total_sales", "total_revenue"])
prodaily = num(prodaily, ["price", "units", "revenue", "stock_end"])
if "date" in daily.columns:
    daily["date"] = to_dt(daily["date"])
if "date" in prodaily.columns:
    prodaily["date"] = to_dt(prodaily["date"])

t_today, t_hist, t_hour, t_restock, t_data = st.tabs(
    ["Today", "History", "Hourly patterns", "Restock planner", "Data"]
)

with t_today:
    if live.empty or "total_sales" not in live.columns:
        st.info("Waiting for machine data. The machine uploads about once a minute when it has internet.")
    else:
        row = live.iloc[0]
        sales, revenue = int(row["total_sales"]), int(row["total_revenue"])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sales today", sales)
        c2.metric("Revenue today (Rs)", revenue)
        c3.metric("Average order (Rs)", round(revenue / sales, 1) if sales else 0)
        c4.metric("Last update", str(row.get("updated", "n/a")))
        if not liveprod.empty and "product" in liveprod.columns:
            a, b = st.columns(2)
            a.plotly_chart(
                px.bar(liveprod, x="product", y="units", text="units", title="Units sold today"),
                width="stretch",
            )
            b.plotly_chart(
                px.pie(liveprod, names="product", values="revenue", title="Revenue share today", hole=0.45),
                width="stretch",
            )
            show = liveprod[["product", "price", "units", "revenue", "stock"]].copy()
            show["status"] = show["stock"].apply(
                lambda stock: "URGENT" if stock <= 2 else ("Restock soon" if stock <= 5 else "OK")
            )
            st.subheader("Stock")
            st.dataframe(show, width="stretch", hide_index=True)

with t_hist:
    if daily.empty or "date" not in daily.columns:
        st.info("No history yet. The Daily tab fills as days are recorded (today's row updates live).")
    else:
        view = st.radio("Group by", ["Daily", "Weekly", "Monthly"], horizontal=True)
        freq = {"Daily": "D", "Weekly": "W", "Monthly": "MS"}[view]
        grouped = (
            daily.dropna(subset=["date"])
            .groupby(pd.Grouper(key="date", freq=freq))[["total_sales", "total_revenue"]]
            .sum()
            .reset_index()
        )
        grouped = (
            grouped[(grouped["total_sales"] > 0) | (grouped["total_revenue"] > 0)]
            if len(grouped) > 1
            else grouped
        )
        if len(grouped) >= 2:
            current, previous = grouped.iloc[-1], grouped.iloc[-2]
            delta = (
                (current["total_revenue"] - previous["total_revenue"]) / previous["total_revenue"] * 100
                if previous["total_revenue"]
                else 0
            )
            st.metric(f"Latest {view.lower()} revenue (Rs)", int(current["total_revenue"]), f"{delta:.1f}% vs previous")
        x, y = st.columns(2)
        x.plotly_chart(px.bar(grouped, x="date", y="total_revenue", title=f"{view} revenue (Rs)"), width="stretch")
        y.plotly_chart(px.bar(grouped, x="date", y="total_sales", title=f"{view} sales (units)"), width="stretch")
        if not prodaily.empty and "product" in prodaily.columns:
            product_grouped = (
                prodaily.dropna(subset=["date"])
                .groupby([pd.Grouper(key="date", freq=freq), "product"])[["units", "revenue"]]
                .sum()
                .reset_index()
            )
            st.plotly_chart(
                px.bar(
                    product_grouped,
                    x="date",
                    y="units",
                    color="product",
                    barmode="group",
                    title=f"Units by product ({view.lower()})",
                ),
                width="stretch",
            )
            best = product_grouped.groupby("product")["units"].sum().sort_values(ascending=False)
            st.write(
                f"**Best seller:** {best.index[0]} ({int(best.iloc[0])} units) | "
                f"**Slowest:** {best.index[-1]} ({int(best.iloc[-1])} units)"
            )

with t_hour:
    if tx.empty or "time" not in tx.columns:
        st.info("Hourly patterns use the Transactions tab, which is filled when each day closes at midnight.")
    else:
        transactions = tx.copy()
        transactions["time"] = to_dt(transactions["time"])
        transactions = transactions.dropna(subset=["time"])
        if transactions.empty:
            st.info("No transactions with a time yet.")
        else:
            transactions["hour"] = transactions["time"].dt.hour
            transactions["weekday"] = transactions["time"].dt.day_name()
            peak = int(transactions["hour"].value_counts().idxmax())
            st.metric("Peak hour", f"{peak}:00")
            st.write(f"Refill before **{peak}:00** to avoid running out at the busiest time.")
            hours = transactions.groupby("hour").size().reset_index(name="sales")
            st.plotly_chart(px.bar(hours, x="hour", y="sales", title="Sales by hour"), width="stretch")
            weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            heatmap = (
                transactions.pivot_table(
                    index="weekday",
                    columns="hour",
                    values="amount",
                    aggfunc="count",
                    fill_value=0,
                )
                .reindex(weekdays)
                .fillna(0)
            )
            st.plotly_chart(
                px.imshow(
                    heatmap,
                    aspect="auto",
                    title="Sales heatmap (weekday x hour)",
                    labels=dict(x="Hour", y="Weekday", color="Sales"),
                ),
                width="stretch",
            )

with t_restock:
    if prodaily.empty or "product" not in prodaily.columns:
        st.info("Restock planning needs ProductDaily data.")
    else:
        recent_dates = sorted(prodaily["date"].dropna().unique())[-7:]
        recent = prodaily[prodaily["date"].isin(recent_dates)]
        average = recent.groupby("product")["units"].mean().rename("avg_units_per_day")
        if not liveprod.empty and "stock" in liveprod.columns:
            stock = liveprod.set_index("product")["stock"].rename("stock_now")
        else:
            stock = prodaily.sort_values("date").groupby("product")["stock_end"].last().rename("stock_now")
        plan = pd.concat([average, stock], axis=1).reset_index()
        plan["days_left"] = (
            plan["stock_now"] / plan["avg_units_per_day"].where(plan["avg_units_per_day"] > 0)
        ).round(1)
        plan["action"] = plan["days_left"].apply(
            lambda value: (
                "No recent sales"
                if pd.isna(value)
                else ("REFILL NOW" if value < 1 else ("Refill soon" if value < 2 else "OK"))
            )
        )
        st.dataframe(plan.sort_values("days_left"), width="stretch", hide_index=True)

with t_data:
    st.write("Sheet tabs read by this dashboard:")
    for tab, df in zip(TABS, [live, liveprod, daily, prodaily, tx]):
        with st.expander(f"{tab} ({len(df)} rows)"):
            st.code(url_for(tab), language="text")
            if tab in errors:
                st.error(f"{tab}: {errors[tab]}")
            st.write(f"Rows: {len(df)}")
            if df.empty:
                st.write("empty")
            else:
                st.write("Columns:", list(df.columns))
                st.dataframe(df.head(5), width="stretch", hide_index=True)
