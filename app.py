import streamlit as st
from simulation import run_model, run_one_semester_outlook
import pandas as pd

# --------------------------------------------------
# Page Title
# --------------------------------------------------

st.title("Academic Capacity Planning Tool")
st.write("Simulate enrollment growth and detect course bottlenecks.")

tab1, tab2 = st.tabs(["Multi-Semester Simulation", "One-Semester Outlook"])
primaryColor="#C5050C"
# --------------------------------------------------
# Make Slider Red
# --------------------------------------------------

st.markdown(
    """
    <style>

    /* Slider handle */
    div[data-baseweb="slider"] [role="slider"]{
        background-color: #C5050C !important;
        border-color: #C5050C !important;
    }

    /* Filled track */
    div[data-baseweb="slider"] div[data-testid="stSlider"] > div > div {
        background-color: #C5050C !important;
    }

    </style>
    """,
    unsafe_allow_html=True
)
with tab1:

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
    # Sorting Dropdown
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
    # Advanced Growth Options (Below Sort)
    # --------------------------------------------------

    st.markdown("### Advanced Growth Options")

    majors = ["IE", "BME", "CHEME", "CIVIL", "COMPE", "EE", "EM", "EP", "ENVIRO", "GEO", "MSE", "ME", "NE"]

    advanced_selected_majors = []
    custom_growth = {}

    with st.expander("Configure Advanced Growth Settings"):

        st.write("Select majors and assign custom growth rates.")

        for major in majors:

            col1, col2 = st.columns([2,1])

            with col1:
                default_checked = not st.session_state.get("reset_one_sem_tab1", False)

                selected = st.checkbox(major,value=default_checked,key=f"tab1_{major}_advanced")

            if selected:

                advanced_selected_majors.append(major)

                with col2:
                    growth = st.number_input(
                        f"{major} Growth %",
                        min_value=-50,
                        max_value=100,
                        value=10,
                        step=1,
                        key=f"{major}_growth"
                    )

                custom_growth[major] = growth

    if st.button("Clear Advanced Options", key='clear_advanced_tab1'):

        for major in majors:
            st.session_state[f"{major}_advanced"] = False
            st.session_state[f"{major}_growth"] = 10

        st.rerun()

    # --------------------------------------------------
    # Override logic if advanced options are used
    # --------------------------------------------------

    use_advanced = len(advanced_selected_majors) > 0

    if use_advanced:
        selected_major = "All"

    # --------------------------------------------------
    # Run Simulation Button
    # --------------------------------------------------

    if st.button("Run Simulation", type="primary"):

        with st.spinner("Running simulation..."):
            recommendations = run_model(
                growth_percent,
                selected_major,
                max_semesters,
                custom_growth,
                advanced_selected_majors
            )

        st.success("Simulation Complete!")

        for scenario, recs in recommendations.items():

            st.subheader(f"{scenario}")

            if not recs:
                st.success("No bottlenecks detected.")
                continue

            df = pd.DataFrame(recs)
            if "overage" not in df.columns:
                df["overage"] = None

            # ================================================
            # SEVERITY CLASSIFICATION
            # ================================================

            def classify_severity(overage):

                if overage >= 50:
                    return "High"
                elif overage >= 10:
                    return "Medium"
                else:
                    return "Low"

            df["Severity"] = df["overage"].apply(classify_severity)

            # ================================================
            # SORTING
            # ================================================

            if sort_option == "Most Critical (Largest Overage)":
                df = df.sort_values(by="overage", ascending=False)

            elif sort_option == "Highest Enrollment":
                df = df.sort_values(by="enrollment", ascending = False)

            elif sort_option == "Earliest Semester (Immediate Issues)":
                df = df.sort_values(by="semester_number", ascending = True)

            elif sort_option == "Latest Semester (Future Issues)":
                df = df.sort_values(by="semester_number", ascending = False)

            # ================================================
            # SAFE METRICS
            # ================================================

            col1, col2, col3 = st.columns(3)

            col1.metric("Total Records", len(df))

            if "overage" in df.columns:
                col2.metric("Worst Overage", df["overage"].max())
            else:
                col2.metric("Capacity Metric","N/A")

            if "semester_number" in df.columns and len(df) > 0:
                col3.metric("First Issue Occurs (Semester", df["semester_number"].min())
            else:
                col3.metric("First Issue Occurs (Semester)","N/A")

            # ================================================
            # SPLIT TABLES
            # ================================================

            bottlenecks_df = df[df["overage"] > 0].copy()
            other_classes_df = df[df["overage"] <= 0].copy()

            # ================================================
            # SUMMARY BY MAJOR
            # ================================================

            all_majors = majors

            major_summary = (
                bottlenecks_df.groupby("major")
                .agg(
                    Total_Issues=("course", "count"),
                    Worst_Overage=("overage", "max"),
                    First_Semester=("semester_number", "min")
                )
                .reset_index()
            )

            full_summary = pd.DataFrame({"major": all_majors}).merge(
                major_summary,
                on="major",
                how="left"
            )

            full_summary["Total_Issues"] = full_summary["Total_Issues"].fillna(0).round(0).astype(int)
            full_summary["Worst_Overage"] = full_summary["Worst_Overage"].fillna("N/A")
            full_summary["First_Semester"] = full_summary["First_Semester"].fillna("N/A")

            st.dataframe(major_summary.style.format({
                "Total_Issues": "{:.0f}",
                "Worst_Overage": "{:.0f}"
            }), use_container_width=True)

            st.divider()

            # ================================================
            # BOTTLENECK TABLE
            # ================================================

            st.subheader("Capacity Bottlenecks")

            with st.expander("View Detailed Issues", expanded=True):

                def highlight_severity(row):

                    if row["Severity"] == "High":
                        return ["background-color: #ffcccc"] * len(row)

                    elif row["Severity"] == "Medium":
                        return ["background-color: #fff3cd"] * len(row)

                    return [""] * len(row)

                styled_df = bottlenecks_df.style.apply(highlight_severity, axis=1)

                st.dataframe(styled_df, use_container_width=True)

            # ================================================
            # OTHER COURSES TABLE
            # ================================================

            with st.expander("Other Classes (Available Capacity)"):

                if not other_classes_df.empty:

                    other_classes_df["remaining_capacity"] = -other_classes_df["overage"]
                    other_classes_df = other_classes_df.drop(columns=["overage"])

                    cols = [
                        "major",
                        "course",
                        "semester_number",
                        "enrollment",
                        "capacity",
                        "remaining_capacity"
                    ]

                    other_classes_df = other_classes_df[[c for c in cols if c in other_classes_df.columns]]

                    st.dataframe(other_classes_df, use_container_width=True)

                else:
                    st.write("No additional classes with remaining capacity.")


