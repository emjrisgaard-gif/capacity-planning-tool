import pandas as pd
import numpy as np

# ------------------------------------------
# Placement Percentages (First-Year Courses)
# ------------------------------------------

semester1_placements = {
    "CHEM103": 0.86,
    "CHEM109": 0.14,
    "MATH221": 0.40,
    "MATH222": 0.21,
    "MATH234": 0.20
}

semester2_placements = {
    "CHEM104": 0.86,
    "MATH222": 0.40,
    "MATH234": 0.20
}

# =====================================================
# DATA LOADING
# =====================================================

def load_courses(filepath):

    df = pd.read_csv(filepath)

    courses = {}
    for _, row in df.iterrows():
        courses[row["course_code"]] = {
            "Fall": row["fall_capacity"],
            "Spring": row["spring_capacity"]
        }

    return courses


def load_course_plan(filepath):

    df = pd.read_csv(filepath)

    course_plans = {}

    for _, row in df.iterrows():

        major = row["major"]
        course = row["course_code"]

        if major not in course_plans:
            course_plans[major] = []

        course_plans[major].append({
            "course": course,
            "min_semester": row["min_semester"],
            "max_semester": row["max_semester"]
        })

    return course_plans


def load_baseline_enrollments(filepath):

    df = pd.read_csv(filepath)

    baseline_cohorts = {}

    for _, row in df.iterrows():
        baseline_cohorts[row["major"]] = row["baseline_enrollment"]

    return baseline_cohorts


# =====================================================
# GROWTH
# =====================================================

def apply_growth(baseline_cohorts, growth_multiplier):

    growth_cohorts = {}

    for major, size in baseline_cohorts.items():
        growth_cohorts[major] = int(size * growth_multiplier)

    return growth_cohorts


# =====================================================
# SIMULATION ENGINE
# =====================================================

def simulate(course_plans, courses, cohort_sizes, max_semesters):

    bottlenecks = []

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

                if enrollment > capacity:

                    bottlenecks.append({
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

                if enrollment > capacity:

                    bottlenecks.append({
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

                if enrollment > capacity:

                    bottlenecks.append({
                        "major": major,
                        "course": course,
                        "semester_number": semester_label,
                        "enrollment": enrollment,
                        "capacity": capacity,
                        "overage": enrollment - capacity
                    })

    return bottlenecks


# =====================================================
# SCENARIO RUNNER
# =====================================================

def run_scenarios(course_plans, courses, growth_scenarios, max_semesters, selected_major="All"):

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
            max_semesters=max_semesters
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
# STREAMLIT ENTRY FUNCTION
# =====================================================

def run_model(growth_percent, selected_major, max_semesters):

    courses = load_courses("courses updated.csv")
    course_plans = load_course_plan("course_plan updated.csv")
    baseline_cohorts = load_baseline_enrollments("baseline_enrollment.csv")

    growth_multiplier = 1 + (growth_percent / 100)

    growth_cohorts = apply_growth(baseline_cohorts, growth_multiplier)

    growth_scenarios = {
        f"{growth_percent}% Growth": growth_cohorts,
        "No Growth": baseline_cohorts
    }

    scenario_results = run_scenarios(
        course_plans=course_plans,
        courses=courses,
        growth_scenarios=growth_scenarios,
        max_semesters=max_semesters,
        selected_major=selected_major
    )

    recommendations = generate_recommendations(scenario_results)

    return recommendations