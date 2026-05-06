import pandas as pd
import numpy as np

# =====================================================
# GOOGLE SHEET URLS
# =====================================================

COURSE_PLANS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2Tu2_e3veV9M0wezAX7Fytkm9Y_HjOGp6vSB8xlEEvKa58BtKAUfJmL7S_M9iOShOk2CHnq0R20bd/pub?gid=0&single=true&output=csv"
ENROLLMENTS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2Tu2_e3veV9M0wezAX7Fytkm9Y_HjOGp6vSB8xlEEvKa58BtKAUfJmL7S_M9iOShOk2CHnq0R20bd/pub?gid=1260404694&single=true&output=csv"
CAPACITIES_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2Tu2_e3veV9M0wezAX7Fytkm9Y_HjOGp6vSB8xlEEvKa58BtKAUfJmL7S_M9iOShOk2CHnq0R20bd/pub?gid=4062538&single=true&output=csv"
PLACEMENTS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2Tu2_e3veV9M0wezAX7Fytkm9Y_HjOGp6vSB8xlEEvKa58BtKAUfJmL7S_M9iOShOk2CHnq0R20bd/pub?gid=1044514389&single=true&output=csv"

# =====================================================
# LOAD FUNCTIONS
# =====================================================

def load_courses():
    df = pd.read_csv(CAPACITIES_URL)
    courses = {}
    for _, row in df.iterrows():
        courses[row["course_code"]] = {
            "Fall": row["fall_capacity"],
            "Spring": row["spring_capacity"]
        }
    return courses


def load_course_plan():
    df = pd.read_csv(COURSE_PLANS_URL)
    course_plans = {}
    for _, row in df.iterrows():
        major = row["major"]
        if major not in course_plans:
            course_plans[major] = []
        course_plans[major].append({
            "course": row["course_code"],
            "min_semester": row["min_semester"],
            "max_semester": row["max_semester"]
        })
    return course_plans


def load_baseline_enrollments():
    df = pd.read_csv(ENROLLMENTS_URL)
    baseline_cohorts = {}
    for _, row in df.iterrows():
        baseline_cohorts[row["major"]] = row["baseline_enrollment"]
    return baseline_cohorts


def load_placements():
    df = pd.read_csv(PLACEMENTS_URL)
    semester1_placements = (
        df[df["semester"] == 1]
        .set_index("course_code")["percent"]
        .to_dict()
    )
    semester2_placements = (
        df[df["semester"] == 2]
        .set_index("course_code")["percent"]
        .to_dict()
    )
    return semester1_placements, semester2_placements


def load_cohort_percentages():
    cohorts_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2Tu2_e3veV9M0wezAX7Fytkm9Y_HjOGp6vSB8xlEEvKa58BtKAUfJmL7S_M9iOShOk2CHnq0R20bd/pub?gid=1076902910&single=true&output=csv"
    df = pd.read_csv(cohorts_url)
    return df


# =====================================================
# GROWTH
# =====================================================

def apply_growth(baseline_cohorts, default_growth, custom_growth):
    growth_cohorts = {}
    for major, size in baseline_cohorts.items():
        if custom_growth and major in custom_growth:
            growth_rate = custom_growth[major] / 100
        else:
            growth_rate = default_growth / 100
        growth_cohorts[major] = int(size * (1 + growth_rate))
    return growth_cohorts


# =====================================================
# ONE SEMESTER OUTLOOK
# =====================================================

def run_one_semester_outlook(total_students, term="Fall", include_noise=True, override_counts=None):

    course_plans = load_course_plan()
    courses = load_courses()
    semester1_placements, semester2_placements = load_placements()
    cohort_df = load_cohort_percentages()

    results = []

    if override_counts is None:
        override_counts = {}

    year_map = {
        "Freshman": 1,
        "Sophomore": 2,
        "Junior": 3,
        "Senior": 4
    }

    # -------------------------------------------------
    # Compute freshman total across all selected majors
    # -------------------------------------------------
    freshman_total = sum(
        int(override_counts.get(major, 0) *
            (cohort_df[(cohort_df["major"] == major) & (cohort_df["year"] == "Freshman")]["cohort_percent"].values[0] /
             cohort_df[cohort_df["major"] == major]["cohort_percent"].sum())
        )
        for major in override_counts
        if len(cohort_df[(cohort_df["major"] == major) & (cohort_df["year"] == "Freshman")]) > 0
    )

    # -------------------------------------------------
    # PLACEMENT COURSES (Freshman only)
    # -------------------------------------------------
    placement_dict = semester1_placements if term == "Fall" else semester2_placements

    for course, pct in placement_dict.items():
        if course not in courses:
            continue
        enrollment = int(freshman_total * pct)
        if include_noise:
            enrollment = max(0, int(np.random.normal(enrollment, enrollment * 0.08)))
        capacity = courses[course][term]
        if capacity == 0:
            continue
        results.append({
            "major": "All",
            "course": course,
            "semester_number": f"{term} 1",
            "enrollment": enrollment,
            "capacity": capacity,
            "overage": enrollment - capacity
        })

    # -------------------------------------------------
    # MAJOR COURSES
    # -------------------------------------------------
    for major, major_total in override_counts.items():

        if major not in course_plans:
            continue

        major_rows = cohort_df[cohort_df["major"] == major]
        major_total_pct = major_rows["cohort_percent"].sum()

        if major_total_pct == 0:
            continue

        for _, row in major_rows.iterrows():

            year_name = row["year"]
            year_pct  = row["cohort_percent"]
            year_num  = year_map.get(year_name)

            if year_num is None:
                continue

            year_fraction = year_pct / major_total_pct
            cohort_size = int(major_total * year_fraction)
            semester_label = f"{term} {year_num}"

            for course_info in course_plans[major]:

                course = course_info["course"]

                if course not in courses:
                    continue

                if not (course_info["min_semester"] <= year_num <= course_info["max_semester"]):
                    continue

                enrollment = cohort_size
                if include_noise:
                    enrollment = max(0, int(np.random.normal(cohort_size, cohort_size * 0.08)))

                capacity = courses[course][term]
                if capacity == 0:
                    continue

                results.append({
                    "major": major,
                    "course": course,
                    "semester_number": semester_label,
                    "enrollment": enrollment,
                    "capacity": capacity,
                    "overage": enrollment - capacity
                })

    return results


