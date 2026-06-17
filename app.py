import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path
import qrcode
import re

DB_PATH = Path("seed_inventory.db")
APP_URL = "https://tobacco-seed-inventory.streamlit.app"

st.set_page_config(page_title="Tobacco Seed Inventory Demo", layout="wide")

st.title("Tobacco Seed Inventory System - Demo")
st.caption("Seed inventory, freezer tracking, germination reminders, QR workflow, and import/export tools.")


def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM accessions", conn)
    conn.close()
    return df


def save_record(record):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO accessions (
            accession_id, line_name, pedigree, generation, year_produced,
            quantity_available, freezer_location, germination_percent,
            last_tested, disease_resistance, quality_traits, notes, photo_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, record)
    conn.commit()
    conn.close()


def get_record(df, accession_id):
    subset = df[df["accession_id"] == accession_id]
    if len(subset) == 0:
        return None
    return subset.iloc[0].to_dict()


def generate_direct_qr(accession_id):
    qr_dir = Path("qr_codes")
    qr_dir.mkdir(exist_ok=True)
    direct_url = f"{APP_URL}/?accession={accession_id}"
    qr_path = qr_dir / f"{accession_id}_direct.png"
    img = qrcode.make(direct_url)
    img.save(qr_path)
    return qr_path, direct_url


def split_freezer_location(df):
    df = df.copy()
    extracted = df["freezer_location"].astype(str).str.extract(
        r"F(?P<Freezer>\d+)-S(?P<Shelf>\d+)-B(?P<Box>\d+)-P(?P<Packet>\d+)",
        flags=re.IGNORECASE
    )
    df["Freezer"] = extracted["Freezer"]
    df["Shelf"] = extracted["Shelf"]
    df["Box"] = extracted["Box"]
    df["Packet"] = extracted["Packet"]
    return df


