import streamlit as st
import sqlite3
import hashlib

from datetime import datetime, date, timedelta

import pandas as pd
import plotly.express as px


# =========================================================
# BASIC CONFIGURATION
# =========================================================

DB = "nadis.db"

st.set_page_config(
    page_title="National Animal Disease Intelligence System",
    page_icon="🐄",
    layout="wide"
)


# =========================================================
# CUSTOM DESIGN
# =========================================================

st.markdown(
    """
    <style>
    .stApp {
        background: #f4f7f6;
    }

    [data-testid="stSidebar"] {
        background: #0b3d2e;
    }

    [data-testid="stSidebar"] * {
        color: white;
    }

    .hero {
        background: linear-gradient(120deg, #0b3d2e, #16865d);
        padding: 22px;
        border-radius: 16px;
        color: white;
        margin-bottom: 16px;
    }

    /* Form labels */
    .stTextInput label,
    .stNumberInput label,
    .stSelectbox label,
    .stMultiSelect label,
    .stTextArea label,
    .stDateInput label {
        color: #102820 !important;
        font-weight: 700 !important;
        font-size: 16px !important;
    }

    /* Input boxes */
    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea {
        color: white !important;
    }

    /* Help and description text */
    .stMarkdown,
    p {
        color: #102820;
    }
    </style>
    """,
    unsafe_allow_html=True
)
DB = "nadis.db"

def connect_database():
    connection = sqlite3.connect(
        DB,
        check_same_thread=False
    )

    connection.row_factory = sqlite3.Row

    return connection


def hash_password(password):
    return hashlib.sha256(
        password.encode()
    ).hexdigest()


def execute_query(sql, parameters=()):
    connection = connect_database()

    connection.execute(
        sql,
        parameters
    )

    connection.commit()
    connection.close()


def get_dataframe(sql, parameters=()):
    connection = connect_database()

    data = pd.read_sql_query(
        sql,
        connection,
        params=parameters
    )

    connection.close()

    return data
# =========================================================
# CREATE DATABASE TABLES
# =========================================================

