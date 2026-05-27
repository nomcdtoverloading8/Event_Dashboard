# =========================================================
# RESTORATION OUTAGE DASHBOARD
# STREAMLIT APP
# =========================================================

# =========================================================
# REQUIREMENTS.TXT
# =========================================================
#
# streamlit
# pandas
# plotly
# openpyxl
#
# =========================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Restoration Outage Dashboard",
    layout="wide"
)

st.title("⚡ Restoration Outage Dashboard")

# =========================================================
# STREAMLIT SECRETS
# =========================================================

# Add these in Streamlit Secrets:
#
# MASTER_FILE_ID = "YOUR_MASTER_FILE_ID"
# EVENT_FILE_ID = "YOUR_EVENT_FILE_ID"

MASTER_FILE_ID = st.secrets["MASTER_FILE_ID"]
EVENT_FILE_ID = st.secrets["EVENT_FILE_ID"]

# =========================================================
# GOOGLE SHEET CSV EXPORT LINKS
# =========================================================

MASTER_URL = (
    f"https://docs.google.com/spreadsheets/d/"
    f"{MASTER_FILE_ID}/export?format=csv"
)

EVENT_URL = (
    f"https://docs.google.com/spreadsheets/d/"
    f"{EVENT_FILE_ID}/export?format=csv"
)

# =========================================================
# LOAD DATA
# =========================================================

@st.cache_data(ttl=300)
def load_data():

    # -------------------------
    # LOAD MASTER FILE
    # -------------------------

    master_df = pd.read_csv(MASTER_URL)

    master_df.columns = master_df.columns.str.strip()

    # -------------------------
    # LOAD EVENT FILE
    # -------------------------

    event_df = pd.read_csv(EVENT_URL)

    event_df.columns = event_df.columns.str.strip()

    return master_df, event_df


try:

    master_df, event_df = load_data()

except Exception as e:

    st.error(f"Error loading data: {e}")
    st.stop()

# =========================================================
# DATA CLEANING
# =========================================================

# -------------------------
# CLEAN MASTER FILE
# -------------------------

master_df["Meterno."] = (
    master_df["Meterno."]
    .astype(str)
    .str.strip()
)

# -------------------------
# CLEAN EVENT FILE
# -------------------------

event_df["Meter_ID"] = (
    event_df["Meter_ID"]
    .astype(str)
    .str.strip()
)

event_df["EVENT_CATEGORY"] = (
    event_df["EVENT_CATEGORY"]
    .astype(str)
    .str.strip()
)

event_df["EVENT_TIME"] = pd.to_datetime(
    event_df["EVENT_TIME"],
    errors="coerce"
)

event_df = event_df.dropna(subset=["EVENT_TIME"])

# =========================================================
# MERGE DATA
# =========================================================

merge_columns = [
    "Meterno.",
    "Circle",
    "Division",
    "Zone/DC",
    "Feeder S/S",
    "Feeder Name",
    "Feeder Type"
]

merged_df = event_df.merge(
    master_df[merge_columns],
    left_on="Meter_ID",
    right_on="Meterno.",
    how="left"
)

# =========================================================
# HEADER METRICS
# =========================================================

min_date = merged_df["EVENT_TIME"].min()
max_date = merged_df["EVENT_TIME"].max()

duration = max_date - min_date

st.subheader("📅 Data Time Range")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Start Time",
        str(min_date)
    )

with col2:
    st.metric(
        "End Time",
        str(max_date)
    )

with col3:
    st.metric(
        "Total Duration",
        str(duration)
    )

# =========================================================
# SIDEBAR FILTERS
# =========================================================

st.sidebar.header("Filters")

# -------------------------
# DATE FILTER
# -------------------------

start_filter = st.sidebar.datetime_input(
    "Start Date",
    value=min_date
)

end_filter = st.sidebar.datetime_input(
    "End Date",
    value=max_date
)

