import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path
import qrcode
import re
import tempfile
import os

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


DB_PATH = Path("seed_inventory.db")
APP_URL = "https://tobacco-seed-inventory.streamlit.app"

st.set_page_config(page_title="Tobacco Seed Inventory Demo", layout="wide")

st.title("Tobacco Seed Inventory System - Demo")
st.caption("Seed inventory, freezer tracking, germination reminders, QR workflow, label printing, and breeding lineage traceability.")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS accessions (
            accession_id TEXT PRIMARY KEY,
            line_name TEXT,
            pedigree TEXT,
            generation TEXT,
            year_produced INTEGER,
            quantity_available TEXT,
            freezer_location TEXT,
            germination_percent INTEGER,
            last_tested TEXT,
            disease_resistance TEXT,
            quality_traits TEXT,
            notes TEXT,
            photo_path TEXT
        )
    """)

    conn.commit()
    conn.close()


def upgrade_db_schema():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(accessions)")
    existing_columns = [row[1] for row in cur.fetchall()]

    required_columns = {
        "serial_number": "TEXT",
        "parent_accession": "TEXT",
        "nursery_type": "TEXT",
        "trial_year": "INTEGER"
    }

    for col, col_type in required_columns.items():
        if col not in existing_columns:
            cur.execute(f"ALTER TABLE accessions ADD COLUMN {col} {col_type}")

    conn.commit()
    conn.close()


def insert_demo_lineage_if_missing():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    demo_records = [
        {
            "accession_id": "22-23GRM1",
            "serial_number": "",
            "line_name": "",
            "parent_accession": "",
            "pedigree": "C176TM/21D5 BLK",
            "generation": "F2",
            "nursery_type": "Original Population",
            "trial_year": 2023,
            "year_produced": 2023,
            "quantity_available": "",
            "freezer_location": "",
            "germination_percent": 0,
            "last_tested": "",
            "disease_resistance": "",
            "quality_traits": "",
            "notes": "Original source population",
            "photo_path": ""
        },
        {
            "accession_id": "24RC1",
            "serial_number": "61685",
            "line_name": "",
            "parent_accession": "22-23GRM1",
            "pedigree": "C176TM/21D5 BLK",
            "generation": "F2",
            "nursery_type": "F2 Population",
            "trial_year": 2024,
            "year_produced": 2024,
            "quantity_available": "1.0 g",
            "freezer_location": "F1-S1-B1-P1",
            "germination_percent": 88,
            "last_tested": "2025-05-21",
            "disease_resistance": "",
            "quality_traits": "",
            "notes": "2024 seed used",
            "photo_path": ""
        },
        {
            "accession_id": "25SB1",
            "serial_number": "62157",
            "line_name": "",
            "parent_accession": "24RC1",
            "pedigree": "C176TM/21D5 BLK",
            "generation": "F3",
            "nursery_type": "F3 Population",
            "trial_year": 2025,
            "year_produced": 2025,
            "quantity_available": "1.0 g",
            "freezer_location": "F1-S1-B1-P2",
            "germination_percent": 86,
            "last_tested": "2025-05-21",
            "disease_resistance": "",
            "quality_traits": "",
            "notes": "2025 seed used",
            "photo_path": ""
        },
        {
            "accession_id": "25SB1-1",
            "serial_number": "62451",
            "line_name": "",
            "parent_accession": "25SB1",
            "pedigree": "C176TM/21D5 BLK",
            "generation": "F3",
            "nursery_type": "Selected Plant",
            "trial_year": 2025,
            "year_produced": 2025,
            "quantity_available": "0.8 g",
            "freezer_location": "F1-S1-B1-P3",
            "germination_percent": 84,
            "last_tested": "2025-05-21",
            "disease_resistance": "",
            "quality_traits": "",
            "notes": "Selected from 25SB1",
            "photo_path": ""
        },
        {
            "accession_id": "26T1",
            "serial_number": "62606",
            "line_name": "25SB1-1",
            "parent_accession": "25SB1-1",
            "pedigree": "C176TM/21D5 BLK",
            "generation": "F4",
            "nursery_type": "Head Row",
            "trial_year": 2026,
            "year_produced": 2026,
            "quantity_available": "0.6 g",
            "freezer_location": "F1-S1-B1-P4",
            "germination_percent": 90,
            "last_tested": "2026-05-21",
            "disease_resistance": "",
            "quality_traits": "",
            "notes": "2026 seed used",
            "photo_path": ""
        }
    ]

    for rec in demo_records:
        cur.execute("""
            INSERT OR IGNORE INTO accessions (
                accession_id, line_name, pedigree, generation, year_produced,
                quantity_available, freezer_location, germination_percent,
                last_tested, disease_resistance, quality_traits, notes, photo_path,
                serial_number, parent_accession, nursery_type, trial_year
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rec["accession_id"],
            rec["line_name"],
            rec["pedigree"],
            rec["generation"],
            rec["year_produced"],
            rec["quantity_available"],
            rec["freezer_location"],
            rec["germination_percent"],
            rec["last_tested"],
            rec["disease_resistance"],
            rec["quality_traits"],
            rec["notes"],
            rec["photo_path"],
            rec["serial_number"],
            rec["parent_accession"],
            rec["nursery_type"],
            rec["trial_year"]
        ))

    conn.commit()
    conn.close()