def dashboard_tab(df):
    st.subheader("Dashboard")

    germ = pd.to_numeric(df["germination_percent"], errors="coerce")

    reminder_df = df.copy()
    reminder_df["last_tested_date"] = pd.to_datetime(reminder_df["last_tested"], errors="coerce")
    reminder_df["days_since_tested"] = (
        pd.Timestamp.today().normalize() - reminder_df["last_tested_date"]
    ).dt.days
    reminder_df["germination_percent"] = pd.to_numeric(reminder_df["germination_percent"], errors="coerce")

    retest_due = len(reminder_df[reminder_df["days_since_tested"] >= 5 * 365])
    low_germination = len(reminder_df[reminder_df["germination_percent"] < 75])
    missing_test_date = len(reminder_df[reminder_df["last_tested_date"].isna()])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Accessions", len(df))
    c2.metric("Freezer Locations", df["freezer_location"].nunique())
    c3.metric("Average Germination", f"{germ.mean():.1f}%")
    c4.metric("Needs Attention", retest_due + low_germination + missing_test_date)

    st.divider()

    st.markdown("### Germination Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Retest Due", retest_due)
    c2.metric("Low Germination", low_germination)
    c3.metric("Missing Test Date", missing_test_date)

    st.divider()

    st.markdown("### Inventory Overview")
    st.dataframe(
        df[
            [
                "accession_id",
                "line_name",
                "generation",
                "year_produced",
                "germination_percent",
                "last_tested",
                "freezer_location"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )


def freezer_map_tab(df):
    st.subheader("Visual Freezer Map")

    st.markdown("""
    Location format: **F1-S2-B3-P7**  
    Freezer 1 → Shelf 2 → Box 3 → Packet 7
    """)

    map_df = split_freezer_location(df)
    valid_df = map_df.dropna(subset=["Freezer", "Shelf", "Box", "Packet"]).copy()

    if valid_df.empty:
        st.warning("No valid freezer locations found. Use format like F1-S2-B3-P7.")
        return

    freezer_options = sorted(valid_df["Freezer"].unique(), key=lambda x: int(x))

    selected_freezer = st.selectbox(
        "Select Freezer",
        freezer_options,
        format_func=lambda x: f"Freezer {x}"
    )

    freezer_df = valid_df[valid_df["Freezer"] == selected_freezer].copy()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Accessions", freezer_df["accession_id"].nunique())
    c2.metric("Shelves Used", freezer_df["Shelf"].nunique())
    c3.metric("Boxes Used", freezer_df["Box"].nunique())
    c4.metric("Packets Used", freezer_df["Packet"].count())

    st.markdown(f"## Freezer {selected_freezer}")

    shelves = sorted(freezer_df["Shelf"].unique(), key=lambda x: int(x))

    for shelf in shelves:
        shelf_df = freezer_df[freezer_df["Shelf"] == shelf].copy()

        st.markdown("---")
        st.markdown(f"### Shelf {shelf}")

        boxes = sorted(shelf_df["Box"].unique(), key=lambda x: int(x))
        cols = st.columns(6)

        for i, box in enumerate(boxes):
            box_df = shelf_df[shelf_df["Box"] == box].copy()
            packet_count = box_df["Packet"].count()

            with cols[i % 6]:
                st.info(f"Box {box}\n\n{packet_count} packets")

    st.divider()

    st.subheader("Open Box Contents")

    shelf_pick = st.selectbox(
        "Select Shelf",
        shelves,
        format_func=lambda x: f"Shelf {x}"
    )

    shelf_df = freezer_df[freezer_df["Shelf"] == shelf_pick].copy()
    box_options = sorted(shelf_df["Box"].unique(), key=lambda x: int(x))

    box_pick = st.selectbox(
        "Select Box",
        box_options,
        format_func=lambda x: f"Box {x}"
    )

    selected_box_df = shelf_df[shelf_df["Box"] == box_pick].copy()
    selected_box_df["Packet_Number"] = selected_box_df["Packet"].astype(int)
    selected_box_df = selected_box_df.sort_values("Packet_Number")

    st.markdown(f"### Contents of F{selected_freezer}-S{shelf_pick}-B{box_pick}")

    st.dataframe(
        selected_box_df[
            [
                "Packet",
                "accession_id",
                "line_name",
                "generation",
                "year_produced",
                "quantity_available",
                "germination_percent",
                "freezer_location"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )


def germination_reminder_tab(df):
    st.subheader("Germination Test Reminders")

    st.write("This section identifies seed lots that may need germination retesting.")

    reminder_df = df.copy()

    reminder_df["last_tested_date"] = pd.to_datetime(
        reminder_df["last_tested"],
        errors="coerce"
    )

    today = pd.Timestamp.today().normalize()

    reminder_df["days_since_tested"] = (
        today - reminder_df["last_tested_date"]
    ).dt.days

    reminder_df["germination_percent"] = pd.to_numeric(
        reminder_df["germination_percent"],
        errors="coerce"
    )

    retest_interval = st.number_input(
        "Retest interval in years",
        min_value=1,
        max_value=10,
        value=5
    )

    germination_threshold = st.number_input(
        "Low germination warning threshold (%)",
        min_value=0,
        max_value=100,
        value=75
    )

    max_days = retest_interval * 365

    reminder_df["Reminder Status"] = "OK"

    reminder_df.loc[
        reminder_df["days_since_tested"] >= max_days,
        "Reminder Status"
    ] = "Retest Due"

    reminder_df.loc[
        reminder_df["germination_percent"] < germination_threshold,
        "Reminder Status"
    ] = "Low Germination"

    reminder_df.loc[
        reminder_df["last_tested_date"].isna(),
        "Reminder Status"
    ] = "Missing Test Date"

    due_df = reminder_df[
        reminder_df["Reminder Status"] != "OK"
    ].copy()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Accessions", len(reminder_df))
    c2.metric("Retest Due", len(reminder_df[reminder_df["Reminder Status"] == "Retest Due"]))
    c3.metric("Low Germination", len(reminder_df[reminder_df["Reminder Status"] == "Low Germination"]))
    c4.metric("Missing Test Date", len(reminder_df[reminder_df["Reminder Status"] == "Missing Test Date"]))

    st.divider()

    st.markdown("### Accessions Requiring Attention")

    if due_df.empty:
        st.success("No germination reminders at this time.")
    else:
        st.dataframe(
            due_df[
                [
                    "accession_id",
                    "line_name",
                    "generation",
                    "year_produced",
                    "germination_percent",
                    "last_tested",
                    "days_since_tested",
                    "freezer_location",
                    "Reminder Status"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    st.markdown("### Full Germination Test Status")

    status_df = reminder_df[
        [
            "accession_id",
            "line_name",
            "generation",
            "year_produced",
            "germination_percent",
            "last_tested",
            "days_since_tested",
            "freezer_location",
            "Reminder Status"
        ]
    ].copy()

    status_df = status_df.sort_values(
        by=["Reminder Status", "days_since_tested"],
        ascending=[True, False]
    )

    st.dataframe(status_df, use_container_width=True, hide_index=True)

    st.download_button(
        "Download Germination Reminder List",
        data=due_df.to_csv(index=False),
        file_name="germination_reminders.csv",
        mime="text/csv"
    )


def import_seed_inventory_tab():
    st.subheader("Import Seed Inventory List")

    uploaded_file = st.file_uploader(
        "Upload seed inventory file",
        type=["csv", "txt", "tsv", "xlsx", "xls"]
    )

    if uploaded_file is None:
        st.info("Upload CSV, Excel, TXT, or TSV file exported from Access or Excel.")
        return

    file_name = uploaded_file.name.lower()

    try:
        if file_name.endswith(".csv"):
            import_df = pd.read_csv(uploaded_file)
        elif file_name.endswith(".txt") or file_name.endswith(".tsv"):
            import_df = pd.read_csv(uploaded_file, sep=None, engine="python")
        elif file_name.endswith(".xlsx") or file_name.endswith(".xls"):
            import_df = pd.read_excel(uploaded_file)
        else:
            st.error("Unsupported file type. Please upload CSV, TXT, TSV, XLSX, or XLS.")
            return
    except Exception as e:
        st.error(f"Could not read file: {e}")
        return

    st.success(f"File loaded successfully: {uploaded_file.name}")
    st.write("Preview of uploaded file")
    st.dataframe(import_df.head(20), use_container_width=True)

    st.markdown("### Column Mapping")

    columns = import_df.columns.tolist()

    accession_col = st.selectbox(
        "Accession / Seed Code column",
        columns,
        index=columns.index("Seed Code") if "Seed Code" in columns else 0
    )

    line_col = st.selectbox(
        "Variety or Strain column",
        columns,
        index=columns.index("Variety or Strain") if "Variety or Strain" in columns else 0
    )

    gen_col = st.selectbox(
        "Generation column",
        columns,
        index=columns.index("Gen") if "Gen" in columns else 0
    )

    pedigree_col = st.selectbox(
        "Source Parents / Pedigree column",
        columns,
        index=columns.index("Source Parents") if "Source Parents" in columns else 0
    )

    notes_cols = st.multiselect(
        "Columns to combine into Notes",
        columns,
        default=[col for col in ["Serial No", "Seed List No", "Source", "Remark"] if col in columns]
    )

    if st.button("Import Seed Inventory"):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        imported = 0
        skipped = 0

        for _, row in import_df.iterrows():
            accession_id = str(row.get(accession_col, "")).strip()

            if accession_id == "" or accession_id.lower() == "nan":
                skipped += 1
                continue

            line_name = str(row.get(line_col, "")).strip()
            generation = str(row.get(gen_col, "")).strip()
            pedigree = str(row.get(pedigree_col, "")).strip()

            notes_parts = []
            for col in notes_cols:
                value = row.get(col, "")
                if pd.notna(value) and str(value).strip() != "":
                    notes_parts.append(f"{col}: {value}")

            notes = " | ".join(notes_parts)

            cur.execute("""
                INSERT OR REPLACE INTO accessions (
                    accession_id, line_name, pedigree, generation, year_produced,
                    quantity_available, freezer_location, germination_percent,
                    last_tested, disease_resistance, quality_traits, notes, photo_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                accession_id,
                line_name,
                pedigree,
                generation,
                0,
                "",
                "",
                0,
                "",
                "",
                "",
                notes,
                ""
            ))

            imported += 1

        conn.commit()
        conn.close()

        st.success(f"Imported {imported:,} records successfully.")
        st.warning(f"Skipped {skipped:,} rows with blank accession/seed code.")
        st.info("Refresh the app to see the updated inventory.")


df = load_data()

query_params = st.query_params
url_accession = query_params.get("accession", None)

tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Dashboard",
    "Search Inventory",
    "Add / Edit Record",
    "Freezer Map",
    "Germination Reminders",
    "Import Seed Inventory",
    "QR Codes",
    "Export"
])


with tab0:
    dashboard_tab(df)


with tab1:
    st.subheader("Search seed lots")

    if url_accession:
        st.success(f"Opened from QR/link: {url_accession}")

    search_default = url_accession if url_accession else ""

    search = st.text_input(
        "Search by Accession ID, Line Name, Pedigree, Trait, or Freezer Location",
        value=search_default,
        key="inventory_search"
    )

    if search:
        mask = df.astype(str).apply(
            lambda col: col.str.contains(search, case=False, na=False)
        ).any(axis=1)
        results = df[mask].copy()
    else:
        results = df.copy()

    st.dataframe(
        results[
            [
                "accession_id",
                "line_name",
                "year_produced",
                "germination_percent",
                "freezer_location",
                "quantity_available"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

    accession_options = results["accession_id"].tolist()

    if accession_options:
        if url_accession in accession_options:
            default_selection = url_accession
        elif "view_accession" in st.session_state and st.session_state.view_accession in accession_options:
            default_selection = st.session_state.view_accession
        else:
            default_selection = accession_options[0]

        selected = st.selectbox(
            "Select accession to view full record",
            accession_options,
            index=accession_options.index(default_selection),
            key="view_accession_select"
        )

        st.session_state.view_accession = selected
        rec = get_record(df, selected)

        st.divider()
        c1, c2 = st.columns([2, 1])

        with c1:
            st.markdown("### Accession Record")
            st.write(f"**Accession ID:** {rec['accession_id']}")
            st.write(f"**Variety/Line Name:** {rec['line_name']}")
            st.write(f"**Pedigree:** {rec['pedigree']}")
            st.write(f"**Generation:** {rec['generation']}")
            st.write(f"**Year Produced:** {rec['year_produced']}")
            st.write(f"**Quantity Available:** {rec['quantity_available']}")
            st.write(f"**Freezer Location:** {rec['freezer_location']}")
            st.write(f"**Germination (%):** {rec['germination_percent']}")
            st.write(f"**Last Date Tested:** {rec['last_tested']}")
            st.write(f"**Disease Resistance:** {rec['disease_resistance']}")
            st.write(f"**Quality Traits:** {rec['quality_traits']}")
            st.write(f"**Notes:** {rec['notes']}")

        with c2:
            qr_path, direct_url = generate_direct_qr(rec["accession_id"])
            st.image(str(qr_path), caption=f"Direct QR: {rec['accession_id']}", width=180)
            st.write("**QR opens:**")
            st.code(direct_url)
            st.info("Scan this QR while the app is running. It opens this accession directly.")
    else:
        st.warning("No accession found. Try a different search term.")


with tab2:
    st.subheader("Add or edit accession record")

    mode = st.radio("Choose action", ["Edit existing record", "Add new record"], horizontal=True)

    if mode == "Edit existing record":
        accession_list = df["accession_id"].tolist()

        selected_edit = st.selectbox(
            "Select accession to edit",
            accession_list,
            key="edit_accession_select"
        )

        rec = get_record(df, selected_edit)

        st.info("Fields below are loaded from the selected accession. Change only what is needed, then click Update Record.")

        accession_id = st.text_input("Accession ID", value=rec["accession_id"], disabled=True)
        line_name = st.text_input("Variety or Line Name", value=str(rec["line_name"]))
        pedigree = st.text_area("Pedigree Information", value=str(rec["pedigree"]))
        generation = st.text_input("Generation", value=str(rec["generation"]))
        year_produced = st.number_input("Year Produced", min_value=1900, max_value=2100, value=int(rec["year_produced"]))
        quantity_available = st.text_input("Quantity Available", value=str(rec["quantity_available"]))
        freezer_location = st.text_input("Freezer Location Coding", value=str(rec["freezer_location"]))
        germination_percent = st.number_input("Germination (%)", min_value=0, max_value=100, value=int(rec["germination_percent"]))
        last_tested = st.text_input("Last Date Tested", value=str(rec["last_tested"]))
        disease_resistance = st.text_input("Disease Resistance", value=str(rec["disease_resistance"]))
        quality_traits = st.text_input("Quality Traits", value=str(rec["quality_traits"]))
        notes = st.text_area("Special Traits or Notes", value=str(rec["notes"]))
        photo_path = st.text_input("Photo Path", value=str(rec["photo_path"]))

        if st.button("Update Record"):
            save_record((
                rec["accession_id"],
                line_name,
                pedigree,
                generation,
                int(year_produced),
                quantity_available,
                freezer_location,
                int(germination_percent),
                last_tested,
                disease_resistance,
                quality_traits,
                notes,
                photo_path
            ))
            st.success("Record updated successfully.")
            st.rerun()

    else:
        st.info("Use this form to create a completely new accession.")

        accession_id = st.text_input("New Accession ID", value="CTRF-2026-006")
        line_name = st.text_input("Variety or Line Name")
        pedigree = st.text_area("Pedigree Information")
        generation = st.text_input("Generation")
        year_produced = st.number_input("Year Produced", min_value=1900, max_value=2100, value=2026)
        quantity_available = st.text_input("Quantity Available", value="1.0 g")
        freezer_location = st.text_input("Freezer Location Coding", value="F1-S2-B2-P1")
        germination_percent = st.number_input("Germination (%)", min_value=0, max_value=100, value=90)
        last_tested = st.text_input("Last Date Tested", value="2026-05-21")
        disease_resistance = st.text_input("Disease Resistance")
        quality_traits = st.text_input("Quality Traits")
        notes = st.text_area("Special Traits or Notes")
        photo_path = st.text_input("Photo Path", value=f"photos/{accession_id}.jpg")

        if st.button("Add New Record"):
            if accession_id in df["accession_id"].tolist():
                st.error("This Accession ID already exists. Use Edit existing record instead.")
            else:
                save_record((
                    accession_id,
                    line_name,
                    pedigree,
                    generation,
                    int(year_produced),
                    quantity_available,
                    freezer_location,
                    int(germination_percent),
                    last_tested,
                    disease_resistance,
                    quality_traits,
                    notes,
                    photo_path
                ))
                generate_direct_qr(accession_id)
                st.success("New record added successfully.")
                st.rerun()


with tab3:
    freezer_map_tab(df)


with tab4:
    germination_reminder_tab(df)


with tab5:
    import_seed_inventory_tab()


with tab6:
    st.subheader("Direct QR codes")
    st.write("These QR codes open the selected accession directly when the app is running.")

    accession_for_qr = st.selectbox("Choose accession for QR code", df["accession_id"].tolist())
    qr_path, direct_url = generate_direct_qr(accession_for_qr)

    c1, c2 = st.columns([1, 2])
    with c1:
        st.image(str(qr_path), caption=accession_for_qr, width=220)
    with c2:
        st.write("**Direct accession URL:**")
        st.code(direct_url)
        st.write("Print this QR on paper for demo purposes.")
        st.write("For long-term use, replace localhost with a server/cloud URL.")


with tab7:
    st.subheader("Export inventory")
    st.download_button(
        "Download CSV backup",
        data=df.to_csv(index=False),
        file_name="seed_inventory_export.csv",
        mime="text/csv"
    )
    st.write("Use this export as a backup or to share with collaborators.")
