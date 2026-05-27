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

# Hide detailed error traces
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

start_time = merged_df["EVENT_TIME"].min()

end_time = merged_df["EVENT_TIME"].max()

st.subheader("Data Duration")

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Start Time",
        start_time.strftime("%d-%m-%Y %I:%M:%S %p")
    )

with col2:

    st.metric(
        "End Time",
        end_time.strftime("%d-%m-%Y %I:%M:%S %p")
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

# =====================================================
# DATE FILTERS
# =====================================================

st.sidebar.subheader("Date and Time Filters")

start_date = st.sidebar.date_input(
    "Start Date",
    value=start_time.date()
)

start_clock = st.sidebar.time_input(
    "Start Time",
    value=start_time.time()
)

end_date = st.sidebar.date_input(
    "End Date",
    value=end_time.date()
)

end_clock = st.sidebar.time_input(
    "End Time",
    value=end_time.time()
)

start_filter = pd.Timestamp.combine(
    start_date,
    start_clock
)

end_filter = pd.Timestamp.combine(
    end_date,
    end_clock
)

filtered_df = merged_df[
    (merged_df["EVENT_TIME"] >= start_filter) &
    (merged_df["EVENT_TIME"] <= end_filter)
]

# =====================================================
# CIRCLE FILTER
# =====================================================

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
# DIVISION FILTER
# =====================================================

division_options = sorted(
    filtered_df["DIVISION"]
    .dropna()
    .unique()
)

selected_division = st.sidebar.multiselect(
    "Division",
    options=division_options,
    default=division_options
)

if selected_division:

    filtered_df = filtered_df[
        filtered_df["DIVISION"]
        .isin(selected_division)
    ]

# =====================================================
# ZONE/DC FILTER
# =====================================================

zone_options = sorted(
    filtered_df["ZONE/DC"]
    .dropna()
    .unique()
)

selected_zone = st.sidebar.multiselect(
    "Zone/DC",
    options=zone_options,
    default=zone_options
)

if selected_zone:

    filtered_df = filtered_df[
        filtered_df["ZONE/DC"]
        .isin(selected_zone)
    ]

# =====================================================
# FEEDER S/S FILTER
# =====================================================

ss_options = sorted(
    filtered_df["FEEDER S/S"]
    .dropna()
    .unique()
)

selected_ss = st.sidebar.multiselect(
    "Feeder S/S",
    options=ss_options,
    default=ss_options
)

if selected_ss:

    filtered_df = filtered_df[
        filtered_df["FEEDER S/S"]
        .isin(selected_ss)
    ]

# =====================================================
# FEEDER TYPE FILTER
# =====================================================

feeder_type_options = sorted(
    filtered_df["FEEDER TYPE"]
    .dropna()
    .unique()
)

selected_feeder_type = st.sidebar.multiselect(
    "Feeder Type",
    options=feeder_type_options,
    default=feeder_type_options
)

if selected_feeder_type:

    filtered_df = filtered_df[
        filtered_df["FEEDER TYPE"]
        .isin(selected_feeder_type)
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
# EVENT TIMELINE
# =====================================================

st.subheader("Event Timeline")

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
    .dt.strftime("%d-%m-%Y %I:%M %p")
)

fig2 = px.line(
    timeline_summary,
    x="TIME_BLOCK",
    y="COUNT",
    color="EVENT_CATEGORY",
    markers=True,
    hover_data={
        "TIME_LABEL": True,
        "COUNT": True,
        "TIME_BLOCK": False
    },
    title="Event Timeline"
)

fig2.update_traces(
    hovertemplate=
    "<b>Time:</b> %{customdata[0]}<br>" +
    "<b>Count:</b> %{y}<extra></extra>"
)

st.plotly_chart(
    fig2,
    use_container_width=True
)

# =====================================================
# METER EVENT SEQUENCE
# =====================================================

st.subheader("Meter Event Sequences")

sequence_df = (
    filtered_df
    .sort_values(["METER_ID", "EVENT_TIME"])
    .groupby("METER_ID")
    .agg({
        "EVENT_CATEGORY":
            lambda x: " → ".join(x),

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

sequence_df["START_TIME"] = (
    sequence_df["START_TIME"]
    .dt.strftime("%d-%m-%Y %I:%M:%S %p")
)

sequence_df["END_TIME"] = (
    sequence_df["END_TIME"]
    .dt.strftime("%d-%m-%Y %I:%M:%S %p")
)

# =====================================================
# SEQUENCE FILTERS
# =====================================================

st.subheader("Sequence Filters")

col1, col2 = st.columns(2)

with col1:

    meter_search = st.text_input(
        "Search Meter ID"
    )

with col2:

    sequence_search = st.selectbox(
        "Sequence Type",
        options=[
            "All",
            "Contains Occurrence",
            "Contains Restoration",
            "Occurrence Only",
            "Restoration Only"
        ]
    )

# =====================================================
# APPLY SEQUENCE FILTERS
# =====================================================

if meter_search:

    sequence_df = sequence_df[
        sequence_df["METER_ID"]
        .str.contains(
            meter_search,
            case=False,
            na=False
        )
    ]

if sequence_search == "Contains Occurrence":

    sequence_df = sequence_df[
        sequence_df["SEQUENCE"]
        .str.contains(
            "Occurrence",
            case=False,
            na=False
        )
    ]

elif sequence_search == "Contains Restoration":

    sequence_df = sequence_df[
        sequence_df["SEQUENCE"]
        .str.contains(
            "Restoration",
            case=False,
            na=False
        )
    ]

elif sequence_search == "Occurrence Only":

    sequence_df = sequence_df[
        (
            sequence_df["SEQUENCE"]
            .str.contains(
                "Occurrence",
                case=False,
                na=False
            )
        )
        &
        (
            ~sequence_df["SEQUENCE"]
            .str.contains(
                "Restoration",
                case=False,
                na=False
            )
        )
    ]

elif sequence_search == "Restoration Only":

    sequence_df = sequence_df[
        (
            sequence_df["SEQUENCE"]
            .str.contains(
                "Restoration",
                case=False,
                na=False
            )
        )
        &
        (
            ~sequence_df["SEQUENCE"]
            .str.contains(
                "Occurrence",
                case=False,
                na=False
            )
        )
    ]

# =====================================================
# DISPLAY SEQUENCE TABLE
# =====================================================

st.dataframe(
    sequence_df,
    use_container_width=True,
    height=500
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