def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM accessions", conn)
    conn.close()

    required_cols = [
        "serial_number", "accession_id", "line_name", "parent_accession",
        "pedigree", "generation", "nursery_type", "trial_year",
        "year_produced", "quantity_available", "freezer_location",
        "germination_percent", "last_tested", "disease_resistance",
        "quality_traits", "notes", "photo_path"
    ]

    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

    return df


def save_record(record):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO accessions (
            accession_id, line_name, pedigree, generation, year_produced,
            quantity_available, freezer_location, germination_percent,
            last_tested, disease_resistance, quality_traits, notes, photo_path,
            serial_number, parent_accession, nursery_type, trial_year
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, record)

    conn.commit()
    conn.close()


def get_record(df, accession_id):
    subset = df[df["accession_id"].astype(str) == str(accession_id)]
    if len(subset) == 0:
        return None
    return subset.iloc[0].to_dict()


def get_record_by_serial_or_accession(df, value):
    value = str(value).strip()
    subset = df[
        (df["accession_id"].astype(str) == value) |
        (df["serial_number"].astype(str) == value)
    ]
    if len(subset) == 0:
        return None
    return subset.iloc[0].to_dict()


def generate_direct_qr(serial_number, accession_id):
    qr_dir = Path("qr_codes")
    qr_dir.mkdir(exist_ok=True)

    qr_value = str(serial_number).strip() if str(serial_number).strip() else accession_id
    direct_url = f"{APP_URL}/?lookup={qr_value}"

    qr_path = qr_dir / f"{qr_value}_direct.png"
    img = qrcode.make(direct_url)
    img.save(qr_path)

    return qr_path, direct_url


def generate_avery_94216_labels(selected_df, copies=1, packet_type="Working"):
    pdf_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name

    c = canvas.Canvas(pdf_path, pagesize=letter)
    page_w, page_h = letter

    label_w = 2.25 * inch
    label_h = 0.75 * inch

    cols = 3
    rows = 10
    labels_per_page = 30

    left_margin = 0.625 * inch
    top_margin = 0.5 * inch
    col_gap = 0.125 * inch
    row_gap = 0.25 * inch

    label_items = []

    for _, row in selected_df.iterrows():
        for _ in range(copies):
            label_items.append(row)

    for i, row in enumerate(label_items):
        pos = i % labels_per_page

        if pos == 0 and i != 0:
            c.showPage()

        col = pos % cols
        row_num = pos // cols

        x = left_margin + col * (label_w + col_gap)
        y = page_h - top_margin - (row_num + 1) * label_h - row_num * row_gap

        serial = str(row.get("serial_number", "")).strip()
        accession = str(row.get("accession_id", "")).strip()
        line_name = str(row.get("line_name", "")).strip()
        generation = str(row.get("generation", "")).strip()
        year = str(row.get("trial_year", "")).strip()
        location = str(row.get("freezer_location", "")).strip()
        quantity = str(row.get("quantity_available", "")).strip()

        lookup_value = serial if serial else accession
        qr_url = f"{APP_URL}/?lookup={lookup_value}"

        qr_img = qrcode.make(qr_url)
        qr_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
        qr_img.save(qr_path)

        c.drawImage(
            qr_path,
            x + label_w - 0.58 * inch,
            y + 0.10 * inch,
            width=0.50 * inch,
            height=0.50 * inch
        )

        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(x + 0.05 * inch, y + 0.56 * inch, f"{serial} | {accession}")

        c.setFont("Helvetica", 5.3)
        c.drawString(x + 0.05 * inch, y + 0.43 * inch, f"{line_name[:24]}")
        c.drawString(x + 0.05 * inch, y + 0.30 * inch, f"{generation} | {year} | {quantity}")
        c.drawString(x + 0.05 * inch, y + 0.18 * inch, f"{packet_type}")
        c.drawString(x + 0.05 * inch, y + 0.06 * inch, f"{location}")

        os.remove(qr_path)

    c.save()
    return pdf_path


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


