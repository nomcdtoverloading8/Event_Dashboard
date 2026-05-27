# =====================================================
# RESTORATION OUTAGE DASHBOARD
# =====================================================

import streamlit as st
import pandas as pd
import plotly.express as px

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Restoration Outage Dashboard",
    layout="wide"
)

st.title("Restoration Outage Dashboard")

st.set_option(
    'client.showErrorDetails',
    False
)

# =====================================================
# GOOGLE SHEET IDS
# =====================================================

MASTER_FILE_ID = st.secrets["MASTER_FILE_ID"]
EVENT_FILE_ID = st.secrets["EVENT_FILE_ID"]

# =====================================================
# GOOGLE SHEET URLS
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

    master_df = pd.read_csv(MASTER_URL)

    master_df.columns = (
        master_df.columns
        .str.strip()
        .str.upper()
    )

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

start_time = merged_df["EVENT_TIME"].min()

end_time = merged_df["EVENT_TIME"].max()

col1, col2, col3 = st.columns(3)

with col1:

    st.caption("Start Time")

    st.write(
        start_time.strftime(
            "%d-%m-%Y %I:%M %p"
        )
    )

with col2:

    st.caption("End Time")

    st.write(
        end_time.strftime(
            "%d-%m-%Y %I:%M %p"
        )
    )

with col3:

    st.caption("Duration")

    st.write(
        str(end_time - start_time)
    )

# =====================================================
# SIDEBAR FILTERS
# =====================================================

st.sidebar.header("Filters")

# =====================================================
# DATETIME FILTERS
# =====================================================

st.sidebar.markdown(
    """
Datetime Format:  
DD-MM-YYYY HH:MM AM/PM
"""
)

start_filter_text = st.sidebar.text_input(
    "Start Datetime",
    value=start_time.strftime(
        "%d-%m-%Y %I:%M %p"
    )
)

end_filter_text = st.sidebar.text_input(
    "End Datetime",
    value=end_time.strftime(
        "%d-%m-%Y %I:%M %p"
    )
)

try:

    start_filter = pd.to_datetime(
        start_filter_text,
        format="%d-%m-%Y %I:%M %p"
    )

    end_filter = pd.to_datetime(
        end_filter_text,
        format="%d-%m-%Y %I:%M %p"
    )

except:

    st.sidebar.error(
        "Invalid datetime format"
    )

    st.stop()

filtered_df = merged_df[
    (merged_df["EVENT_TIME"] >= start_filter) &
    (merged_df["EVENT_TIME"] <= end_filter)
]

# =====================================================
# FILTER FUNCTION
# =====================================================

def apply_filter(df, column):

    options = sorted(
        df[column]
        .dropna()
        .astype(str)
        .unique()
    )

    selected = st.sidebar.multiselect(
        column,
        options=options
    )

    if len(selected) > 0:

        df = df[
            df[column]
            .astype(str)
            .isin(selected)
        ]

    return df

# =====================================================
# APPLY FILTERS
# =====================================================

filter_columns = [
    "CIRCLE",
    "DIVISION",
    "ZONE/DC",
    "FEEDER S/S",
    "FEEDER TYPE"
]

for col in filter_columns:

    filtered_df = apply_filter(
        filtered_df,
        col
    )

# =====================================================
# LATEST EVENT OF EACH METER ONLY
# =====================================================

latest_df = (
    filtered_df
    .sort_values(
        "EVENT_TIME"
    )
    .groupby("METER_ID")
    .tail(1)
    .copy()
)

# =====================================================
# EVENT CATEGORY FILTER
# =====================================================

event_options = [
    "Occurrence",
    "Restoration"
]

selected_event_filter = st.sidebar.multiselect(
    "Latest Meter Status",
    options=event_options
)

if len(selected_event_filter) > 0:

    latest_df = latest_df[
        latest_df["EVENT_CATEGORY"]
        .isin(selected_event_filter)
    ]

# =====================================================
# OCCURRENCE VS RESTORATION COUNT
# =====================================================

count_df = (
    latest_df["EVENT_CATEGORY"]
    .value_counts()
    .reset_index()
)

count_df.columns = [
    "EVENT_CATEGORY",
    "COUNT"
]

fig1 = px.bar(
    count_df,
    x="EVENT_CATEGORY",
    y="COUNT",
    text="COUNT",
    color="EVENT_CATEGORY",
    title="Latest Meter Status Count"
)

fig1.update_traces(
    textposition="outside"
)

st.plotly_chart(
    fig1,
    use_container_width=True
)

# =====================================================
# EVENT TIMELINE
# =====================================================

timeline_df = filtered_df.copy()

timeline_df["TIME_BLOCK"] = (
    timeline_df["EVENT_TIME"]
    .dt.floor("15min")
)