# =====================================================
# SIMULATION ENGINE
# =====================================================

def simulate(course_plans, courses, cohort_sizes, max_semesters, semester1_placements, semester2_placements):

    results = []
    cohort_df = load_cohort_percentages()

    year_map = {
        "Freshman": 1,
        "Sophomore": 2,
        "Junior": 3,
        "Senior": 4
    }

    total_students = sum(cohort_sizes.values())

    # Pre-compute year-level cohort sizes for each major
    major_year_sizes = {}
    for major, total in cohort_sizes.items():
        major_year_sizes[major] = {}
        major_rows = cohort_df[cohort_df["major"] == major]
        major_total_pct = major_rows["cohort_percent"].sum()
        if major_total_pct == 0:
            continue
        for _, row in major_rows.iterrows():
            year_num = year_map.get(row["year"])
            if year_num is None:
                continue
            year_fraction = row["cohort_percent"] / major_total_pct
            major_year_sizes[major][year_num] = int(total * year_fraction)

    for semester_number in range(1, max_semesters + 1):

        term = "Fall" if semester_number % 2 == 1 else "Spring"
        year = (semester_number + 1) // 2
        semester_label = f"{term} {year}"

        # ---------------------------------------------
        # PLACEMENT COURSES
        # ---------------------------------------------
        if semester_number == 1:
            placement_dict = semester1_placements
        elif semester_number == 2:
            placement_dict = semester2_placements
        else:
            placement_dict = {}

        # Freshman total for placement courses
        freshman_total = sum(
            major_year_sizes.get(major, {}).get(1, 0)
            for major in cohort_sizes
        )

        for course, pct in placement_dict.items():
            if course not in courses:
                continue
            enrollment = int(freshman_total * pct)
            capacity = courses[course][term]
            results.append({
                "major": "All",
                "course": course,
                "semester_number": semester_label,
                "enrollment": enrollment,
                "capacity": capacity,
                "overage": enrollment - capacity
            })

        # ---------------------------------------------
        # MAJOR-SPECIFIC COURSES
        # ---------------------------------------------
        for major, year_sizes in major_year_sizes.items():

            if major not in course_plans:
                continue

            for year_num, cohort_size in year_sizes.items():

                if year_num != year:
                    continue

                enrollment = max(0, int(np.random.normal(cohort_size, cohort_size * 0.08)))

                for course_info in course_plans[major]:

                    course = course_info["course"]
                    min_sem = course_info["min_semester"]
                    max_sem = course_info["max_semester"]

                    if not (min_sem <= year_num <= max_sem):
                        continue

                    if course not in courses:
                        continue

                    capacity = courses[course][term]
                    if capacity == 0:
                        continue

                    results.append({
                        "major": major,
                        "course": course,
                        "semester_number": semester_label,
                        "enrollment": enrollment,
                        "capacity": capacity,
                        "overage": enrollment - capacity
                    })

    return results


# =====================================================
# SCENARIO RUNNER
# =====================================================

def run_scenarios(course_plans, courses, growth_scenarios, max_semesters, semester1_placements, semester2_placements, selected_major="All"):

    all_results = {}

    if selected_major != "All":
        if selected_major not in course_plans:
            raise ValueError(f"Major '{selected_major}' not found.")
        filtered_plans = {selected_major: course_plans[selected_major]}
    else:
        filtered_plans = course_plans

    for scenario_name, cohort_sizes in growth_scenarios.items():
        results = simulate(
            course_plans=filtered_plans,
            courses=courses,
            cohort_sizes=cohort_sizes,
            max_semesters=max_semesters,
            semester1_placements=semester1_placements,
            semester2_placements=semester2_placements
        )
        all_results[scenario_name] = results

    return all_results


# =====================================================
# RECOMMENDATIONS
# =====================================================

def generate_recommendations(scenario_results):
    recommendations = {}
    for scenario, bottlenecks in scenario_results.items():
        recommendations[scenario] = bottlenecks
    return recommendations


# =====================================================
# RUN MODEL
# =====================================================

def run_model(growth_percent, selected_major, max_semesters,
              custom_growth=None,
              advanced_selected_majors=None):

    if advanced_selected_majors is None:
        advanced_selected_majors = []

    course_plans = load_course_plan()
    baseline_cohorts = load_baseline_enrollments()
    courses = load_courses()
    semester1_placements, semester2_placements = load_placements()

    if advanced_selected_majors:
        baseline_cohorts = {
            major: size
            for major, size in baseline_cohorts.items()
            if major in advanced_selected_majors
        }
        course_plans = {
            major: plans
            for major, plans in course_plans.items()
            if major in advanced_selected_majors
        }

    growth_cohorts = apply_growth(baseline_cohorts, growth_percent, custom_growth)

    growth_scenarios = {
        f"{growth_percent}% Growth": growth_cohorts,
        "No Growth": baseline_cohorts
    }

    scenario_results = run_scenarios(
        course_plans=course_plans,
        courses=courses,
        growth_scenarios=growth_scenarios,
        max_semesters=max_semesters,
        semester1_placements=semester1_placements,
        semester2_placements=semester2_placements,
        selected_major=selected_major
    )

    return generate_recommendations(scenario_results)