def build_lineage(df, accession_id):
    lineage = []
    current = str(accession_id).strip()
    visited = set()

    while current and current not in visited:
        visited.add(current)

        row = df[df["accession_id"].astype(str) == current]

        if row.empty:
            lineage.append({
                "Serial No": "",
                "Accession": current,
                "Generation": "",
                "Nursery Type": "",
                "Year": "",
                "Parent Accession": ""
            })
            break

        rec = row.iloc[0]

        lineage.append({
            "Serial No": rec.get("serial_number", ""),
            "Accession": rec.get("accession_id", ""),
            "Generation": rec.get("generation", ""),
            "Nursery Type": rec.get("nursery_type", ""),
            "Year": rec.get("trial_year", ""),
            "Parent Accession": rec.get("parent_accession", "")
        })

        parent = rec.get("parent_accession", "")

        if pd.isna(parent) or str(parent).strip() == "":
            break

        current = str(parent).strip()

    return pd.DataFrame(lineage)


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

    st.markdown("### Inventory Overview")

    cols = [
        "serial_number", "accession_id", "parent_accession",
        "pedigree", "generation", "nursery_type", "trial_year",
        "germination_percent", "freezer_location"
    ]

    st.dataframe(df[cols], use_container_width=True, hide_index=True)


def search_inventory_tab(df, lookup_value=None):
    st.subheader("Search seed lots")

    if lookup_value:
        st.success(f"Opened from QR/link: {lookup_value}")

    search_default = lookup_value if lookup_value else ""

    search = st.text_input(
        "Search by Serial No, Accession ID, Parent Accession, Pedigree, Generation, Nursery Type, or Freezer Location",
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

    display_cols = [
        "serial_number", "accession_id", "parent_accession",
        "pedigree", "generation", "nursery_type", "trial_year",
        "germination_percent", "freezer_location"
    ]

    st.dataframe(results[display_cols], use_container_width=True, hide_index=True)

    accession_options = results["accession_id"].tolist()

    if accession_options:
        selected = st.selectbox(
            "Select accession to view full record",
            accession_options,
            key="view_accession_select"
        )

        rec = get_record(df, selected)

        st.divider()
        c1, c2 = st.columns([2, 1])

        with c1:
            st.markdown("### Packet Information")
            st.write(f"Serial No: {rec['serial_number']}")
            st.write(f"Accession: {rec['accession_id']}")
            st.write(f"Parent Accession: {rec['parent_accession']}")
            st.write(f"Pedigree: {rec['pedigree']}")
            st.write(f"Generation: {rec['generation']}")
            st.write(f"Nursery Type: {rec['nursery_type']}")
            st.write(f"Year: {rec['trial_year']}")
            st.write(f"Quantity Available: {rec['quantity_available']}")
            st.write(f"Freezer Location: {rec['freezer_location']}")
            st.write(f"Germination (%): {rec['germination_percent']}")
            st.write(f"Last Date Tested: {rec['last_tested']}")
            st.write(f"Notes: {rec['notes']}")

        with c2:
            qr_path, direct_url = generate_direct_qr(rec["serial_number"], rec["accession_id"])
            st.image(str(qr_path), caption=f"QR: {rec['serial_number']} | {rec['accession_id']}", width=180)
            st.write("QR opens:")
            st.code(direct_url)

        st.divider()
        st.markdown("### Breeding Lineage")
        lineage_df = build_lineage(df, rec["accession_id"])
        st.dataframe(lineage_df, use_container_width=True, hide_index=True)
    else:
        st.warning("No accession found. Try a different search term.")


def add_edit_tab(df):
    st.subheader("Add or edit accession record")

    mode = st.radio("Choose action", ["Edit existing record", "Add new record"], horizontal=True)

    if mode == "Edit existing record":
        accession_list = df["accession_id"].tolist()
        selected_edit = st.selectbox("Select accession to edit", accession_list)
        rec = get_record(df, selected_edit)

        serial_number = st.text_input("Serial Number", value=str(rec["serial_number"]))
        accession_id = st.text_input("Accession ID", value=str(rec["accession_id"]), disabled=True)
        line_name = st.text_input("Variety or Strain", value=str(rec["line_name"]))
        parent_accession = st.text_input("Parent Accession", value=str(rec["parent_accession"]))
        pedigree = st.text_area("Pedigree", value=str(rec["pedigree"]))
        generation = st.text_input("Generation", value=str(rec["generation"]))
        nursery_type = st.text_input("Nursery Type", value=str(rec["nursery_type"]))

        trial_year_value = 2026 if pd.isna(rec["trial_year"]) or str(rec["trial_year"]) == "" else int(float(rec["trial_year"]))
        year_produced_value = 0 if pd.isna(rec["year_produced"]) or str(rec["year_produced"]) == "" else int(float(rec["year_produced"]))
        germination_value = 0 if pd.isna(rec["germination_percent"]) or str(rec["germination_percent"]) == "" else int(float(rec["germination_percent"]))

        trial_year = st.number_input("Year", min_value=1900, max_value=2100, value=trial_year_value)
        year_produced = st.number_input("Seed Production Year", min_value=0, max_value=2100, value=year_produced_value)
        quantity_available = st.text_input("Quantity Available", value=str(rec["quantity_available"]))
        freezer_location = st.text_input("Freezer Location", value=str(rec["freezer_location"]))
        germination_percent = st.number_input("Germination (%)", min_value=0, max_value=100, value=germination_value)
        last_tested = st.text_input("Last Date Tested", value=str(rec["last_tested"]))
        disease_resistance = st.text_input("Disease Resistance", value=str(rec["disease_resistance"]))
        quality_traits = st.text_input("Quality Traits", value=str(rec["quality_traits"]))
        notes = st.text_area("Notes", value=str(rec["notes"]))
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
                photo_path,
                serial_number,
                parent_accession,
                nursery_type,
                int(trial_year)
            ))
            st.success("Record updated successfully.")
            st.rerun()

    else:
        serial_number = st.text_input("Serial Number", value="62610")
        accession_id = st.text_input("Accession ID", value="26T5")
        line_name = st.text_input("Variety or Strain")
        parent_accession = st.text_input("Parent Accession", value="25SB1-9")
        pedigree = st.text_area("Pedigree", value="C176TM/21D5 BLK")
        generation = st.text_input("Generation", value="F4")
        nursery_type = st.text_input("Nursery Type", value="Head Row")
        trial_year = st.number_input("Year", min_value=1900, max_value=2100, value=2026)
        year_produced = st.number_input("Seed Production Year", min_value=0, max_value=2100, value=2026)
        quantity_available = st.text_input("Quantity Available", value="0.5 g")
        freezer_location = st.text_input("Freezer Location", value="F1-S1-B2-P3")
        germination_percent = st.number_input("Germination (%)", min_value=0, max_value=100, value=90)
        last_tested = st.text_input("Last Date Tested", value="2026-05-21")
        disease_resistance = st.text_input("Disease Resistance")
        quality_traits = st.text_input("Quality Traits")
        notes = st.text_area("Notes")
        photo_path = st.text_input("Photo Path")

        if st.button("Add New Record"):
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
                photo_path,
                serial_number,
                parent_accession,
                nursery_type,
                int(trial_year)
            ))
            generate_direct_qr(serial_number, accession_id)
            st.success("New record added successfully.")
            st.rerun()


