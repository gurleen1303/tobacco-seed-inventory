
import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path
import qrcode

DB_PATH = Path("seed_inventory.db")
LOCAL_APP_URL = "http://localhost:8501"

st.set_page_config(page_title="Tobacco Seed Inventory Demo", layout="wide")

st.title("Tobacco Seed Inventory System - Demo")
st.caption("Seed inventory, freezer location tracking, germination status, and direct QR accession workflow.")

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
    direct_url = f"{LOCAL_APP_URL}/?accession={accession_id}"
    qr_path = qr_dir / f"{accession_id}_direct.png"
    img = qrcode.make(direct_url)
    img.save(qr_path)
    return qr_path, direct_url

df = load_data()

# Read accession from URL, e.g. http://localhost:8501/?accession=CTRF-1990-001
query_params = st.query_params
url_accession = query_params.get("accession", None)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Search Inventory",
    "Add / Edit Record",
    "Freezer Map",
    "QR Codes",
    "Export"
])

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
        mask = df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        results = df[mask].copy()
    else:
        results = df.copy()

    st.dataframe(
        results[["accession_id", "line_name", "year_produced", "germination_percent", "freezer_location", "quantity_available"]],
        use_container_width=True,
        hide_index=True
    )

    accession_options = results["accession_id"].tolist()

    if accession_options:
        # If QR/link accession exists in filtered results, select it
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
                rec["accession_id"], line_name, pedigree, generation, int(year_produced),
                quantity_available, freezer_location, int(germination_percent),
                last_tested, disease_resistance, quality_traits, notes, photo_path
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
                    accession_id, line_name, pedigree, generation, int(year_produced),
                    quantity_available, freezer_location, int(germination_percent),
                    last_tested, disease_resistance, quality_traits, notes, photo_path
                ))
                generate_direct_qr(accession_id)
                st.success("New record added successfully.")
                st.rerun()

with tab3:
    st.subheader("Freezer location coding")
    st.markdown("""
    Example code: **F1-S2-B3-P7**

    - **F1** = Freezer 1  
    - **S2** = Shelf 2  
    - **B3** = Box 3  
    - **P7** = Position 7  
    """)

    freezer_df = df[["accession_id", "line_name", "freezer_location"]].sort_values("freezer_location")
    st.dataframe(freezer_df, use_container_width=True, hide_index=True)

with tab4:
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

with tab5:
    st.subheader("Export inventory")
    st.download_button(
        "Download CSV backup",
        data=df.to_csv(index=False),
        file_name="seed_inventory_export.csv",
        mime="text/csv"
    )
    st.write("Use this export as a backup or to share with collaborators.")