filtered_df = merged_df[
    (merged_df["EVENT_TIME"] >= pd.Timestamp(start_filter)) &
    (merged_df["EVENT_TIME"] <= pd.Timestamp(end_filter))
]

# -------------------------
# CIRCLE FILTER
# -------------------------

circle_options = sorted(
    filtered_df["Circle"]
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
        filtered_df["Circle"].isin(selected_circle)
    ]

# -------------------------
# DIVISION FILTER
# -------------------------

division_options = sorted(
    filtered_df["Division"]
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
        filtered_df["Division"].isin(selected_division)
    ]

# =========================================================
# EVENT SEQUENCE ANALYSIS
# =========================================================

filtered_df = filtered_df.sort_values(
    ["Meter_ID", "EVENT_TIME"]
)

records = []

grouped = filtered_df.groupby("Meter_ID")

for meter_id, group in grouped:

    group = group.sort_values("EVENT_TIME")

    sequence = " → ".join(
        group["EVENT_CATEGORY"].tolist()
    )

    occurrence_count = (
        group["EVENT_CATEGORY"]
        .str.lower()
        .eq("occurrence")
        .sum()
    )

    restoration_count = (
        group["EVENT_CATEGORY"]
        .str.lower()
        .eq("restoration")
        .sum()
    )

    first_event = group["EVENT_TIME"].min()

    last_event = group["EVENT_TIME"].max()

    outage_duration = last_event - first_event

    records.append({

        "Meter_ID": meter_id,

        "Sequence": sequence,

        "Occurrence_Count": occurrence_count,

        "Restoration_Count": restoration_count,

        "Total_Events": len(group),

        "First_Event": first_event,

        "Last_Event": last_event,

        "Outage_Duration": outage_duration,

        "Circle": group["Circle"].iloc[0],

        "Division": group["Division"].iloc[0],

        "Zone/DC": group["Zone/DC"].iloc[0],

        "Feeder S/S": group["Feeder S/S"].iloc[0],

        "Feeder Name": group["Feeder Name"].iloc[0],

        "Feeder Type": group["Feeder Type"].iloc[0]
    })

pattern_df = pd.DataFrame(records)

# =========================================================
# CLASSIFICATION LOGIC
# =========================================================

def classify_pattern(sequence):

    seq = sequence.lower()

    occurrence_count = seq.count("occurrence")

    restoration_count = seq.count("restoration")

    # --------------------------------------
    # ONLY OCCURRENCE
    # --------------------------------------

    if occurrence_count > 0 and restoration_count == 0:
        return "Only Occurrence"

    # --------------------------------------
    # ONLY RESTORATION
    # --------------------------------------

    elif restoration_count > 0 and occurrence_count == 0:
        return "Only Restoration"

    # --------------------------------------
    # PERFECT MATCH
    # --------------------------------------

    elif occurrence_count == restoration_count:

        if seq.startswith("occurrence"):

            return "Balanced Sequence"

        else:

            return "Restoration First"

    # --------------------------------------
    # PENDING RESTORATION
    # --------------------------------------

    elif occurrence_count > restoration_count:
        return "Pending Restoration"

    # --------------------------------------
    # EXTRA RESTORATION
    # --------------------------------------

    elif restoration_count > occurrence_count:
        return "Extra Restoration"

    # --------------------------------------
    # OTHER
    # --------------------------------------

    else:
        return "Complex Pattern"

pattern_df["Pattern_Type"] = (
    pattern_df["Sequence"]
    .apply(classify_pattern)
)

# =========================================================
# KPI SECTION
# =========================================================

st.subheader("📊 Key Metrics")

total_meters = pattern_df["Meter_ID"].nunique()

total_occurrence = pattern_df["Occurrence_Count"].sum()

total_restoration = pattern_df["Restoration_Count"].sum()

pending_restoration = (
    pattern_df["Pattern_Type"]
    .eq("Pending Restoration")
    .sum()
)

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.metric(
        "Total Meters",
        total_meters
    )