with tab2:

    st.header("One Semester Outlook")

    majors = ["IE","BME","CHEME","CIVIL","COMPE","EE","EM","EP","ENVIRO","GEO","MSE","ME","NE"]

    # ==================================================
    # ADVANCED GROWTH OPTIONS
    # ==================================================

    st.markdown("### Advanced Growth Options")

    advanced_selected_majors = []
    custom_growth = {}

    # ==================================================
    # TERM + NOISE CONTROLS
    # ==================================================

    term_choice = st.radio(
        "Semester",
        ["Fall", "Spring"]
    )

    include_noise = st.checkbox(
        "Include enrollment uncertainty (±8%)",
        value=True
    )

    st.write("#### Select majors and assign custom growth rates.")

    for major in majors:

        col1, col2 = st.columns([2, 1])

        with col1:
            default_checked = not st.session_state.get("reset_one_sem_tab2", False)

            selected = st.checkbox(
                major,
                value=default_checked,
                key=f"one_sem_{major}_advanced"
            )

        if selected:

            advanced_selected_majors.append(major)

            with col2:
                default_growth = 10

                growth = st.number_input(
                    f"{major} Growth %",
                    min_value=-50,
                    max_value=100,
                    value=default_growth,
                    step=1,
                    key=f"one_sem_{major}_growth"
                )

            custom_growth[major] = growth

    if st.button("Clear Advanced Options", key="clear_advanced_tab2"):

        for major in majors:
            st.session_state[f"one_sem_{major}_advanced"] = False
            st.session_state[f"one_sem_{major}_growth"] = 10

        st.rerun()

    # ==================================================
    # RUN SIMULATION
    # ==================================================

    if st.button("Run One Semester Outlook", type="primary"):

        results = run_one_semester_outlook(
            selected_majors=advanced_selected_majors,
            growth_percent=10,
            term=term_choice,
            include_noise=include_noise
        )

        df = pd.DataFrame(results)

        bottlenecks_df = df[df["overage"] > 0].copy()
        other_classes_df = df[df["overage"] <= 0].copy()

        # ==========================================
        # ADD SEVERITY (FIX FOR YOUR ERROR)
        # ==========================================

        def classify_severity(overage):
            if overage >= 50:
                return "High"
            elif overage >= 10:
                return "Medium"
            else:
                return "Low"

        if not bottlenecks_df.empty:
            bottlenecks_df["Severity"] = bottlenecks_df["overage"].apply(classify_severity)

        # ==========================================
        # SUMMARY TABLE
        # ==========================================

        summary = (
            bottlenecks_df.groupby("major")
            .agg(
                Total_Issues=("course","count"),
                Worst_Overage=("overage","max"),
                Semester=("semester_number","min")
            )
            .reset_index()
        )

        st.subheader("Summary by Major")
        st.dataframe(summary, use_container_width=True)

        st.divider()

        # ==========================================
        # BOTTLENECK TABLE (WITH COLORS FIXED)
        # ==========================================

        st.subheader("Courses Over Capacity")

        with st.expander("View Detailed Issues", expanded=True):

            if not bottlenecks_df.empty:

                def highlight_severity(row):

                    if row.get("Severity") == "High":
                        return ["background-color: #ffcccc"] * len(row)

                    elif row.get("Severity") == "Medium":
                        return ["background-color: #fff3cd"] * len(row)

                    return [""] * len(row)

                styled_df = bottlenecks_df.style.apply(highlight_severity, axis=1)

                st.dataframe(styled_df, use_container_width=True)

            else:
                st.write("No bottlenecks detected.")

        st.divider()

        # ==========================================
        # UNDER CAPACITY TABLE
        # ==========================================

        st.subheader("Courses With Remaining Capacity")

        if not other_classes_df.empty:

            other_classes_df["remaining_capacity"] = -other_classes_df["overage"]
            other_classes_df = other_classes_df.drop(columns=["overage"])

            st.dataframe(
                other_classes_df,
                use_container_width=True
            )

        else:
            st.write("No courses with remaining capacity.")