def lineage_tab(df, lookup_value=None):
    st.subheader("Breeding Lineage / Traceability")

    options = df["accession_id"].tolist()
    default_index = 0

    if lookup_value:
        rec = get_record_by_serial_or_accession(df, lookup_value)
        if rec and rec["accession_id"] in options:
            default_index = options.index(rec["accession_id"])

    accession = st.selectbox("Select accession", options, index=default_index)
    rec = get_record(df, accession)

    st.markdown("### Packet Information")
    st.write(f"Serial No: {rec['serial_number']}")
    st.write(f"Accession: {rec['accession_id']}")
    st.write(f"Parent Accession: {rec['parent_accession']}")
    st.write(f"Pedigree: {rec['pedigree']}")
    st.write(f"Generation: {rec['generation']}")
    st.write(f"Nursery Type: {rec['nursery_type']}")
    st.write(f"Year: {rec['trial_year']}")

    st.divider()
    st.markdown("### Breeding Lineage")

    lineage_df = build_lineage(df, accession)

    for i, row in lineage_df.iterrows():
        serial = row["Serial No"] if str(row["Serial No"]).strip() else "No serial"
        st.write(f"{serial} | {row['Accession']} | {row['Generation']} | {row['Nursery Type']} | {row['Year']}")

        if i < len(lineage_df) - 1:
            st.write("↓")

    st.divider()
    st.dataframe(lineage_df, use_container_width=True, hide_index=True)