def initialise_database():

    connection = connect_database()

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            district TEXT
        );

        CREATE TABLE IF NOT EXISTS animals(
            id INTEGER PRIMARY KEY,
            tag TEXT UNIQUE,
            owner TEXT,
            phone TEXT,
            species TEXT,
            breed TEXT,
            age REAL,
            sex TEXT,
            village TEXT,
            latitude REAL,
            longitude REAL,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS cases(
            id INTEGER PRIMARY KEY,
            case_no TEXT UNIQUE,
            owner TEXT,
            phone TEXT,
            tag TEXT,
            species TEXT,
            village TEXT,
            latitude REAL,
            longitude REAL,
            symptoms TEXT,
            affected INTEGER,
            deaths INTEGER,
            onset TEXT,
            risk TEXT,
            suspected TEXT,
            status TEXT,
            assigned TEXT,
            notes TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS vaccines(
            id INTEGER PRIMARY KEY,
            tag TEXT,
            owner TEXT,
            species TEXT,
            vaccine TEXT,
            given_date TEXT,
            next_due TEXT,
            batch TEXT,
            officer TEXT,
            village TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS labs(
            id INTEGER PRIMARY KEY,
            sample_id TEXT UNIQUE,
            case_no TEXT,
            sample_type TEXT,
            lab TEXT,
            status TEXT,
            result TEXT,
            remarks TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS alerts(
            id INTEGER PRIMARY KEY,
            title TEXT,
            message TEXT,
            severity TEXT,
            village TEXT,
            status TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS audit(
            id INTEGER PRIMARY KEY,
            username TEXT,
            action TEXT,
            details TEXT,
            created_at TEXT
        );
        """
    )

    default_users = [
        (
            "District Officer",
            "officer",
            "Officer@123",
            "District Officer"
        ),
        (
            "Veterinary Doctor",
            "vet",
            "Vet@123",
            "Veterinarian"
        ),
        (
            "Field Worker",
            "field",
            "Field@123",
            "Field Worker"
        ),
        (
            "Laboratory Officer",
            "lab",
            "Lab@123",
            "Lab Officer"
        )
    ]

    for name, username, password, role in default_users:

        connection.execute(
            """
            INSERT OR IGNORE INTO users(
                name,
                username,
                password,
                role,
                district
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                username,
                hash_password(password),
                role,
                "Tiruchirappalli"
            )
        )

    connection.commit()
    connection.close()


# =========================================================
# AUDIT LOG
# =========================================================

def add_audit_log(action, details=""):

    execute_query(
        """
        INSERT INTO audit(
            username,
            action,
            details,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            st.session_state.user["username"],
            action,
            details,
            datetime.now().isoformat(
                timespec="seconds"
            )
        )
    )


# =========================================================
# RULE-BASED TRIAGE
# =========================================================

def calculate_triage(
    symptoms,
    deaths,
    affected
):

    selected_symptoms = {
        symptom.lower()
        for symptom in symptoms
    }

    risk_score = 0
    suspected_disease = "General illness"

    if (
        "mouth lesions" in selected_symptoms
        and (
            "excess salivation" in selected_symptoms
            or "lameness" in selected_symptoms
        )
    ):
        suspected_disease = (
            "Suspected Foot-and-Mouth Disease"
        )

        risk_score += 5

    elif "skin nodules" in selected_symptoms:

        suspected_disease = (
            "Suspected lumpy skin condition"
        )

        risk_score += 5

    elif (
        "abortion" in selected_symptoms
        and "fever" in selected_symptoms
    ):

        suspected_disease = (
            "Suspected reproductive infection"
        )

        risk_score += 4

    elif (
        "breathing difficulty" in selected_symptoms
        and "nasal discharge" in selected_symptoms
    ):

        suspected_disease = (
            "Suspected respiratory infection"
        )

        risk_score += 4

    elif (
        "diarrhoea" in selected_symptoms
        and "fever" in selected_symptoms
    ):

        suspected_disease = (
            "Suspected enteric infection"
        )

        risk_score += 3

    if "fever" in selected_symptoms:
        risk_score += 1

    if deaths >= 2:
        risk_score += 4

    elif deaths == 1:
        risk_score += 2

    if affected >= 5:
        risk_score += 2

    if risk_score >= 7:
        risk = "Critical"

    elif risk_score >= 5:
        risk = "High"

    elif risk_score >= 3:
        risk = "Medium"

    else:
        risk = "Low"

    return risk, suspected_disease


# =========================================================
# OUTBREAK CLUSTER DETECTION
# =========================================================

def detect_outbreak_cluster(
    village,
    suspected_disease
):

    last_seven_days = (
        datetime.now() - timedelta(days=7)
    ).isoformat(timespec="seconds")

    connection = connect_database()

    number_of_cases = connection.execute(
        """
        SELECT COUNT(*)
        FROM cases
        WHERE village = ?
        AND suspected = ?
        AND created_at >= ?
        """,
        (
            village,
            suspected_disease,
            last_seven_days
        )
    ).fetchone()[0]

    existing_alert = connection.execute(
        """
        SELECT COUNT(*)
        FROM alerts
        WHERE village = ?
        AND title = 'Suspected outbreak cluster'
        AND status = 'Active'
        """,
        (village,)
    ).fetchone()[0]

    if (
        number_of_cases >= 3
        and not existing_alert
    ):

        connection.execute(
            """
            INSERT INTO alerts(
                title,
                message,
                severity,
                village,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "Suspected outbreak cluster",
                (
                    f"{number_of_cases} related reports "
                    f"detected during the last seven days. "
                    f"Veterinary verification is required."
                ),
                "Critical",
                village,
                "Active",
                datetime.now().isoformat(
                    timespec="seconds"
                )
            )
        )

    connection.commit()
    connection.close()


# Initialise the database

initialise_database()


# =========================================================
# USER SESSION
# =========================================================

if "user" not in st.session_state:
    st.session_state.user = None


# =========================================================
# LOGIN PAGE
# =========================================================

if not st.session_state.user:

    st.markdown(
        """
        <div class="hero">
            <h1>🐄 National Animal disease Intelligence System</h1>
            <h3>
                National Animal Disease Intelligence System
            </h3>
            <p>
                Department of Animal Husbandry and Dairying
                Government of India
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    left_column, middle_column, right_column = (
        st.columns([1, 1.1, 1])
    )

    with middle_column:

        st.subheader("Secure Login")

        username = st.text_input(
            "Username"
        )

        password = st.text_input(
            "Password",
            type="password"
        )

        if st.button(
            "Sign in",
            use_container_width=True,
            type="primary"
        ):

            connection = connect_database()

            user = connection.execute(
                """
                SELECT *
                FROM users
                WHERE username = ?
                AND password = ?
                """,
                (
                    username,
                    hash_password(password)
                )
            ).fetchone()

            connection.close()

            if user:

                st.session_state.user = dict(user)

                st.rerun()

            else:

                st.error(
                    "Invalid username or password"
                )

        with st.expander(
            "Demo login details"
        ):

            st.code(
                """
officer / Officer@123
vet / Vet@123
field / Field@123
lab / Lab@123
                """
            )

        st.caption(
            "Prototype only. Veterinary diagnosis "
            "requires professional confirmation."
        )

    st.stop()


# =========================================================
# SIDEBAR
# =========================================================

logged_in_user = st.session_state.user

with st.sidebar:

    st.markdown("## 🐄 National Animal Disease Intelligence System")

    st.write(
        f"**{logged_in_user['name']}**"
    )

    st.caption(
        logged_in_user["role"]
    )

    selected_page = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Report Case",
            "Case Management",
            "Animal Registry",
            "Vaccination",
            "Laboratory",
            "Alerts",
            "Reports"
        ]
    )

    st.divider()

    if st.button(
        "Logout",
        use_container_width=True
    ):

        st.session_state.user = None

        st.rerun()


st.markdown(
    f"""
    <div class="hero">
        <h2>{selected_page}</h2>
        <b>{logged_in_user["role"]}</b>
        |
        Tiruchirappalli District
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# DASHBOARD
# =========================================================

if selected_page == "Dashboard":

    cases = get_dataframe(
        """
        SELECT *
        FROM cases
        ORDER BY id DESC
        """
    )

    animals = get_dataframe(
        "SELECT * FROM animals"
    )

    vaccinations = get_dataframe(
        "SELECT * FROM vaccines"
    )

    alerts = get_dataframe(
        """
        SELECT *
        FROM alerts
        WHERE status = 'Active'
        """
    )

    metric_columns = st.columns(5)

    metric_columns[0].metric(
        "Total cases",
        len(cases)
    )

    if len(cases):

        high_risk_count = len(
            cases[
                cases["risk"].isin(
                    ["High", "Critical"]
                )
            ]
        )

    else:
        high_risk_count = 0

    metric_columns[1].metric(
        "High / Critical",
        high_risk_count
    )

    metric_columns[2].metric(
        "Registered animals",
        len(animals)
    )

    metric_columns[3].metric(
        "Vaccinations",
        len(vaccinations)
    )

    metric_columns[4].metric(
        "Active alerts",
        len(alerts)
    )

    for index, alert in alerts.iterrows():

        st.error(
            f"🚨 {alert['title']} | "
            f"{alert['village']}: "
            f"{alert['message']}"
        )

    if len(cases):

        left_chart, right_chart = st.columns(2)

        risk_summary = (
            cases
            .groupby("risk")
            .size()
            .reset_index(name="Cases")
        )

        risk_chart = px.bar(
            risk_summary,
            x="risk",
            y="Cases",
            color="risk",
            title="Cases by risk level"
        )

        left_chart.plotly_chart(
            risk_chart,
            use_container_width=True
        )

        status_chart = px.pie(
            cases,
            names="status",
            title="Case status"
        )

        right_chart.plotly_chart(
            status_chart,
            use_container_width=True
        )

        map_data = (
            cases
            .dropna(
                subset=[
                    "latitude",
                    "longitude"
                ]
            )
            .rename(
                columns={
                    "latitude": "lat",
                    "longitude": "lon"
                }
            )
        )

        if len(map_data):

            st.subheader(
                "Geospatial disease-risk map"
            )

            st.map(
                map_data[["lat", "lon"]]
            )

        st.subheader(
            "Latest reported cases"
        )

        st.dataframe(
            cases[
                [
                    "case_no",
                    "village",
                    "species",
                    "suspected",
                    "risk",
                    "status"
                ]
            ].head(10),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No cases have been reported. "
            "Create the first report from Report Case."
        )


# =========================================================
# REPORT CASE
# =========================================================

elif selected_page == "Report Case":

    st.info(
        "This is a decision-support triage system. "
        "A registered veterinarian must verify "
        "the final diagnosis."
    )

    with st.form(
        "case_form",
        clear_on_submit=True
    ):

        column1, column2, column3 = (
            st.columns(3)
        )

        owner = column1.text_input(
            "Owner / Farmer name*"
        )

        phone = column2.text_input(
            "Phone number"
        )

        animal_tag = column3.text_input(
            "Animal tag / Herd ID"
        )

        column1, column2 = st.columns(2)

        species = column1.selectbox(
            "Species",
            [
                "Cattle",
                "Buffalo",
                "Goat",
                "Sheep",
                "Pig",
                "Poultry"
            ]
        )

        village = column2.text_input(
            "Village*"
        )

        symptoms = st.multiselect(
            "Observed symptoms*",
            [
                "Fever",
                "Mouth lesions",
                "Excess salivation",
                "Lameness",
                "Diarrhoea",
                "Nasal discharge",
                "Breathing difficulty",
                "Abortion",
                "Skin nodules",
                "Loss of appetite",
                "Sudden weakness"
            ]
        )

        column1, column2, column3 = (
            st.columns(3)
        )

        affected = column1.number_input(
            "Animals affected",
            min_value=1,
            max_value=100000,
            value=1
        )

        deaths = column2.number_input(
            "Animal deaths",
            min_value=0,
            max_value=100000,
            value=0
        )

        onset_date = column3.date_input(
            "Symptom onset date",
            date.today()
        )

        column1, column2 = st.columns(2)

        latitude = column1.number_input(
            "Latitude",
            value=10.7905,
            format="%.6f"
        )

        longitude = column2.number_input(
            "Longitude",
            value=78.7047,
            format="%.6f"
        )

        notes = st.text_area(
            "Additional field notes"
        )

        submitted = st.form_submit_button(
            "Submit and run triage",
            type="primary",
            use_container_width=True
        )

    if submitted:

        if (
            not owner
            or not village
            or not symptoms
        ):

            st.error(
                "Complete all required fields."
            )

        else:

            risk, suspected_disease = (
                calculate_triage(
                    symptoms,
                    int(deaths),
                    int(affected)
                )
            )

            case_number = (
                "PK-"
                + datetime.now().strftime(
                    "%Y%m%d%H%M%S%f"
                )
            )

            execute_query(
                """
                INSERT INTO cases(
                    case_no,
                    owner,
                    phone,
                    tag,
                    species,
                    village,
                    latitude,
                    longitude,
                    symptoms,
                    affected,
                    deaths,
                    onset,
                    risk,
                    suspected,
                    status,
                    assigned,
                    notes,
                    created_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    case_number,
                    owner,
                    phone,
                    animal_tag,
                    species,
                    village,
                    latitude,
                    longitude,
                    ", ".join(symptoms),
                    affected,
                    deaths,
                    str(onset_date),
                    risk,
                    suspected_disease,
                    "Reported",
                    "Unassigned",
                    notes,
                    datetime.now().isoformat(
                        timespec="seconds"
                    )
                )
            )

            add_audit_log(
                "CREATE_CASE",
                case_number
            )

            detect_outbreak_cluster(
                village,
                suspected_disease
            )

            st.success(
                f"Case {case_number} created | "
                f"Risk: {risk} | "
                f"{suspected_disease}"
            )

            if risk in [
                "High",
                "Critical"
            ]:

                st.error(
                    "Priority veterinary review is required. "
                    "Isolate affected animals pending "
                    "professional assessment."
                )


# =========================================================
# CASE MANAGEMENT
# =========================================================

elif selected_page == "Case Management":

    case_data = get_dataframe(
        """
        SELECT *
        FROM cases
        ORDER BY id DESC
        """
    )

    if not len(case_data):

        st.info(
            "No cases are currently available."
        )

    else:

        st.dataframe(
            case_data[
                [
                    "case_no",
                    "owner",
                    "village",
                    "risk",
                    "suspected",
                    "status",
                    "assigned"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        selected_case = st.selectbox(
            "Select case",
            case_data["case_no"].tolist()
        )

        selected_row = case_data[
            case_data["case_no"]
            == selected_case
        ].iloc[0]

        st.write(
            f"**Symptoms:** "
            f"{selected_row['symptoms']}"
        )

        st.write(
            f"**Affected animals:** "
            f"{selected_row['affected']}"
        )

        st.write(
            f"**Deaths:** "
            f"{selected_row['deaths']}"
        )

        status_options = [
            "Reported",
            "Assigned",
            "Field Visit",
            "Sample Collected",
            "Under Treatment",
            "Confirmed",
            "Contained",
            "Closed"
        ]

        current_status_index = (
            status_options.index(
                selected_row["status"]
            )
            if selected_row["status"]
            in status_options
            else 0
        )

        new_status = st.selectbox(
            "Case status",
            status_options,
            index=current_status_index
        )

        assigned_officer = st.text_input(
            "Assigned veterinary officer",
            selected_row["assigned"]
        )

        updated_notes = st.text_area(
            "Case notes",
            selected_row["notes"] or ""
        )

        if st.button(
            "Update case",
            type="primary"
        ):

            execute_query(
                """
                UPDATE cases
                SET status = ?,
                    assigned = ?,
                    notes = ?
                WHERE case_no = ?
                """,
                (
                    new_status,
                    assigned_officer,
                    updated_notes,
                    selected_case
                )
            )

            add_audit_log(
                "UPDATE_CASE",
                selected_case
            )

            st.success(
                "Case updated successfully."
            )

            st.rerun()


# =========================================================
# ANIMAL REGISTRY
# =========================================================

elif selected_page == "Animal Registry":

    with st.form(
        "animal_form",
        clear_on_submit=True
    ):

        column1, column2, column3 = (
            st.columns(3)
        )

        tag = column1.text_input(
            "Unique animal tag / Herd ID*"
        )

        owner = column2.text_input(
            "Owner name*"
        )

        phone = column3.text_input(
            "Phone number"
        )

        column1, column2, column3, column4 = (
            st.columns(4)
        )

        species = column1.selectbox(
            "Species",
            [
                "Cattle",
                "Buffalo",
                "Goat",
                "Sheep",
                "Pig",
                "Poultry"
            ]
        )

        breed = column2.text_input(
            "Breed"
        )

        animal_age = column3.number_input(
            "Age in years",
            min_value=0.0,
            max_value=50.0,
            value=1.0
        )

        animal_sex = column4.selectbox(
            "Sex",
            [
                "Female",
                "Male",
                "Mixed herd",
                "Unknown"
            ]
        )

        column1, column2, column3 = (
            st.columns(3)
        )

        village = column1.text_input(
            "Village*"
        )

        latitude = column2.number_input(
            "Latitude",
            value=10.7905
        )

        longitude = column3.number_input(
            "Longitude",
            value=78.7047
        )

        save_animal = (
            st.form_submit_button(
                "Register animal / herd",
                type="primary"
            )
        )

    if save_animal:

        if not tag or not owner or not village:

            st.error(
                "Complete all required fields."
            )

        else:

            try:

                execute_query(
                    """
                    INSERT INTO animals(
                        tag,
                        owner,
                        phone,
                        species,
                        breed,
                        age,
                        sex,
                        village,
                        latitude,
                        longitude,
                        created_at
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        tag,
                        owner,
                        phone,
                        species,
                        breed,
                        animal_age,
                        animal_sex,
                        village,
                        latitude,
                        longitude,
                        datetime.now().isoformat(
                            timespec="seconds"
                        )
                    )
                )

                add_audit_log(
                    "REGISTER_ANIMAL",
                    tag
                )

                st.success(
                    "Animal or herd registered."
                )

            except sqlite3.IntegrityError:

                st.error(
                    "This animal tag already exists."
                )

    animal_data = get_dataframe(
        """
        SELECT *
        FROM animals
        ORDER BY id DESC
        """
    )

    st.subheader(
        "Registered animals and herds"
    )

    st.dataframe(
        animal_data,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# VACCINATION
# =========================================================

elif selected_page == "Vaccination":

    with st.form(
        "vaccination_form",
        clear_on_submit=True
    ):

        column1, column2, column3 = (
            st.columns(3)
        )

        tag = column1.text_input(
            "Animal tag / Herd ID"
        )

        owner = column2.text_input(
            "Owner name*"
        )

        species = column3.selectbox(
            "Species",
            [
                "Cattle",
                "Buffalo",
                "Goat",
                "Sheep",
                "Pig",
                "Poultry"
            ]
        )

        column1, column2, column3 = (
            st.columns(3)
        )

        vaccine = column1.selectbox(
            "Vaccine",
            [
                "FMD",
                "Brucellosis",
                "PPR",
                "HS",
                "BQ",
                "CSF",
                "Enterotoxaemia",
                "Other"
            ]
        )

        given_date = column2.date_input(
            "Vaccination date",
            date.today()
        )

        next_due_date = column3.date_input(
            "Next due date",
            date.today()
            + timedelta(days=180)
        )

        column1, column2, column3 = (
            st.columns(3)
        )

        batch_number = column1.text_input(
            "Vaccine batch number"
        )

        vaccination_officer = (
            column2.text_input(
                "Vaccinating officer",
                logged_in_user["name"]
            )
        )

        village = column3.text_input(
            "Village*"
        )

        save_vaccination = (
            st.form_submit_button(
                "Save vaccination",
                type="primary"
            )
        )

    if save_vaccination:

        if not owner or not village:

            st.error(
                "Complete all required fields."
            )

        else:

            execute_query(
                """
                INSERT INTO vaccines(
                    tag,
                    owner,
                    species,
                    vaccine,
                    given_date,
                    next_due,
                    batch,
                    officer,
                    village,
                    created_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?
                )
                """,
                (
                    tag,
                    owner,
                    species,
                    vaccine,
                    str(given_date),
                    str(next_due_date),
                    batch_number,
                    vaccination_officer,
                    village,
                    datetime.now().isoformat(
                        timespec="seconds"
                    )
                )
            )

            add_audit_log(
                "ADD_VACCINATION",
                tag
            )

            st.success(
                "Vaccination record saved."
            )

    vaccination_data = get_dataframe(
        """
        SELECT *
        FROM vaccines
        ORDER BY id DESC
        """
    )

    if len(vaccination_data):

        vaccination_data["next_due_date"] = (
            pd.to_datetime(
                vaccination_data["next_due"]
            )
        )

        upcoming_date = (
            pd.Timestamp.today()
            + pd.Timedelta(days=30)
        )

        due_vaccinations = vaccination_data[
            vaccination_data[
                "next_due_date"
            ] <= upcoming_date
        ]

        st.metric(
            "Vaccinations overdue or due within 30 days",
            len(due_vaccinations)
        )

    st.dataframe(
        vaccination_data,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# LABORATORY
# =========================================================

elif selected_page == "Laboratory":

    available_cases = get_dataframe(
        """
        SELECT case_no
        FROM cases
        ORDER BY id DESC
        """
    )

    if len(available_cases):

        case_options = (
            available_cases[
                "case_no"
            ].tolist()
        )

    else:

        case_options = ["No case available"]

    with st.form(
        "laboratory_form",
        clear_on_submit=True
    ):

        column1, column2 = st.columns(2)

        related_case = column1.selectbox(
            "Related case",
            case_options
        )

        sample_id = column2.text_input(
            "Sample ID*",
            value=(
                "SMP-"
                + datetime.now().strftime(
                    "%Y%m%d%H%M%S"
                )
            )
        )

        column1, column2, column3 = (
            st.columns(3)
        )

        sample_type = column1.selectbox(
            "Sample type",
            [
                "Blood",
                "Serum",
                "Swab",
                "Tissue",
                "Faecal",
                "Other"
            ]
        )

        laboratory_name = (
            column2.text_input(
                "Laboratory",
                "District Veterinary Laboratory"
            )
        )

        laboratory_status = (
            column3.selectbox(
                "Laboratory status",
                [
                    "Collected",
                    "In Transit",
                    "Received",
                    "Testing",
                    "Completed"
                ]
            )
        )

        laboratory_result = st.selectbox(
            "Laboratory result",
            [
                "Pending",
                "Negative",
                "Positive",
                "Inconclusive"
            ]
        )

        laboratory_remarks = st.text_area(
            "Laboratory remarks"
        )

        save_sample = (
            st.form_submit_button(
                "Save sample / result",
                type="primary"
            )
        )

    if save_sample:

        try:

            execute_query(
                """
                INSERT INTO labs(
                    sample_id,
                    case_no,
                    sample_type,
                    lab,
                    status,
                    result,
                    remarks,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?
                )
                """,
                (
                    sample_id,
                    related_case,
                    sample_type,
                    laboratory_name,
                    laboratory_status,
                    laboratory_result,
                    laboratory_remarks,
                    datetime.now().isoformat(
                        timespec="seconds"
                    )
                )
            )

            if laboratory_status == "Completed":

                execute_query(
                    """
                    UPDATE cases
                    SET status = 'Confirmed'
                    WHERE case_no = ?
                    """,
                    (related_case,)
                )

            add_audit_log(
                "LAB_UPDATE",
                sample_id
            )

            st.success(
                "Laboratory record saved."
            )

        except sqlite3.IntegrityError:

            st.error(
                "This sample ID already exists."
            )

    laboratory_data = get_dataframe(
        """
        SELECT *
        FROM labs
        ORDER BY id DESC
        """
    )

    st.dataframe(
        laboratory_data,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# ALERTS
# =========================================================

elif selected_page == "Alerts":

    with st.form(
        "alert_form",
        clear_on_submit=True
    ):

        column1, column2 = st.columns(2)

        alert_title = column1.text_input(
            "Alert title*"
        )

        alert_severity = column2.selectbox(
            "Alert severity",
            [
                "Information",
                "Warning",
                "High",
                "Critical"
            ]
        )

        alert_message = st.text_area(
            "Multilingual advisory / message*"
        )

        alert_village = st.text_input(
            "Village or affected area"
        )

        publish_alert = (
            st.form_submit_button(
                "Publish alert",
                type="primary"
            )
        )

    if publish_alert:

        if not alert_title or not alert_message:

            st.error(
                "Enter alert title and message."
            )

        else:

            execute_query(
                """
                INSERT INTO alerts(
                    title,
                    message,
                    severity,
                    village,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    alert_title,
                    alert_message,
                    alert_severity,
                    alert_village,
                    "Active",
                    datetime.now().isoformat(
                        timespec="seconds"
                    )
                )
            )

            add_audit_log(
                "PUBLISH_ALERT",
                alert_title
            )

            st.success(
                "Government advisory published."
            )

    alerts_data = get_dataframe(
        """
        SELECT *
        FROM alerts
        ORDER BY id DESC
        """
    )

    st.dataframe(
        alerts_data,
        use_container_width=True,
        hide_index=True
    )

    active_alerts = alerts_data[
        alerts_data["status"] == "Active"
    ] if len(alerts_data) else pd.DataFrame()

    if len(active_alerts):

        selected_alert_id = st.selectbox(
            "Select active alert to resolve",
            active_alerts["id"].tolist()
        )

        if st.button(
            "Mark alert as resolved"
        ):

            execute_query(
                """
                UPDATE alerts
                SET status = 'Resolved'
                WHERE id = ?
                """,
                (int(selected_alert_id),)
            )

            add_audit_log(
                "RESOLVE_ALERT",
                str(selected_alert_id)
            )

            st.success(
                "Alert marked as resolved."
            )

            st.rerun()


# =========================================================
# REPORTS
# =========================================================

elif selected_page == "Reports":

    st.subheader(
        "Downloadable Government Reports"
    )

    selected_dataset = st.selectbox(
        "Select report",
        [
            "Cases",
            "Animals",
            "Vaccinations",
            "Laboratory",
            "Alerts",
            "Audit Log"
        ]
    )

    table_mapping = {
        "Cases": "cases",
        "Animals": "animals",
        "Vaccinations": "vaccines",
        "Laboratory": "labs",
        "Alerts": "alerts",
        "Audit Log": "audit"
    }

    selected_table = (
        table_mapping[
            selected_dataset
        ]
    )

    report_data = get_dataframe(
        f"""
        SELECT *
        FROM {selected_table}
        ORDER BY id DESC
        """
    )

    st.dataframe(
        report_data,
        use_container_width=True,
        hide_index=True
    )

    csv_data = report_data.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="Download CSV Report",
        data=csv_data,
        file_name=(
            f"National Animal Disease Intelligence System_"
            f"{selected_table}_"
            f"{date.today()}.csv"
        ),
        mime="text/csv",
        use_container_width=True
    )

    if (
        selected_dataset == "Cases"
        and len(report_data)
    ):

        village_summary = (
            report_data
            .groupby(
                [
                    "village",
                    "risk"
                ]
            )
            .size()
            .reset_index(
                name="case_count"
            )
        )

        st.subheader(
            "Village Risk Summary"
        )

        st.dataframe(
            village_summary,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    " National Animal Disease Intelligence System (NADIS) | "
    "Prototype decision-support system only | "
    "Not a substitute for veterinary diagnosis"
)