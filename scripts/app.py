import streamlit as st
st.set_page_config(page_title="BukitVista Hybrid Search", layout="wide")
from hybrid_query_handler import hybrid_query


def format_number(num):
  if isinstance(num, (int, float)) and num.is_integer():
    return int(num)
  return num

st.markdown("<h1 style='text-align: center;'>🔍 Find a Room in BukitVista!</h1>", unsafe_allow_html=True)

# --- input section ---
with st.expander("🔧 Search Settings", expanded=True):
  user_text = st.text_input("Search Description")
  user_address = st.text_input("Address")

  col1, col2 = st.columns(2)
  with col1:
    price_range = st.slider("💰 Price per Night (USD)", 0, 1000, (0, 1000))
  with col2:
    alpha = st.slider("📊 Hybrid Score Balance (0 = keyword, 1 = semantic)", 0.0, 1.0, 0.5, step=0.05)

  col1, col2, col3, col4, col5 = st.columns(5)
  with col1:
    bathrooms = st.number_input("🛁 Bathrooms", min_value=0.0, step=1.0)
  with col2:
    bedrooms = st.number_input("🛏 Bedrooms", min_value=0.0, step=1.0)
  with col3:
    rooms = st.number_input("🚪 Rooms", min_value=0.0, step=1.0)
  with col4:
    garages = st.number_input("🚗 Garages", min_value=0.0, step=1.0)
  with col5:
    max_guests = st.number_input("👥 Max Guests", min_value=0.0, step=1.0)

  sort_by = st.selectbox("Sort Results By", ["relevancy", "latest update", "cheapest", "most expensive"])

# --- when clicked ---
if st.button("🔍 Search"):
  filters = {}

  if price_range != (0, 1000):
    filters["price_per_night"] = {
      "min": price_range[0],
      "max": price_range[1]
    }

  if bathrooms > 0:
    filters["bathrooms"] = {"$eq": bathrooms}
  if bedrooms > 0:
    filters["bedrooms"] = {"$eq": bedrooms}
  if rooms > 0:
    filters["rooms"] = {"$eq": rooms}
  if garages > 0:
    filters["garages"] = {"$eq": garages}
  if max_guests > 0:
    filters["max_guests"] = {"$eq": max_guests}

  results = hybrid_query(
    user_text=user_text,
    user_address=user_address,
    filters=filters,
    top_k=30,
    alpha=alpha
  )

  relevant_results = [r for r in results if r.get("hybrid_score", 0) >= 0.275]

  if sort_by == "latest update":
    relevant_results.sort(key=lambda x: x["metadata"].get("update_days_ago", 9999))
  elif sort_by == "cheapest":
    relevant_results.sort(key=lambda x: x["metadata"].get("price_per_night", float('inf')))
  elif sort_by == "most expensive":
    relevant_results.sort(key=lambda x: x["metadata"].get("price_per_night", -1), reverse=True)

  st.subheader(f"Found {len(relevant_results)} Result(s)")
  # display results in rows of 3 columns
  cols = st.columns(3)
  for idx, item in enumerate(relevant_results):
    meta = item["metadata"]
    try:
      meta["price_per_night"] = round(meta["price_per_night"], 2)
    except:
      meta["price_per_night"] = "N/A"

    # potong deskripsi jika terlalu panjang
    desc = meta.get("all_text", "")
    try:
      words = desc.split('description: ')[1].split()
      tooltip_desc = " ".join(words[:100]) + "..." if len(words) > 100 else " ".join(words)
    except:
      tooltip_desc = ""

    with cols[idx % 3]:
      st.markdown(f"#### 🏠 {meta.get('name', 'Unnamed')}")
      
      # gambar dengan tooltip saat hover
      if meta.get("picture_url"):
        st.markdown(
          f"<div title='{tooltip_desc}' style='text-align:center;'>"
          f"<img src='{meta['picture_url']}' alt='Room Image' style='width:100%; border-radius:8px;'/>"
          f"</div>",
          unsafe_allow_html=True
        )
      
      st.markdown(f"**📍 {meta.get('address_original', '-')}**")
      st.markdown(
        f"{format_number(meta.get('bathrooms', '-'))} 🛁 &nbsp;&nbsp; "
        f"{format_number(meta.get('bedrooms', '-'))} 🛏 &nbsp;&nbsp; "
        f"{format_number(meta.get('rooms', '-'))} 🚪 &nbsp;&nbsp; "
        f"{format_number(meta.get('garages', '-'))} 🚗 &nbsp;&nbsp; "
        f"{format_number(meta.get('max_guests', '-'))} 👥"
      )
      st.markdown(f"💰 **${meta.get('price_per_night', '-')}/night**")
      st.markdown(f"🕒 {meta.get('update_days_ago', '-')} days ago")

      links = []
      if meta.get("lodging_url"):
        links.append(f"[🌐 BukitVista]({meta['lodging_url']})")
      if meta.get("airbnb_url"):
        links.append(f"[🏡 Airbnb]({meta['airbnb_url']})")
      if meta.get("gmap_url"):
        links.append(f"[🗺 Maps]({meta['gmap_url']})")
      st.markdown(" | ".join(links), unsafe_allow_html=True)

      if "hybrid_score" in item:
        st.markdown(f"📊 Score: {item['hybrid_score']:.3f}")
