import streamlit as st
from simulation import run_model
import pandas as pd

# --------------------------------------------------
# Page Title
# --------------------------------------------------

st.title("Academic Capacity Planning Tool")
st.write("Simulate enrollment growth and detect course bottlenecks.")

# --------------------------------------------------
# Step 4: Make Slider Red (Custom CSS)
# --------------------------------------------------

st.markdown(
    """
    <style>
    /* Change only the slider handle (thumb) */
    div[data-baseweb="slider"] span[role="slider"] {
        background-color: red !important;
        border-color: red !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --------------------------------------------------
# User Inputs
# --------------------------------------------------

growth_percent = st.slider(
    "Enrollment Growth (%)",
    min_value=0,
    max_value=50,
    value=10
)

selected_major = st.selectbox(
    "Select Major",
    ["All", "IE", "BME", "CHEME", "CIVIL", "COMPE", "EE", "EM", "EP", "ENVIRO", "GEO", "MSE", "ME", "NE"]
)

max_semesters = st.slider(
    "Number of Semesters to Simulate",
    min_value=4,
    max_value=12,
    value=8
)

# --------------------------------------------------
# Step 2: Sorting Dropdown
# --------------------------------------------------

sort_option = st.selectbox(
    "Sort Results By",
    [
        "Most Critical (Largest Overage)",
        "Highest Enrollment",
        "Earliest Semester (Immediate Issues)",
        "Latest Semester (Future Issues)"
    ]
)

# --------------------------------------------------
# Run Simulation Button
# --------------------------------------------------

if st.button("Run Simulation"):

    with st.spinner("Running simulation..."):
        recommendations = run_model(
            growth_percent,
            selected_major,
            max_semesters
        )

    st.success("Simulation Complete!")

    # --------------------------------------------------
    # Display Results
    # --------------------------------------------------

    for scenario, recs in recommendations.items():

        st.subheader(f"{scenario}")

        if not recs:
            st.success("No bottlenecks detected.")
            continue

        df = pd.DataFrame(recs)

        # --------------------------------------------------
        # Apply Sorting (uses your existing dropdown)
        # --------------------------------------------------

        if sort_option == "Most Critical (Largest Overage)":
            df = df.sort_values(by="overage", ascending=False)

        elif sort_option == "Highest Enrollment":
            df = df.sort_values(by="enrollment", ascending=False)

        elif sort_option == "Earliest Semester (Immediate Issues)":
            df = df.sort_values(by="semester_number", ascending=True)

        elif sort_option == "Latest Semester (Future Issues)":
            df = df.sort_values(by="semester_number", ascending=False)

        # --------------------------------------------------
        # OPTIONAL SEVERITY CLASSIFICATION
        # --------------------------------------------------

        def classify_severity(overage):
            if overage >= 50:
                return "High"
            elif overage >= 20:
                return "Medium"
            else:
                return "Low"

        df["Severity"] = df["overage"].apply(classify_severity)

        # --------------------------------------------------
        # EXECUTIVE SUMMARY METRICS
        # --------------------------------------------------

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Bottlenecks", len(df))
        col2.metric("Worst Overage", df["overage"].max())
        col3.metric("First Issue Occurs (Semester)", df["semester_number"].min())

        st.divider()

        # --------------------------------------------------
        # SUMMARY BY MAJOR (Executive Friendly)
        # --------------------------------------------------

        if "major" in df.columns:

            st.markdown("### Issues by Major")

            major_summary = (
                df.groupby("major")
                .agg(
                    Total_Issues=("course", "count"),
                    Worst_Overage=("overage", "max"),
                    First_Semester=("semester_number", "min")
                )
                .reset_index()
            )

            st.dataframe(major_summary, use_container_width=True)

            st.divider()

        # --------------------------------------------------
        # EXPANDABLE DETAILED TABLE
        # --------------------------------------------------

        with st.expander("View Detailed Issues"):

            # Color severity visually
            def highlight_severity(row):
                if row["Severity"] == "High":
                    return ["background-color: #ffcccc"] * len(row)
                elif row["Severity"] == "Medium":
                    return ["background-color: #fff3cd"] * len(row)
                else:
                    return [""] * len(row)

            styled_df = df.style.apply(highlight_severity, axis=1)

            st.dataframe(styled_df, use_container_width=True)