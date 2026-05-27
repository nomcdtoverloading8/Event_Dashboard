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

    # MASTER FILE
    master_df = pd.read_csv(MASTER_URL)

    master_df.columns = (
        master_df.columns
        .str.strip()
        .str.upper()
    )

    # EVENT FILE HEADER DETECTION
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
# FILTERS
# =====================================================

st.sidebar.header("Filters")

# =====================================================
# DATETIME FILTERS
# =====================================================

start_filter = st.sidebar.text_input(
    "Start Datetime",
    value=start_time.strftime(
        "%Y-%m-%d %H:%M:%S"
    )
)

end_filter = st.sidebar.text_input(
    "End Datetime",
    value=end_time.strftime(
        "%Y-%m-%d %H:%M:%S"
    )
)

start_filter = pd.to_datetime(
    start_filter
)

end_filter = pd.to_datetime(
    end_filter
)

filtered_df = merged_df[
    (merged_df["EVENT_TIME"] >= start_filter) &
    (merged_df["EVENT_TIME"] <= end_filter)
]

# =====================================================
# MULTIPLE FILTERS
# =====================================================

filter_columns = [
    "CIRCLE",
    "DIVISION",
    "ZONE/DC",
    "FEEDER S/S",
    "FEEDER TYPE"
]

for col in filter_columns:

    options = sorted(
        filtered_df[col]
        .dropna()
        .unique()
    )

    selected = st.sidebar.multiselect(
        col,
        options=options,
        default=options
    )

    if selected:

        filtered_df = filtered_df[
            filtered_df[col]
            .isin(selected)
        ]

# =====================================================
# EVENT COUNTS
# =====================================================

count_df = (
    filtered_df["EVENT_CATEGORY"]
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
    title="Occurrence vs Restoration Count"
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
    "<b>Time:</b> %{customdata[0]}<br>" +
    "<b>Count:</b> %{y}<extra></extra>"
)

fig2.update_layout(
    title="Restoration vs Occurrence Timeline",
    hovermode="x unified"
)

st.plotly_chart(
    fig2,
    use_container_width=True
)

# =====================================================
# METER SEQUENCE ANALYSIS
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
            " → ".join(x),

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

sequence_df = (
    sequence_df
    .reset_index()
)

# =====================================================
# SEQUENCE CLASSIFICATION
# =====================================================

def classify_sequence(seq):

    seq = seq.lower()

    occ_count = seq.count(
        "occurrence"
    )

    res_count = seq.count(
        "restoration"
    )

    if occ_count > 0 and res_count == 0:

        return "Only Occurrence"

    elif occ_count > 0 and res_count > 0:

        if occ_count == res_count:

            return "Fully Restored"

        else:

            return "Partially Restored"

    elif res_count > 0 and occ_count == 0:

        return "Only Restoration"

    else:

        return "Unknown"

sequence_df["PATTERN"] = (
    sequence_df["SEQUENCE"]
    .apply(classify_sequence)
)

# =====================================================
# PATTERN GRAPH
# =====================================================

pattern_graph_df = (
    sequence_df["PATTERN"]
    .value_counts()
    .reset_index()
)

pattern_graph_df.columns = [
    "PATTERN",
    "COUNT"
]

fig3 = px.bar(
    pattern_graph_df,
    x="PATTERN",
    y="COUNT",
    text="COUNT",
    color="PATTERN",
    hover_data=["COUNT"],
    title="Meter Sequence Patterns"
)

fig3.update_traces(
    textposition="outside"
)

st.plotly_chart(
    fig3,
    use_container_width=True
)

# =====================================================
# PATTERN FILTER
# =====================================================

pattern_filter = st.multiselect(
    "Pattern Filter",
    options=sequence_df["PATTERN"].unique(),
    default=sequence_df["PATTERN"].unique()
)

sequence_df = sequence_df[
    sequence_df["PATTERN"]
    .isin(pattern_filter)
]

# =====================================================
# SEARCH FILTER
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
# SEQUENCE TABLE
# =====================================================

st.dataframe(
    sequence_df,
    use_container_width=True,
    height=500
)

# =====================================================
# RAW DATA
# =====================================================

with st.expander(
    "Raw Data"
):

    st.dataframe(
        filtered_df,
        use_container_width=True,
        height=500
    )

# =====================================================
# FOOTER
# =====================================================

st.caption(
    "Dashboard auto-refreshes every 5 minutes from Google Sheets."
)
