# =====================================================
# RESTORATION OUTAGE DASHBOARD
# =====================================================

import streamlit as st
import pandas as pd
import plotly.express as px

# =====================================================
# STREAMLIT SETTINGS
# =====================================================

st.set_page_config(
    page_title="Restoration Outage Dashboard",
    layout="wide"
)

st.title("Restoration Outage Dashboard")

# Hide ugly error traces
st.set_option('client.showErrorDetails', False)

# =====================================================
# GOOGLE SHEET IDS FROM STREAMLIT SECRETS
# =====================================================

MASTER_FILE_ID = st.secrets["MASTER_FILE_ID"]
EVENT_FILE_ID = st.secrets["EVENT_FILE_ID"]

# =====================================================
# GOOGLE SHEET CSV URLS
# =====================================================

MASTER_URL = (
    f"https://docs.google.com/spreadsheets/d/"
    f"{MASTER_FILE_ID}/export?format=csv"
)

EVENT_URL = (
    f"https://docs.google.com/spreadsheets/d/"
    f"{EVENT_FILE_ID}/export?format=csv"
)

# =====================================================
# LOAD DATA
# =====================================================

@st.cache_data(ttl=300)
def load_data():

    # -----------------------------
    # MASTER FILE
    # -----------------------------

    master_df = pd.read_csv(MASTER_URL)

    master_df.columns = (
        master_df.columns
        .str.strip()
        .str.upper()
    )

    # -----------------------------
    # EVENT FILE AUTO HEADER DETECTION
    # -----------------------------

    temp_df = pd.read_csv(
        EVENT_URL,
        header=None
    )

    header_row = 0

    if "METER_ID" not in (
        temp_df.iloc[0]
        .astype(str)
        .str.upper()
        .tolist()
    ):
        header_row = 1

    event_df = pd.read_csv(
        EVENT_URL,
        header=header_row
    )

    event_df.columns = (
        event_df.columns
        .str.strip()
        .str.upper()
    )

    return master_df, event_df

# =====================================================
# SAFE LOADING
# =====================================================

try:

    master_df, event_df = load_data()

except:

    st.error(
        "Unable to load dashboard data."
    )

    st.stop()

# =====================================================
# CLEAN DATA
# =====================================================

master_df["METERNO."] = (
    master_df["METERNO."]
    .astype(str)
    .str.strip()
)

event_df["METER_ID"] = (
    event_df["METER_ID"]
    .astype(str)
    .str.strip()
)

event_df["EVENT_TIME"] = pd.to_datetime(
    event_df["EVENT_TIME"],
    errors="coerce"
)

event_df = event_df.dropna(
    subset=["EVENT_TIME"]
)

# =====================================================
# MERGE DATA
# =====================================================

merged_df = event_df.merge(

    master_df[[
        "METERNO.",
        "CIRCLE",
        "DIVISION",
        "ZONE/DC",
        "FEEDER S/S",
        "FEEDER NAME",
        "FEEDER TYPE"
    ]],

    left_on="METER_ID",
    right_on="METERNO.",
    how="left"
)

# =====================================================
# DATA DURATION
# =====================================================

st.subheader("Data Duration")

start_time = merged_df["EVENT_TIME"].min()

end_time = merged_df["EVENT_TIME"].max()

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Start Time",
        str(start_time)
    )

with col2:

    st.metric(
        "End Time",
        str(end_time)
    )

with col3:

    st.metric(
        "Duration",
        str(end_time - start_time)
    )

# =====================================================
# SIDEBAR FILTERS
# =====================================================

st.sidebar.header("Filters")

# -----------------------------
# DATE FILTER
# -----------------------------

start_filter = st.sidebar.datetime_input(
    "Start Date",
    value=start_time
)

end_filter = st.sidebar.datetime_input(
    "End Date",
    value=end_time
)

filtered_df = merged_df[
    (merged_df["EVENT_TIME"] >= pd.Timestamp(start_filter)) &
    (merged_df["EVENT_TIME"] <= pd.Timestamp(end_filter))
]

# -----------------------------
# CIRCLE FILTER
# -----------------------------

circle_options = sorted(
    filtered_df["CIRCLE"]
    .dropna()
    .unique()
)

selected_circle = st.sidebar.multiselect(
    "Circle",
    options=circle_options,
    default=circle_options
)

if selected_circle:

    filtered_df = filtered_df[
        filtered_df["CIRCLE"]
        .isin(selected_circle)
    ]

# =====================================================
# EVENT COUNTS
# =====================================================

st.subheader("Event Counts")

count_df = (
    filtered_df["EVENT_CATEGORY"]
    .value_counts()
    .reset_index()
)

count_df.columns = [
    "EVENT_CATEGORY",
    "COUNT"
]

fig = px.bar(
    count_df,
    x="EVENT_CATEGORY",
    y="COUNT",
    text="COUNT",
    title="Occurrence vs Restoration Count"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# =====================================================
# TIMELINE GRAPH
# =====================================================

st.subheader("Event Timeline")

filtered_df["HOUR"] = (
    filtered_df["EVENT_TIME"]
    .dt.floor("h")
)

timeline_df = (
    filtered_df.groupby(
        ["HOUR", "EVENT_CATEGORY"]
    )
    .size()
    .reset_index(name="COUNT")
)

fig2 = px.line(
    timeline_df,
    x="HOUR",
    y="COUNT",
    color="EVENT_CATEGORY",
    markers=True,
    title="Event Timeline"
)

st.plotly_chart(
    fig2,
    use_container_width=True
)

# =====================================================
# METER EVENT SEQUENCES
# =====================================================

st.subheader("Meter Event Sequences")

filtered_df = filtered_df.sort_values(
    ["METER_ID", "EVENT_TIME"]
)

sequence_df = (
    filtered_df.groupby("METER_ID")
    ["EVENT_CATEGORY"]
    .apply(lambda x: " → ".join(x))
    .reset_index()
)

sequence_df.columns = [
    "METER_ID",
    "SEQUENCE"
]

st.dataframe(
    sequence_df,
    use_container_width=True,
    height=400
)

# =====================================================
# RAW DATA
# =====================================================

st.subheader("Raw Data")

st.dataframe(
    filtered_df,
    use_container_width=True,
    height=500
)

# =====================================================
# FOOTER
# =====================================================

st.success(
    "Dashboard auto-refreshes every 5 minutes from Google Sheets."
)