with k2:
    st.metric(
        "Total Occurrence",
        total_occurrence
    )

with k3:
    st.metric(
        "Total Restoration",
        total_restoration
    )

with k4:
    st.metric(
        "Pending Restoration",
        pending_restoration
    )

# =========================================================
# PATTERN SUMMARY
# =========================================================

st.subheader("🔄 Event Pattern Summary")

summary_df = (
    pattern_df.groupby("Pattern_Type")
    .size()
    .reset_index(name="Meter_Count")
    .sort_values("Meter_Count", ascending=False)
)

col1, col2 = st.columns([1, 2])

with col1:

    st.dataframe(
        summary_df,
        use_container_width=True
    )

with col2:

    fig = px.bar(
        summary_df,
        x="Pattern_Type",
        y="Meter_Count",
        text="Meter_Count",
        title="Pattern Distribution"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# =========================================================
# TIMELINE ANALYSIS
# =========================================================

st.subheader("📈 Event Timeline")

timeline_df = filtered_df.copy()

timeline_df["Hour"] = (
    timeline_df["EVENT_TIME"]
    .dt.floor("H")
)

timeline_summary = (
    timeline_df.groupby(
        ["Hour", "EVENT_CATEGORY"]
    )
    .size()
    .reset_index(name="Count")
)

fig2 = px.line(
    timeline_summary,
    x="Hour",
    y="Count",
    color="EVENT_CATEGORY",
    markers=True,
    title="Occurrence vs Restoration Timeline"
)

st.plotly_chart(
    fig2,
    use_container_width=True
)

# =========================================================
# FEEDER ANALYSIS
# =========================================================

st.subheader("⚡ Feeder Wise Analysis")

feeder_summary = (
    pattern_df.groupby(
        [
            "Circle",
            "Division",
            "Feeder Name",
            "Feeder Type"
        ]
    )
    .agg(
        Total_Meters=("Meter_ID", "count"),
        Total_Occurrence=("Occurrence_Count", "sum"),
        Total_Restoration=("Restoration_Count", "sum")
    )
    .reset_index()
    .sort_values("Total_Occurrence", ascending=False)
)

st.dataframe(
    feeder_summary,
    use_container_width=True,
    height=400
)

# =========================================================
# TOP OUTAGE FEEDERS
# =========================================================

st.subheader("🚨 Top Outage Feeders")

top_feeders = (
    feeder_summary
    .sort_values(
        "Total_Occurrence",
        ascending=False
    )
    .head(15)
)

fig3 = px.bar(
    top_feeders,
    x="Feeder Name",
    y="Total_Occurrence",
    color="Feeder Type",
    title="Top 15 Feeders by Occurrence Count"
)

st.plotly_chart(
    fig3,
    use_container_width=True
)

# =========================================================
# DETAILED TABLE
# =========================================================

st.subheader("🧾 Detailed Meter Event Analysis")

st.dataframe(
    pattern_df,
    use_container_width=True,
    height=600
)

# =========================================================
# DOWNLOAD SECTION
# =========================================================

st.subheader("📥 Download Reports")

output = io.BytesIO()

with pd.ExcelWriter(
    output,
    engine="openpyxl"
) as writer:

    pattern_df.to_excel(
        writer,
        sheet_name="Meter_Patterns",
        index=False
    )

    feeder_summary.to_excel(
        writer,
        sheet_name="Feeder_Summary",
        index=False
    )

    filtered_df.to_excel(
        writer,
        sheet_name="Filtered_Raw_Data",
        index=False
    )

st.download_button(
    label="Download Analysis Excel",
    data=output.getvalue(),
    file_name="Restoration_Outage_Analysis.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# =========================================================
# FOOTER
# =========================================================

st.success(
    "Dashboard auto-refreshes every 5 minutes from Google Sheets."
)
