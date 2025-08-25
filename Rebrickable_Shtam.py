

import streamlit as st
import pandas as pd
import requests
from collections import defaultdict

# --- CONFIG ---
API_KEY = '3e72ebd83a22190e2274c1e68c3c394a'
SET_NUM = '75192-1'
BASE_URL = f'https://rebrickable.com/api/v3/lego/sets/{SET_NUM}/parts/'
HEADERS = {'Authorization': f'key {API_KEY}'}

# --- DATA FETCHING ---
@st.cache_data
def fetch_inventory():
    params = {'page': 1, 'page_size': 1000}
    all_parts = []

    while True:
        response = requests.get(BASE_URL, headers=HEADERS, params=params)
        if response.status_code != 200:
            st.error(f"API Error: {response.status_code}")
            break
        data = response.json()
        all_parts.extend(data['results'])
        if not data['next']:
            break
        params['page'] += 1

    # Group by element_id
    grouped = defaultdict(lambda: {
        'element_id': '',
        'part_num': '',
        'part_name': '',
        'color_name': '',
        'quantity': 0,
        'part_img_url': ''
    })

    for part in all_parts:
        eid = part['element_id']
        grouped[eid]['element_id'] = eid
        grouped[eid]['part_num'] = part['part']['part_num']
        grouped[eid]['part_name'] = part['part']['name']
        grouped[eid]['color_name'] = part['color']['name']
        grouped[eid]['quantity'] += part['quantity']
        grouped[eid]['part_img_url'] = part['part']['part_img_url']

    return pd.DataFrame(grouped.values())

# --- UI ---
st.set_page_config(page_title="LEGO UCS Falcon Inventory", layout="wide")
st.title("🛸 LEGO UCS Millennium Falcon Inventory")
st.markdown("Set **75192-1** • Powered by Rebrickable API")

df = fetch_inventory()

# --- Filters ---
color_filter = st.multiselect("Filter by Color", options=df['color_name'].unique())
min_qty = st.slider("Minimum Quantity", 1, int(df['quantity'].max()), 1)

filtered_df = df.copy()
if color_filter:
    filtered_df = filtered_df[filtered_df['color_name'].isin(color_filter)]
filtered_df = filtered_df[filtered_df['quantity'] >= min_qty]

# --- Display Table ---
for _, row in filtered_df.iterrows():
    cols = st.columns([1, 3])
    with cols[0]:
        st.image(row['part_img_url'], width=80)
    with cols[1]:
        st.markdown(f"**{row['part_name']}**")
        st.write(f"Part #: `{row['part_num']}`")
        st.write(f"Color: `{row['color_name']}`")
        st.write(f"Quantity: `{row['quantity']}`")
        st.write(f"Element ID: `{row['element_id']}`")
    st.markdown("---")