def freezer_map_tab(df):
    st.subheader("Visual Freezer Map")

    st.markdown("""
    Location format: F1-S2-B3-P7  
    Freezer 1 → Shelf 2 → Box 3 → Packet 7
    """)

    map_df = split_freezer_location(df)
    valid_df = map_df.dropna(subset=["Freezer", "Shelf", "Box", "Packet"]).copy()

    if valid_df.empty:
        st.warning("No valid freezer locations found. Use format like F1-S2-B3-P7.")
        return

    freezer_options = sorted(valid_df["Freezer"].unique(), key=lambda x: int(x))
    selected_freezer = st.selectbox("Select Freezer", freezer_options, format_func=lambda x: f"Freezer {x}")

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
    shelf_pick = st.selectbox("Select Shelf", shelves, format_func=lambda x: f"Shelf {x}")

    shelf_df = freezer_df[freezer_df["Shelf"] == shelf_pick].copy()
    box_options = sorted(shelf_df["Box"].unique(), key=lambda x: int(x))
    box_pick = st.selectbox("Select Box", box_options, format_func=lambda x: f"Box {x}")

    selected_box_df = shelf_df[shelf_df["Box"] == box_pick].copy()
    selected_box_df["Packet_Number"] = selected_box_df["Packet"].astype(int)
    selected_box_df = selected_box_df.sort_values("Packet_Number")

    box_cols = [
        "Packet", "serial_number", "accession_id", "parent_accession",
        "pedigree", "generation", "nursery_type", "freezer_location"
    ]

    st.dataframe(selected_box_df[box_cols], use_container_width=True, hide_index=True)


def germination_reminder_tab(df):
    st.subheader("Germination Test Reminders")

    reminder_df = df.copy()
    reminder_df["last_tested_date"] = pd.to_datetime(reminder_df["last_tested"], errors="coerce")
    reminder_df["days_since_tested"] = (
        pd.Timestamp.today().normalize() - reminder_df["last_tested_date"]
    ).dt.days
    reminder_df["germination_percent"] = pd.to_numeric(reminder_df["germination_percent"], errors="coerce")

    retest_interval = st.number_input("Retest interval in years", min_value=1, max_value=10, value=5)
    germination_threshold = st.number_input("Low germination warning threshold (%)", min_value=0, max_value=100, value=75)

    max_days = retest_interval * 365

    reminder_df["Reminder Status"] = "OK"
    reminder_df.loc[reminder_df["days_since_tested"] >= max_days, "Reminder Status"] = "Retest Due"
    reminder_df.loc[reminder_df["germination_percent"] < germination_threshold, "Reminder Status"] = "Low Germination"
    reminder_df.loc[reminder_df["last_tested_date"].isna(), "Reminder Status"] = "Missing Test Date"

    due_df = reminder_df[reminder_df["Reminder Status"] != "OK"].copy()

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
        st.dataframe(due_df, use_container_width=True, hide_index=True)


def qr_tab(df):
    st.subheader("Direct QR Codes")

    accession_for_qr = st.selectbox("Choose accession for QR code", df["accession_id"].tolist())
    rec = get_record(df, accession_for_qr)

    qr_path, direct_url = generate_direct_qr(rec["serial_number"], rec["accession_id"])

    c1, c2 = st.columns([1, 2])

    with c1:
        st.image(str(qr_path), caption=f"{rec['serial_number']} | {rec['accession_id']}", width=220)

    with c2:
        st.write("Direct accession URL:")
        st.code(direct_url)
        st.write("QR lookup uses serial number when available.")


