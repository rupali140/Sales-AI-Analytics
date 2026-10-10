
import io

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


# --------------------------------------------------
# 1. Page configuration
# --------------------------------------------------
st.set_page_config(
    page_title="Sales Analytics Dashboard",
    page_icon="📊",
    layout="wide",
)

API_BASE_URL = "http://127.0.0.1:8000"
SALES_URL = f"{API_BASE_URL}/api/sales"
IMPORT_URL = f"{API_BASE_URL}/api/sales/import"
PREDICTION_URL = f"{API_BASE_URL}/api/predictions/revenue"
INSIGHTS_URL = f"{API_BASE_URL}/api/insights"

REQUEST_TIMEOUT = 30
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

MONTH_MAP = {
    "january": "Jan", "jan": "Jan",
    "february": "Feb", "feb": "Feb",
    "march": "Mar", "mar": "Mar",
    "april": "Apr", "apr": "Apr",
    "may": "May",
    "june": "Jun", "jun": "Jun",
    "july": "Jul", "jul": "Jul",
    "august": "Aug", "aug": "Aug",
    "september": "Sep", "sep": "Sep",
    "october": "Oct", "oct": "Oct",
    "november": "Nov", "nov": "Nov",
    "december": "Dec", "dec": "Dec",
}

CSV_COLUMNS = ["month", "revenue", "profit", "orders"]


