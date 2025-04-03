import pandas as pd
from datetime import datetime
import re
import json
from requests_html import HTMLSession

# Load API key from JSON file
with open("cred.json", "r") as file:
  config = json.load(file)
  url = config["EXAMPLE_URL"]

today = datetime.today()

# baca CSV
df = pd.read_csv("data/penginapan_bukitvista.csv")
date_format = "Updated on %B %d, %Y at %I:%M %p"
df['property_type'] = df['property_type'].fillna('')
df['property_status'] = df['property_status'].fillna('')
df['zip'] = df['zip'].fillna('')
df['state'] = df['state'].fillna('')
df['area'] = df['area'].fillna('')
df['country'] = df['country'].fillna('')
df['address'] = df['address'].fillna('')
df['author'] = df['author'].fillna('Bukit Vista')
df['bedrooms'] = df['bedrooms'].fillna(0)
df['rooms'] = df['rooms'].fillna(0)
df['bathrooms'] = df['bathrooms'].fillna(0)
df['garages'] = df['garages'].fillna(0)
df['max_guests'] = df['max_guests'].fillna(0)

# df['months_since'] = pd.NA
# df['update_days_ago'] = pd.NA
# df['price_per_night_usd'] = pd.NA

for index, row in df.iterrows():
  description = f"{row['name']} {row['property_type']} {row['property_status']} {row['description']}"
  df.at[index, 'description'] = description.replace('w/', 'with').lower()

  if 'santorini' in df.at[index, 'description']:
    df.at[index, 'address'] = 'santorini, thira, thera, greece, yunani, abroad, overseas, luar negeri'
  else:
    address = f"{row['address']} {row['state']} {row['area']} {row['country']} {row['zip']}"
    df.at[index, 'address'] = address.lower().replace('.0', '')

  if pd.notna(row['date_since']):
    mon = int(row['date_since'].split()[0])
    if 'years' in row['date_since']:
      mon = mon * 12
    df.at[index, 'months_since'] = mon
  else:
    df.at[index, 'months_since'] = 0

  if pd.notna(row['last_update']):
    last_update = datetime.strptime(row['last_update'], date_format)
    df.at[index, 'update_days_ago'] = (today - last_update).days
  else:
    df.at[index, 'update_days_ago'] = df.at[index, 'months_since'] * 30

  if pd.notna(row['price']):
    if re.search(r'month|bulan', row['price'], re.IGNORECASE):
      price_period = 30
    elif re.search(r'2 nights|2 malam', row['price'], re.IGNORECASE):
      price_period = 2
      row['price'] = re.sub(r'2 nights|2 malam', '', row['price'], flags=re.IGNORECASE)
    elif re.search(r'night|malam', row['price'], re.IGNORECASE):
      price_period = 1

    price_match = "".join(filter(str.isdigit, row['price']))
    if price_match:
      price_per_night = int(price_match) / price_period
      if 'Rp' in row['price']:
        response = HTMLSession().get(url).json()
        idr_to_usd = response["conversion_rates"]["IDR"]
        price_per_night = price_per_night / idr_to_usd
    else:
      price_per_night = pd.NA

    df.at[index, 'price_per_night'] = price_per_night
    
  else:
    df.at[index, 'price_per_night'] = 1000 # Extremely high price for filtering
  
# hapus kolom
df.drop(columns=['name', 'property_type', 'property_status', 'date_since', 'last_update', 'lodging_url', 'airbnb_url', 'gmap_url', 'area', 'state', 'zip', 'country', 'city', 'price', 'property_id'], inplace=True)

# simpan hasilnya
df.to_csv("data/processed_penginapan_bukitvista.csv", index=False)