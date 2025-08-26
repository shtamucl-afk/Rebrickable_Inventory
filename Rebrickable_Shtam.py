import streamlit as st
import pandas as pd
import requests
from collections import defaultdict

# --- CONFIG ---
API_KEY = 'b1aa8e758f4416a87738eeeac71bbda5'  # Replace with your actual API key

# --- Load category mapping from CSV ---
category_df = pd.read_csv("part_categories.csv")
category_map = dict(zip(category_df['id'], category_df['name']))

# --- Load Favourite Sets ---
favourite_df = pd.read_csv("Favourite Sets.csv", encoding='latin1')
favourite_df.columns = favourite_df.columns.str.strip()
favourite_df['set_num'] = favourite_df['set_num'].str.strip()
favourite_df['name'] = favourite_df['name'].str.strip()
favourite_sets = dict(zip(favourite_df['set_num'], favourite_df['name']))

# --- Sidebar Input ---
st.sidebar.header("Select A Set")

set_choice = st.sidebar.selectbox(
    "Choose a favourite set",
    options=list(favourite_sets.keys()),
    format_func=lambda x: favourite_sets.get(x, x)
)

manual_set_id = st.sidebar.text_input("Or enter a Set ID manually", value="")
final_set_id = manual_set_id.strip() if manual_set_id else set_choice

# --- Fetch Set Metadata ---
@st.cache_data
def fetch_set_metadata(set_id):
    url = f'https://rebrickable.com/api/v3/lego/sets/{set_id}/'
    response = requests.get(url, headers={'Authorization': f'key {API_KEY}'})
    if response.status_code != 200:
        return None
    return response.json()

# --- Fetch Theme Name ---
@st.cache_data
def fetch_theme_name(theme_id):
    url = f'https://rebrickable.com/api/v3/lego/themes/{theme_id}/'
    response = requests.get(url, headers={'Authorization': f'key {API_KEY}'})
    if response.status_code != 200:
        return "Unknown"
    return response.json().get('name', 'Unknown')

# --- Fetch Inventory ---
@st.cache_data
def fetch_inventory(set_id):
    base_url = f'https://rebrickable.com/api/v3/lego/sets/{set_id}/parts/'
    params = {'page': 1, 'page_size': 1000}
    all_parts = []

    while True:
        response = requests.get(base_url, headers={'Authorization': f'key {API_KEY}'}, params=params)
        if response.status_code != 200:
            st.error(f"API Error: {response.status_code}")
            break
        data = response.json()
        all_parts.extend(data['results'])
        if not data['next']:
            break
        params['page'] += 1

    # Group by element_id
    element_group = defaultdict(lambda: {
        'element_id': '',
        'part_num': '',
        'part_name': '',
        'part_cat_id': None,
        'color_name': '',
        'quantity': 0,
        'part_img_url': ''
    })

    for part in all_parts:
        eid = part['element_id']
        element_group[eid]['element_id'] = eid
        element_group[eid]['part_num'] = part['part']['part_num']
        element_group[eid]['part_name'] = part['part']['name']
        element_group[eid]['part_cat_id'] = part['part']['part_cat_id']
        element_group[eid]['color_name'] = part['color']['name']
        element_group[eid]['quantity'] += part['quantity']
        element_group[eid]['part_img_url'] = part['part']['part_img_url']

    grouped_by_element = list(element_group.values())

    # Group by part_num
    part_group = defaultdict(lambda: {
        'part_num': '',
        'part_name': '',
        'category_name': '',
        'variants': []
    })

    for item in grouped_by_element:
        pnum = item['part_num']
        part_group[pnum]['part_num'] = pnum
        part_group[pnum]['part_name'] = item['part_name']
        part_group[pnum]['category_name'] = category_map.get(item['part_cat_id'], 'Unknown')
        part_group[pnum]['variants'].append({
            'element_id': item['element_id'],
            'color_name': item['color_name'],
            'quantity': item['quantity'],
            'part_img_url': item['part_img_url']
        })

    return pd.DataFrame(part_group.values())

# --- Main UI ---
set_info = fetch_set_metadata(final_set_id)
df = fetch_inventory(final_set_id)