timeline_summary = (
    timeline_df.groupby(
        ["TIME_BLOCK", "EVENT_CATEGORY"]
    )
    .size()
    .reset_index(name="COUNT")
)

timeline_summary["TIME_LABEL"] = (
    timeline_summary["TIME_BLOCK"]
    .dt.strftime(
        "%d-%m-%Y %I:%M %p"
    )
)

fig2 = px.line(
    timeline_summary,
    x="TIME_BLOCK",
    y="COUNT",
    color="EVENT_CATEGORY",
    markers=True,
    custom_data=["TIME_LABEL"]
)

fig2.update_traces(
    hovertemplate=
    "<b>Datetime:</b> %{customdata[0]}<br>" +
    "<b>Count:</b> %{y}<br>" +
    "<b>Category:</b> %{fullData.name}" +
    "<extra></extra>"
)

fig2.update_layout(
    title="Restoration vs Occurrence Timeline",
    hovermode="x unified"
)

fig2.update_xaxes(
    showspikes=True,
    spikemode="across",
    spikesnap="cursor",
    showline=True
)

fig2.update_yaxes(
    showspikes=True,
    spikemode="across",
    spikesnap="cursor",
    showline=True
)

st.plotly_chart(
    fig2,
    use_container_width=True
)

# =====================================================
# METER SEQUENCE TABLE
# =====================================================

sequence_df = (
    filtered_df
    .sort_values(
        ["METER_ID", "EVENT_TIME"]
    )
    .groupby("METER_ID")
    .agg({

        "EVENT_CATEGORY":
            lambda x:
            " -> ".join(x),

        "EVENT_TIME":
            ["min", "max"],

        "CIRCLE":
            "first",

        "DIVISION":
            "first",

        "ZONE/DC":
            "first",

        "FEEDER S/S":
            "first",

        "FEEDER NAME":
            "first",

        "FEEDER TYPE":
            "first"
    })
)

sequence_df.columns = [
    "SEQUENCE",
    "START_TIME",
    "END_TIME",
    "CIRCLE",
    "DIVISION",
    "ZONE/DC",
    "FEEDER S/S",
    "FEEDER NAME",
    "FEEDER TYPE"
]

sequence_df = sequence_df.reset_index()

# =====================================================
# ADD FINAL STATUS
# =====================================================

sequence_df["FINAL_STATUS"] = (
    sequence_df["SEQUENCE"]
    .str.split(" -> ")
    .str[-1]
)

# =====================================================
# APPLY FINAL STATUS FILTER
# =====================================================

if len(selected_event_filter) > 0:

    sequence_df = sequence_df[
        sequence_df["FINAL_STATUS"]
        .isin(selected_event_filter)
    ]

# =====================================================
# SEQUENCE FILTER
# =====================================================

sequence_options = list(
    sequence_df["SEQUENCE"]
    .unique()
)

occurrence_patterns = sorted([
    x for x in sequence_options
    if x.startswith("Occurrence")
])

restoration_patterns = sorted([
    x for x in sequence_options
    if x.startswith("Restoration")
])

remaining_patterns = sorted([
    x for x in sequence_options
    if x not in occurrence_patterns
    and x not in restoration_patterns
])

ordered_options = (
    occurrence_patterns +
    restoration_patterns +
    remaining_patterns
)

selected_sequences = st.sidebar.multiselect(
    "Sequence Pattern",
    options=ordered_options
)

if len(selected_sequences) > 0:

    sequence_df = sequence_df[
        sequence_df["SEQUENCE"]
        .isin(selected_sequences)
    ]

# =====================================================
# SEARCH METER ID
# =====================================================

meter_search = st.text_input(
    "Search Meter ID"
)

if meter_search:

    sequence_df = sequence_df[
        sequence_df["METER_ID"]
        .str.contains(
            meter_search,
            case=False,
            na=False
        )
    ]

# =====================================================
# FORMAT TIMES
# =====================================================

sequence_df["START_TIME"] = (
    sequence_df["START_TIME"]
    .dt.strftime(
        "%d-%m-%Y %I:%M:%S %p"
    )
)

sequence_df["END_TIME"] = (
    sequence_df["END_TIME"]
    .dt.strftime(
        "%d-%m-%Y %I:%M:%S %p"
    )
)

# =====================================================
# REMOVE FINAL STATUS COLUMN
# =====================================================

sequence_df = sequence_df.drop(
    columns=["FINAL_STATUS"]
)

# =====================================================
# SEQUENCE TABLE
# =====================================================

st.dataframe(
    sequence_df,
    use_container_width=True,
    height=500
)

# =====================================================
# FOOTER
# =====================================================

st.caption(
    "Dashboard auto-refreshes every 5 minutes from Google Sheets."
)