# --------------------------------------------------
# 2. Fetch data from FastAPI
# --------------------------------------------------
@st.cache_data(ttl=30)
def fetch_sales_data():
    response = requests.get(
        SALES_URL,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    result = response.json()

    if isinstance(result, dict):
        result = result.get("sales", result.get("data"))

    if not isinstance(result, list):
        raise ValueError(
            "The sales API did not return a list of records."
        )

    return result


def fetch_revenue_prediction():
    response = requests.get(
        PREDICTION_URL,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    result = response.json()

    required_fields = [
        "predicted_revenue",
        "average_revenue",
        "monthly_trend",
        "months_used",
    ]

    missing = [
        field for field in required_fields
        if field not in result
    ]

    if missing:
        raise ValueError(
            "Prediction response is missing: "
            + ", ".join(missing)
        )

    return result


def fetch_sales_insights():
    """Fetch sales insights from the FastAPI backend."""
    response = requests.get(
        INSIGHTS_URL,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    result = response.json()

    if not isinstance(result, dict):
        raise ValueError(
            "The insights API did not return a JSON object."
        )

    return result


# --------------------------------------------------
# 3. Validate uploaded CSV
# --------------------------------------------------
def prepare_csv(uploaded_file):
    raw = uploaded_file.getvalue()

    if not raw:
        raise ValueError("The selected CSV file is empty.")

    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("CSV file size cannot exceed 10 MB.")

    try:
        frame = pd.read_csv(io.BytesIO(raw))
    except (
        pd.errors.ParserError,
        pd.errors.EmptyDataError,
        UnicodeDecodeError,
    ) as error:
        raise ValueError(
            f"Could not read the CSV file: {error}"
        ) from error

    if frame.empty:
        raise ValueError("The CSV contains no data rows.")

    frame.columns = (
        frame.columns.astype(str).str.strip().str.lower()
    )

    missing = [
        column for column in CSV_COLUMNS
        if column not in frame.columns
    ]

    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing)
        )

    frame = frame[CSV_COLUMNS].copy()

    frame["month"] = frame["month"].map(
        lambda value: MONTH_MAP.get(
            str(value).strip().lower(), ""
        )
    )

    for column in ["revenue", "profit", "orders"]:
        frame[column] = pd.to_numeric(
            frame[column],
            errors="coerce",
        )

    if frame.isnull().any().any():
        raise ValueError(
            "Check for invalid months, blank cells, "
            "or non-numeric values."
        )

    if not frame["month"].isin(MONTHS).all():
        raise ValueError(
            "Use valid month names, such as Jan or January."
        )

    if frame["month"].duplicated().any():
        raise ValueError(
            "Each month must appear only once in the CSV."
        )

    numeric_columns = ["revenue", "profit", "orders"]

    if (frame[numeric_columns] < 0).any().any():
        raise ValueError(
            "Revenue, profit, and orders cannot be negative."
        )

    if (frame["orders"] % 1 != 0).any():
        raise ValueError("Orders must be whole numbers.")

    frame["orders"] = frame["orders"].astype(int)

    return frame.rename(
        columns={
            "month": "Month",
            "revenue": "Revenue",
            "profit": "Profit",
            "orders": "Orders",
        }
    )


# --------------------------------------------------
# 4. Prepare API data
# --------------------------------------------------
def load_api_frame():
    records = fetch_sales_data()
    frame = pd.DataFrame(records)

    if frame.empty:
        return pd.DataFrame(
            columns=["Month", "Revenue", "Profit", "Orders"]
        )

    missing = [
        column for column in CSV_COLUMNS
        if column not in frame.columns
    ]

    if missing:
        raise ValueError(
            "The API response is missing: "
            + ", ".join(missing)
        )

    frame = frame[CSV_COLUMNS].copy()

    frame["month"] = frame["month"].map(
        lambda value: MONTH_MAP.get(
            str(value).strip().lower(), ""
        )
    )

    for column in ["revenue", "profit", "orders"]:
        frame[column] = pd.to_numeric(
            frame[column],
            errors="coerce",
        )

    if frame.isnull().any().any():
        raise ValueError(
            "The API returned invalid month or numeric values."
        )

    if not frame["month"].isin(MONTHS).all():
        raise ValueError("The API returned an invalid month.")

    if frame["month"].duplicated().any():
        raise ValueError(
            "The API returned duplicate month records."
        )

    if (frame[["revenue", "profit", "orders"]] < 0).any().any():
        raise ValueError("The API returned negative values.")

    if (frame["orders"] % 1 != 0).any():
        raise ValueError(
            "The API returned fractional order counts."
        )

    return frame.rename(
        columns={
            "month": "Month",
            "revenue": "Revenue",
            "profit": "Profit",
            "orders": "Orders",
        }
    )


# --------------------------------------------------
# 5. Sort months chronologically
# --------------------------------------------------
def sort_months(frame):
    month_order = {
        month: index
        for index, month in enumerate(MONTHS)
    }

    return (
        frame.sort_values(
            "Month",
            key=lambda column: column.map(month_order),
        )
        .reset_index(drop=True)
    )


# --------------------------------------------------
# 6. Dashboard heading and sidebar
# --------------------------------------------------
st.title("📊 Sales Analytics Dashboard")

st.caption(
    "Explore sales performance, revenue, profit, "
    "orders, and revenue predictions."
)

st.sidebar.header("🔎 Dashboard Filters")
st.sidebar.subheader("📁 Import Sales CSV")

st.sidebar.caption(
    "Required columns: month, revenue, profit, orders. "
    "Import saves your data to the backend database."
)


# --------------------------------------------------
# 7. CSV upload and validation
# --------------------------------------------------
uploaded_file = st.sidebar.file_uploader(
    "Choose a CSV file",
    type=["csv"],
    key="sales_csv_uploader",
    help="Maximum 10 MB; one row per month.",
)

prepared_upload = None

if uploaded_file is not None:
    try:
        prepared_upload = prepare_csv(uploaded_file)

        st.sidebar.success(
            f"CSV validated: {len(prepared_upload)} rows."
        )

        with st.sidebar.expander("Preview CSV"):
            st.dataframe(
                prepared_upload,
                hide_index=True,
                use_container_width=True,
            )

    except ValueError as error:
        st.sidebar.error(str(error))


# --------------------------------------------------
# 8. Import CSV into SQLite through FastAPI
# --------------------------------------------------
uploaded_bytes = (
    uploaded_file.getvalue()
    if uploaded_file is not None
    else None
)

already_imported = (
    prepared_upload is not None
    and uploaded_bytes
    == st.session_state.get("imported_csv_bytes")
)

if already_imported:
    st.sidebar.info(
        "This exact CSV has already been imported."
    )

import_clicked = st.sidebar.button(
    "📥 Import CSV to Database",
    type="primary",
    disabled=(
        prepared_upload is None or already_imported
    ),
    use_container_width=True,
)

if import_clicked and prepared_upload is not None:
    try:
        api_payload = prepared_upload.rename(
            columns={
                "Month": "month",
                "Revenue": "revenue",
                "Profit": "profit",
                "Orders": "orders",
            }
        ).to_dict(orient="records")

        response = requests.post(
            IMPORT_URL,
            json=api_payload,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()
        result = response.json()

        st.session_state["imported_csv_bytes"] = uploaded_bytes

        fetch_sales_data.clear()

        st.session_state["import_notice"] = (
            "CSV imported successfully! "
            f"New months: {result.get('inserted_count', 0)}; "
            f"updated months: {result.get('updated_count', 0)}."
        )

        st.rerun()

    except requests.exceptions.HTTPError as error:
        try:
            body = error.response.json()
            detail = body.get("detail", body)
        except (ValueError, AttributeError):
            detail = (
                error.response.text[:500]
                if error.response is not None
                else str(error)
            )

        status_code = (
            error.response.status_code
            if error.response is not None
            else "HTTP error"
        )

        st.sidebar.error(
            f"Import failed ({status_code}): {detail}"
        )

    except requests.exceptions.RequestException as error:
        st.sidebar.error(
            f"Could not reach the backend: {error}"
        )

    except (ValueError, TypeError) as error:
        st.sidebar.error(
            f"Could not process the import response: {error}"
        )


if "import_notice" in st.session_state:
    st.success(st.session_state.pop("import_notice"))


# --------------------------------------------------
# 9. Choose active dataset
# --------------------------------------------------
use_upload_preview = (
    prepared_upload is not None and not already_imported
)

if use_upload_preview:
    data = prepared_upload.copy()
    data_source = "CSV Preview (not yet saved)"

else:
    try:
        data = load_api_frame()

    except requests.exceptions.RequestException as error:
        st.error(
            "Unable to connect to FastAPI. Check that the "
            "backend is running at http://127.0.0.1:8000."
        )
        st.code(str(error))
        st.stop()

    except (ValueError, TypeError) as error:
        st.error(f"Invalid backend sales data: {error}")
        st.stop()

    data_source = "FastAPI + SQLite"


if data.empty:
    st.warning(
        "No sales data is available. Upload and import a CSV "
        "or add sales through the API."
    )
    st.stop()

data = sort_months(data)

st.caption(f"**Current data source:** {data_source}")


# --------------------------------------------------
# 10. Month filter
# --------------------------------------------------
selected_months = st.sidebar.multiselect(
    "Select month(s)",
    options=data["Month"].tolist(),
    default=data["Month"].tolist(),
    key="dashboard_month_filter",
)

filtered_data = data[
    data["Month"].isin(selected_months)
].copy()

if filtered_data.empty:
    st.warning("Please select at least one month.")
    st.stop()


# --------------------------------------------------
# 11. Calculate KPIs
# --------------------------------------------------
total_revenue = filtered_data["Revenue"].sum()
total_profit = filtered_data["Profit"].sum()
total_orders = filtered_data["Orders"].sum()

average_revenue_per_order = (
    total_revenue / total_orders
    if total_orders > 0
    else 0
)


# --------------------------------------------------
# 12. KPI cards
# --------------------------------------------------
st.subheader("📌 Key Performance Indicators")

col1, col2, col3 = st.columns(3)

col1.metric(
    "💰 Total Revenue",
    f"₹{total_revenue:,.0f}",
)

col2.metric(
    "📈 Total Profit",
    f"₹{total_profit:,.0f}",
)

col3.metric(
    "🛒 Total Orders",
    f"{total_orders:,.0f}",
)


# --------------------------------------------------
# 13. AI Sales Insights from backend
# --------------------------------------------------
st.divider()
st.subheader("🤖 AI Sales Insights")

if data_source == "FastAPI + SQLite":
    try:
        with st.spinner("Analyzing sales data..."):
            insight_data = fetch_sales_insights()

        if insight_data.get("status") == "success":
            st.info(
                insight_data.get(
                    "summary",
                    "Sales analysis completed.",
                )
            )

            st.markdown("### 📊 Key Findings")

            insights = insight_data.get("insights", [])

            if insights:
                for insight in insights:
                    st.markdown(f"- {insight}")
            else:
                st.write("No key findings available.")

            st.markdown("### 💡 Recommendations")

            recommendations = insight_data.get(
                "recommendations", []
            )

            if recommendations:
                for recommendation in recommendations:
                    st.markdown(f"- {recommendation}")
            else:
                st.write("No recommendations available.")

            metric_col1, metric_col2 = st.columns(2)

            insight_revenue = insight_data.get("total_revenue")
            insight_profit = insight_data.get("total_profit")

            if insight_revenue is not None:
                metric_col1.metric(
                    "Revenue Analyzed",
                    f"₹{float(insight_revenue):,.0f}",
                )

            if insight_profit is not None:
                metric_col2.metric(
                    "Profit Analyzed",
                    f"₹{float(insight_profit):,.0f}",
                )

            st.caption(
                f"Method: {insight_data.get('method', 'Sales Analysis')}"
            )

            note = insight_data.get("note", "")
            if note:
                st.caption(note)

        else:
            st.warning(
                insight_data.get(
                    "summary",
                    "Insights could not be generated.",
                )
            )

    except requests.exceptions.RequestException as error:
        st.warning(
            "Unable to load sales insights. "
            "Please check that the backend is running."
        )
        st.caption(str(error))

    except (ValueError, TypeError, KeyError) as error:
        st.warning(
            "The sales insights response could not be displayed."
        )
        st.caption(str(error))

else:
    st.info(
        "Import this CSV into the database to view insights "
        "based on saved sales history."
    )


# --------------------------------------------------
# 14. Revenue prediction
# --------------------------------------------------
st.divider()
st.subheader("🔮 Revenue Prediction")

prediction = None

if data_source == "FastAPI + SQLite":
    try:
        prediction = fetch_revenue_prediction()

        pred_col1, pred_col2, pred_col3 = st.columns(3)

        pred_col1.metric(
            "Predicted Next-Period Revenue",
            f"₹{prediction['predicted_revenue']:,.0f}",
        )

        pred_col2.metric(
            "Average Revenue",
            f"₹{prediction['average_revenue']:,.0f}",
        )

        trend = prediction["monthly_trend"]

        pred_col3.metric(
            "Monthly Trend",
            f"₹{trend:,.0f}",
            delta=(
                "Increasing" if trend > 0
                else "Decreasing" if trend < 0
                else "Stable"
            ),
        )

        st.caption(
            f"Method: {prediction.get('method', 'Linear Regression')} "
            f"· Historical records used: {prediction['months_used']}"
        )

        st.info(
            "This is a trend-based estimate from saved sales history, "
            "not a guarantee of future revenue."
        )

    except requests.exceptions.RequestException as error:
        st.warning(
            "Revenue prediction is temporarily unavailable. "
            "Check the prediction API."
        )
        st.caption(str(error))

    except (ValueError, TypeError, KeyError) as error:
        st.warning(
            "The prediction response could not be displayed."
        )
        st.caption(str(error))

else:
    st.info(
        "Import this CSV into the database to view a prediction "
        "based on saved sales history."
    )


# --------------------------------------------------
# 15. Historical revenue and forecast chart
# --------------------------------------------------
st.divider()
st.subheader("📈 Monthly Revenue and Forecast")

revenue_chart = px.line(
    filtered_data,
    x="Month",
    y="Revenue",
    markers=True,
    title="Historical Revenue",
    labels={
        "Month": "Month",
        "Revenue": "Revenue (₹)",
    },
)

if prediction is not None:
    revenue_chart.add_scatter(
        x=["Next period"],
        y=[prediction["predicted_revenue"]],
        mode="markers+text",
        text=[
            f"₹{prediction['predicted_revenue']:,.0f}"
        ],
        textposition="top center",
        name="Predicted Revenue",
        marker={"size": 13, "symbol": "diamond"},
    )

    revenue_chart.update_xaxes(
        categoryorder="array",
        categoryarray=MONTHS + ["Next period"],
    )

st.plotly_chart(
    revenue_chart,
    use_container_width=True,
)


# --------------------------------------------------
# 16. Profit and orders charts
# --------------------------------------------------
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    profit_chart = px.bar(
        filtered_data,
        x="Month",
        y="Profit",
        title="Monthly Profit",
        labels={"Profit": "Profit (₹)"},
    )

    st.plotly_chart(
        profit_chart,
        use_container_width=True,
    )

with chart_col2:
    orders_chart = px.bar(
        filtered_data,
        x="Month",
        y="Orders",
        title="Monthly Orders",
        labels={"Orders": "Number of Orders"},
    )

    st.plotly_chart(
        orders_chart,
        use_container_width=True,
    )


# --------------------------------------------------
# 17. Sales data table
# --------------------------------------------------
st.subheader("📋 Sales Data")

st.dataframe(
    filtered_data,
    use_container_width=True,
    hide_index=True,
)


# --------------------------------------------------
# 18. Basic sales insights for selected months
# --------------------------------------------------
st.divider()
st.subheader("💡 Sales Insights for Selected Months")

best_revenue = filtered_data.loc[
    filtered_data["Revenue"].idxmax()
]

best_profit = filtered_data.loc[
    filtered_data["Profit"].idxmax()
]

insight_col1, insight_col2 = st.columns(2)

with insight_col1:
    st.info(
        f"Highest revenue: **{best_revenue['Month']}** "
        f"(₹{best_revenue['Revenue']:,.0f})"
    )

with insight_col2:
    st.info(
        f"Highest profit: **{best_profit['Month']}** "
        f"(₹{best_profit['Profit']:,.0f})"
    )

st.metric(
    "Average Revenue per Order",
    f"₹{average_revenue_per_order:,.2f}",
)

st.caption(
    "CSV files are previewed before import. AI Sales Insights and "
    "predictions use sales history saved in the database. Forecasts "
    "are estimates and may differ from actual results. "
    "The current insights engine is rule-based."
)