if set_info and not df.empty:
    st.set_page_config(page_title=f"{set_info['name']} - Lego Inventory List", layout="wide")

    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown(
            f"<img src='{set_info['set_img_url']}' style='height:250px; object-fit:contain;'>",
            unsafe_allow_html=True
        )

    with col2:
        st.title(f"{set_info['name']} - Lego Inventory List")
        theme_name = fetch_theme_name(set_info.get('theme_id'))
        st.markdown(
            f"""
            <div style='line-height:1.4; font-size:16px'>
            <b>Set ID:</b> <code>{final_set_id}</code> • Powered by Rebrickable API<br>
            <b>Number of Parts:</b> <code>{set_info.get('num_parts', 'N/A')}</code><br>
            <b>Year Released:</b> <code>{set_info.get('year', 'N/A')}</code><br>
            <b>Theme:</b> <code>{theme_name}</code>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<hr style='margin-top:10px; margin-bottom:0px; border-width:3px; border-color:#333; border-style:solid;'>", unsafe_allow_html=True)


    # --- Filters in Sidebar ---
    all_colors = sorted({
        v['color_name']
        for row in df.itertuples()
        for v in getattr(row, 'variants', [])
    })
    all_categories = sorted(df['category_name'].unique())

    
    # --- 0) Initialize session_state defaults BEFORE creating any widgets ---
    if "color_search" not in st.session_state:
        st.session_state.update({
            "color_search": "",
            "category_search": "",
            "part_search": "",
            "color_filter": [],
            "category_filter": [],
        })

    # --- 1) Define a clear callback (safe place to modify widget keys) ---
    def clear_filters():
        st.session_state.update({
            "color_search": "",
            "category_search": "",
            "part_search": "",
            "color_filter": [],
            "category_filter": [],
        })
        # No need to call st.rerun(); callbacks trigger a rerun automatically.

    with st.sidebar:
        st.header("🔍 Filters")

        # --- 2) Button uses callback; do NOT assign to st.session_state here ---
        
        st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
        st.button("🧹 Clear Filters", use_container_width=False, on_click=clear_filters)
        st.markdown("</div>", unsafe_allow_html=True)


        # --- 3) Text inputs (widget keys are now "owned" by the widgets) ---
        st.text_input("Search Color", key="color_search")
        st.text_input("Search Category", key="category_search")
        st.text_input("Search Part Description", key="part_search")

        # --- 4) Build filtered option lists from current search strings ---
        cs = st.session_state.color_search.strip().lower()
        cats = st.session_state.category_search.strip().lower()
        filtered_colors = [c for c in all_colors if cs in c.lower()]
        filtered_categories = [c for c in all_categories if cats in c.lower()]

        # --- 5) Sanitize selections BEFORE rendering multiselects ---
        # (Avoids "selected value not in options" when options shrink)
        st.session_state.color_filter = [
            c for c in st.session_state.color_filter if c in filtered_colors
        ]
        st.session_state.category_filter = [
            c for c in st.session_state.category_filter if c in filtered_categories
        ]

        # --- 6) Multiselects (no defaults needed; keys hold the values) ---
        st.multiselect(
            "Color (Exact Match)",
            options=filtered_colors,
            key="color_filter",
        )
        st.multiselect(
            "Category (Exact Match)",
            options=filtered_categories,
            key="category_filter",
        )

    # --- Display Grouped Table in Columns ---
    for _, row in df.iterrows():
        # Use session_state values instead of old local variables
        if st.session_state.part_search and st.session_state.part_search.lower() not in row['part_name'].lower():
            continue
        if st.session_state.category_filter and row['category_name'] not in st.session_state.category_filter:
            continue
        if st.session_state.category_search and st.session_state.category_search.lower() not in row['category_name'].lower():
            continue

        variants = row['variants']

        # Apply color filters
        if st.session_state.color_filter:
            variants = [v for v in variants if v['color_name'] in st.session_state.color_filter]
        if st.session_state.color_search:
            variants = [v for v in variants if st.session_state.color_search.lower() in v['color_name'].lower()]

        if not variants:
            continue
        # Render part header
        st.markdown(
            f"""
            <div style='font-family:Quire Sans; font-size:22px; margin-top:0px; margin-bottom:10px'>
            <b>{row['part_name']}</b>            
            <small>(ID: <code>{row['part_num']}</code>, Category: <code>{row['category_name']}</code>)</small>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Render variants in columns
        cols = st.columns(len(variants), width=len(variants)*150)
        for col, variant in zip(cols, variants):
            with col:
                st.markdown(
                    f"""
                    <div style='line-height:1.6; font-size:16px; margin-bottom:6px'>
                    <img src='{variant['part_img_url']}' width='80'><br>
                    <b>Color:</b> <code>{variant['color_name']}</code><br>
                    <b>Qty:</b> <code>{variant['quantity']}</code><br>
                    <b>Element ID:</b> <code>{variant['element_id']}</code>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        st.markdown("<hr style='margin-top:0px; margin-bottom:0px;'>", unsafe_allow_html=True)


