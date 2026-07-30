import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Ciudad de Strike Filtering System", layout="wide")
st.title("Ciudad de Strike - Strict COMELEC Address Filter")
st.write(
    "Strictly filters by Unit Ranges (PH 1: 1-72 | PH 2: 101-324). Automatically catches fused formats, typo labels, and standalone valid unit numbers.")

uploaded_file = st.file_uploader("Upload Excel / CSV File", type=["xlsx", "xls", "csv"])


def parse_address(address):
    """
    Parses messy COMELEC addresses. Categorizes failures strictly into Excluded (non-strike) vs Needs Manual Review (strike).
    """
    if pd.isna(address):
        return pd.Series([False, None, "Excluded - Missing Address"])

    addr_str = str(address).upper()

    # Clean up common data entry typos
    addr_str = addr_str.replace("=", " ").replace("_", " ")

    # 1. Molino Check (Rule: Banish Molino completely to Excluded)
    if "MOLINO" in addr_str:
        return pd.Series([False, None, "Excluded - Contains Molino Address"])

    # 2. City validation (Rule: If no STRIKE, banish to Excluded)
    if "STRIKE" not in addr_str:
        return pd.Series([False, None, "Excluded - Non-Ciudad de Strike"])

    # --- EVERYTHING BELOW THIS LINE IS CONFIRMED CIUDAD DE STRIKE ---

    # 3. Block/Lot Flag (Rule: "BLOCK16 LOT11" goes to manual review)
    if re.search(r'\b(?:LOT|L|BLOCK|BLK)\b', addr_str):
        return pd.Series([True, None, "Needs Manual Review - Block/Lot Format"])

    unit_str = None
    category = None

    # 4. Extract Explicit Unit (UNIT, U, ROOM, RM)
    unit_match = re.search(r'\b(?:UNIT|U|ROOM|RM)[\s\-#]*[A-Z]*(\d+(?:-\d+)?)', addr_str)

    if unit_match:
        unit_str = unit_match.group(1)
    else:
        # Matches dashed bldg-unit combos (e.g., "BLDG 4-219" -> extracts "219")
        bldg_dash_match = re.search(r'\b(?:BLDG|BUILDING|BLG|B)[\s#]*\d+[\s\-]+(\d+(?:-\d+)?)', addr_str)
        if bldg_dash_match:
            unit_str = bldg_dash_match.group(1)
        else:
            # Check standalone '#' but ONLY if NOT attached to B/BLDG/BLG
            hash_match = re.search(r'(?<!B)(?<!BLDG)(?<!BLG)(?<!BUILDING)[\s\-]*#[\s\-]*[A-Z]*(\d+(?:-\d+)?)', addr_str)
            if hash_match:
                unit_str = hash_match.group(1)

    # 5. Check for leading unit before building (e.g., "209 B4", "216 BLDG5", "121 BLG16")
    if not unit_str:
        leading_match = re.search(
            r'\b(\d+(?:-\d+)?)[\s\-]*(?:(?:PHASE|PH|P)[\s\-]*[12I]+[\s\-]*)?(?:B|BLDG|BLG|BUILDING)', addr_str)
        if leading_match:
            unit_str = leading_match.group(1)

    # 6. Fallback: Standalone valid numbers (e.g., "208 CIUDAD DE STRIKE")
    if not unit_str:
        # Hide Phase text so we don't accidentally grab the "1" or "2"
        clean_addr = re.sub(r'\b(?:PHASE|PH|P)[\s\-]*[12I]+\b', '', addr_str)
        # Hide explicit Building numbers so we don't treat "BLDG 10" as Unit 10
        clean_addr = re.sub(r'\b(?:BLDG|BUILDING|BLG|B)[\s\-#]*\d+\b', '', clean_addr)

        # Look at any numbers remaining in the address
        standalone_nums = re.findall(r'\b\d+\b', clean_addr)
        for num_str in standalone_nums:
            num = int(num_str)
            # If the standalone number perfectly fits one of our ranges, accept it as the unit
            if 1 <= num <= 72 or 101 <= num <= 324:
                unit_str = num_str
                break

    # 7. Strict Range Evaluation & Final Flags
    if unit_str:
        # Heal dashes in typos (e.g., "2-12" -> "212")
        clean_unit_str = unit_str.replace("-", "")
        unit_num = int(clean_unit_str)

        # Core Range Logic
        if 1 <= unit_num <= 72:
            category = "PH 1"
        elif 101 <= unit_num <= 324:
            category = "PH 2"
        else:
            category = "Needs Manual Review - Out of Range"
    else:
        # No valid unit number was found at all.
        # Check if they provided a Building number but no Unit
        if re.search(r'\b(?:BLDG|BUILDING|BLG|B)[\s\-#]*\d+', addr_str):
            category = "Needs Manual Review - Only Bldg Number Found"
        # Purely text (like "CIUDAD DE STRIKE PHASE 2" without any valid unit ranges)
        else:
            category = "Needs Manual Review - No Number Found"

    return pd.Series([True, clean_unit_str if unit_str else None, category])


if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)

    address_col = st.selectbox("Select the Address Column from your file:", df.columns)

    if st.button("Run Filtering System"):
        df[['Is_Ciudad_De_Strike', 'Evaluated_Unit', 'Category']] = df[address_col].apply(parse_address)
        st.session_state['processed_df'] = df

if 'processed_df' in st.session_state:
    df = st.session_state['processed_df']

    st.divider()
    st.subheader("Filter Summary Dashboard")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Ciudad de Strike", (df['Is_Ciudad_De_Strike'] == True).sum())
    c2.metric("Phase 1 (1-72)", (df['Category'] == 'PH 1').sum())
    c3.metric("Phase 2 (101-324)", (df['Category'] == 'PH 2').sum())
    c4.metric("Needs Review (Strike Only)", df['Category'].str.startswith('Needs Manual Review').sum())

    st.divider()

    selected_filter = st.radio(
        "**Select Category View:**",
        ["All Records", "PH 1 Only", "PH 2 Only", "Needs Manual Review", "Excluded (Non-Strike / Molino)"],
        horizontal=True
    )

    if selected_filter == "PH 1 Only":
        view_df = df[df['Category'] == 'PH 1']
    elif selected_filter == "PH 2 Only":
        view_df = df[df['Category'] == 'PH 2']
    elif selected_filter == "Needs Manual Review":
        view_df = df[df['Category'].str.startswith('Needs Manual Review')]
    elif selected_filter == "Excluded (Non-Strike / Molino)":
        view_df = df[df['Category'].str.startswith('Excluded')]
    else:
        view_df = df

    st.write(f"Showing **{len(view_df)}** entries:")
    st.dataframe(view_df, use_container_width=True)

    csv = view_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"Export '{selected_filter}' to CSV",
        data=csv,
        file_name=f"Ciudad_de_Strike_{selected_filter.replace(' ', '_').replace('/', '_')}.csv",
        mime="text/csv"
    )