def label_printing_tab(df):
    st.subheader("Avery 94216 Label Printing")

    st.write("Create waterproof seed packet labels directly from the seed inventory database.")

    st.info("Use Avery 94216 labels: 0.75 inch × 2.25 inch. Print PDF at 100% / Actual Size.")

    search_text = st.text_input(
        "Search accession, serial number, line name, pedigree, generation, or freezer location",
        key="label_search"
    )

    label_df = df.copy()

    if search_text:
        label_df = label_df[
            label_df.astype(str).apply(
                lambda row: row.str.contains(search_text, case=False, na=False).any(),
                axis=1
            )
        ]

    display_cols = [
        "serial_number", "accession_id", "line_name", "generation",
        "trial_year", "quantity_available", "freezer_location"
    ]

    st.dataframe(label_df[display_cols], use_container_width=True, hide_index=True)

    label_options = (
        label_df["serial_number"].astype(str)
        + " | "
        + label_df["accession_id"].astype(str)
        + " | "
        + label_df["freezer_location"].astype(str)
    ).tolist()

    selected_labels = st.multiselect(
        "Select records to print labels",
        label_options
    )

    copies = st.number_input(
        "Number of labels per selected record",
        min_value=1,
        max_value=10,
        value=3
    )

    packet_type = st.selectbox(
        "Packet type printed on label",
        ["Working", "CTRF Backup", "McLachlan Backup", "Active Seed Room", "Long-term Freezer"]
    )

    if st.button("Generate Avery 94216 Label PDF"):
        if not selected_labels:
            st.warning("Please select at least one record.")
            return

        selected_accession_ids = [item.split(" | ")[1] for item in selected_labels]

        selected_df = label_df[
            label_df["accession_id"].astype(str).isin(selected_accession_ids)
        ].copy()

        pdf_path = generate_avery_94216_labels(
            selected_df=selected_df,
            copies=int(copies),
            packet_type=packet_type
        )

        with open(pdf_path, "rb") as f:
            st.download_button(
                label="Download Label PDF",
                data=f,
                file_name="avery_94216_seed_labels.pdf",
                mime="application/pdf"
            )

        st.success("Label PDF generated successfully. Print using 100% / Actual Size.")


def export_tab(df):
    st.subheader("Export Inventory")

    st.download_button(
        "Download CSV Backup",
        data=df.to_csv(index=False),
        file_name="seed_inventory_export.csv",
        mime="text/csv"
    )


init_db()
upgrade_db_schema()
insert_demo_lineage_if_missing()
df = load_data()

query_params = st.query_params
lookup_value = query_params.get("lookup", None)

if lookup_value:
    rec = get_record_by_serial_or_accession(df, lookup_value)

    if rec:
        st.success(f"Opened QR record: {rec['serial_number']} | {rec['accession_id']}")

        st.markdown("### Packet Information")
        st.write(f"Serial No: {rec['serial_number']}")
        st.write(f"Accession: {rec['accession_id']}")
        st.write(f"Parent Accession: {rec['parent_accession']}")
        st.write(f"Pedigree: {rec['pedigree']}")
        st.write(f"Generation: {rec['generation']}")
        st.write(f"Nursery Type: {rec['nursery_type']}")
        st.write(f"Year: {rec['trial_year']}")
        st.write(f"Freezer Location: {rec['freezer_location']}")

        st.markdown("### Breeding Lineage")
        lineage_df = build_lineage(df, rec["accession_id"])
        st.dataframe(lineage_df, use_container_width=True, hide_index=True)

        st.divider()
    else:
        st.error(f"No record found for QR lookup: {lookup_value}")


tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "Dashboard",
    "Search Inventory",
    "Add / Edit Record",
    "Lineage",
    "Freezer Map",
    "Germination Reminders",
    "QR Codes",
    "Label Printing",
    "Export"
])

with tab0:
    dashboard_tab(df)

with tab1:
    search_inventory_tab(df, lookup_value)

with tab2:
    add_edit_tab(df)

with tab3:
    lineage_tab(df, lookup_value)

with tab4:
    freezer_map_tab(df)

with tab5:
    germination_reminder_tab(df)

with tab6:
    qr_tab(df)

with tab7:
    label_printing_tab(df)

with tab8:
    export_tab(df)
