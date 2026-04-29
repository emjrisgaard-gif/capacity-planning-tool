import pandas as pd
import numpy as np

# ------------------------------------------
# Placement Percentages (First-Year Courses)
# ------------------------------------------

# =====================================================
# GOOGLE SHEET URLS
# =====================================================

COURSE_PLANS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2Tu2_e3veV9M0wezAX7Fytkm9Y_HjOGp6vSB8xlEEvKa58BtKAUfJmL7S_M9iOShOk2CHnq0R20bd/pub?gid=0&single=true&output=csv"

ENROLLMENTS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2Tu2_e3veV9M0wezAX7Fytkm9Y_HjOGp6vSB8xlEEvKa58BtKAUfJmL7S_M9iOShOk2CHnq0R20bd/pub?gid=1260404694&single=true&output=csv"

CAPACITIES_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2Tu2_e3veV9M0wezAX7Fytkm9Y_HjOGp6vSB8xlEEvKa58BtKAUfJmL7S_M9iOShOk2CHnq0R20bd/pub?gid=4062538&single=true&output=csv"

PLACEMENTS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2Tu2_e3veV9M0wezAX7Fytkm9Y_HjOGp6vSB8xlEEvKa58BtKAUfJmL7S_M9iOShOk2CHnq0R20bd/pub?gid=1044514389&single=true&output=csv"

# =====================================================
# LOAD FUNCTIONS (NEW)
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

def load_cohorts():
    cohorts_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2Tu2_e3veV9M0wezAX7Fytkm9Y_HjOGp6vSB8xlEEvKa58BtKAUfJmL7S_M9iOShOk2CHnq0R20bd/pub?gid=1076902910&single=true&output=csv"

    df = pd.read_csv(cohorts_url)

    cohorts = {}

    for _, row in df.iterrows():

        major = row["major"]
        year = row["year"]
        size = row["cohort_size"]

        if major not in cohorts:
            cohorts[major] = {}

        cohorts[major][year] = size

    return cohorts
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

def run_one_semester_outlook(selected_majors, growth_percent, term="Fall", include_noise=True):

    course_plans = load_course_plan()
    courses = load_courses()
    cohorts = load_cohorts()
    semester1_placements, semester2_placements = load_placements()

    results = []

    if selected_majors:
        cohorts = {m: cohorts[m] for m in selected_majors if m in cohorts}
        course_plans = {m: course_plans[m] for m in selected_majors if m in course_plans}

    # -------------------------------------------------
    # APPLY GROWTH
    # -------------------------------------------------

    for major in cohorts:
        for year in cohorts[major]:

            base = cohorts[major][year]
            growth = base * (growth_percent / 100)
            cohorts[major][year] = int(base + growth)

    # -------------------------------------------------
    # PLACEMENT COURSES (Freshman only)
    # -------------------------------------------------

    freshman_total = sum(
        cohorts[major].get("Freshman", 0)
        for major in cohorts
    )

    placement_dict = semester1_placements if term == "Fall" else semester2_placements

    semester_label = f"{term} 1"

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
            "semester_number": semester_label,
            "enrollment": enrollment,
            "capacity": capacity,
            "overage": enrollment - capacity
        })

    # -------------------------------------------------
    # MAJOR COURSES
    # -------------------------------------------------

    year_map = {
        "Freshman": 1,
        "Sophomore": 2,
        "Junior": 3,
        "Senior": 4
    }

    for major, years in cohorts.items():

        if major not in course_plans:
            continue

        for year_name, cohort_size in years.items():

            year_num = year_map.get(year_name)

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

    # total incoming students across all majors
    total_students = sum(cohort_sizes.values())

    for semester_number in range(1, max_semesters + 1):

        # Determine term
        if semester_number % 2 == 1:
            term = "Fall"
        else:
            term = "Spring"

        # Determine academic year
        year = (semester_number + 1) // 2
        semester_label = f"{term} {year}"

        # =====================================================
        # SEMESTER 1 PLACEMENT COURSES
        # =====================================================

        if semester_number == 1:

            for course, pct in semester1_placements.items():

                if course not in courses:
                    continue

                enrollment = int(total_students * pct)
                capacity = courses[course][term]

                results.append({
    "major": "All",
    "course": course,
    "semester_number": semester_label,
    "enrollment": enrollment,
    "capacity": capacity,
    "overage": enrollment - capacity
})

        # =====================================================
        # SEMESTER 2 PLACEMENT COURSES
        # =====================================================

        if semester_number == 2:

            for course, pct in semester2_placements.items():

                if course not in courses:
                    continue

                enrollment = int(total_students * pct)
                capacity = courses[course][term]

                results.append({
    "major": "All",
    "course": course,
    "semester_number": semester_label,
    "enrollment": enrollment,
    "capacity": capacity,
    "overage": enrollment - capacity
})

        # =====================================================
        # MAJOR-SPECIFIC COURSES
        # =====================================================

        for major, size in cohort_sizes.items():

            # enrollment noise ±8%
            enrollment = max(0, int(np.random.normal(size, size * 0.08)))

            if major not in course_plans:
                continue

            required_courses = course_plans[major]

            for course_info in required_courses:

                course = course_info["course"]
                min_sem = course_info["min_semester"]
                max_sem = course_info["max_semester"]

                if not (min_sem <= semester_number <= max_sem):
                    continue

                if course not in courses:
                    continue

                capacity = courses[course][term]

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
            max_semesters=max_semesters, semester1_placements=semester1_placements, semester2_placements=semester2_placements
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


def run_model(growth_percent, selected_major, max_semesters,
              custom_growth=None,
              advanced_selected_majors=None):
    semester1_placements, semester2_placements = load_placements()

    if advanced_selected_majors is None:
        advanced_selected_majors = []

    # ------------------------------------------
    # LOAD DATA FROM GOOGLE SHEETS
    # ------------------------------------------

    course_plans = load_course_plan()
    baseline_cohorts = load_baseline_enrollments()
    courses = load_courses()
    semester1_placements, semester2_placements = load_placements()

    # ------------------------------------------
    # Advanced override logic
    # ------------------------------------------

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

    # ------------------------------------------
    # Apply growth
    # ------------------------------------------

    growth_cohorts = apply_growth(
        baseline_cohorts,
        growth_percent,
        custom_growth
    )

    growth_scenarios = {
        f"{growth_percent}% Growth": growth_cohorts,
        "No Growth": baseline_cohorts
    }

    # ------------------------------------------
    # Run simulation
    # ------------------------------------------

    scenario_results = run_scenarios(
        course_plans=course_plans,
        courses=courses,
        growth_scenarios=growth_scenarios,
        max_semesters=max_semesters, semester1_placements=semester1_placements, semester2_placements=semester2_placements,
        selected_major=selected_major
    )

    return generate_recommendations(scenario_results)

