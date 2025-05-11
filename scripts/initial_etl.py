import time
from requests_html import HTMLSession
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import re
import json
import roman
from langdetect import detect
from transformers import MarianMTModel, MarianTokenizer
import spacy
from nltk.corpus import stopwords
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
import uuid

address_entities = set()
date_format = "Updated on %B %d, %Y at %I:%M %p"
today = datetime.today()

# get exchange rate idr to usd
with open("cred.json", "r") as file:
   config = json.load(file)
   exchage_rate_url = config["EXAMPLE_URL"]
   pinecone_api_key = config['PINECONE_API_KEY']

# model for translation and lemmatization
model_name = "Helsinki-NLP/opus-mt-mul-en"
tokenizer = MarianTokenizer.from_pretrained(model_name)
translate_model = MarianMTModel.from_pretrained(model_name)
nlp_en = spacy.load("en_core_web_sm")
stop_words = set(stopwords.words("english"))

def remove_emojis(text):
   emoji_pattern = re.compile(
      "["
      "\U0001F600-\U0001F64F"  # emoticons
      "\U0001F300-\U0001F5FF"  # symbols & pictographs
      "\U0001F680-\U0001F6FF"  # transport & map symbols
      "\U0001F1E0-\U0001F1FF"  # flags
      "\U00002702-\U000027B0"  # other symbols
      "\U000024C2-\U0001F251"  # enclosed characters
      "\U0001F900-\U0001F9FF"  # supplemental symbols
      "\U0001FA70-\U0001FAFF"  # extended symbols
      "\U0001F000-\U0001F02F"  # Mahjong, domino tiles
      "]+", flags=re.UNICODE
   )
   return emoji_pattern.sub(r'', text)

# daftar frasa yang akan dihapus (gunakan regex untuk variasi)
patterns = [
   r"(carefully |exclusively )?(managed |curated )?(by )?bukit vista",
   r"about (the|this)? space",
   r"welcome",
   r"guest access",
   r"other things to note",
   r"note: price valid until \w+ \d+",
   r"this property availability is updated daily",
   r"availability of this \w is updated daily",
   r"book\w{0,3} now( on airbnb)?",
]
# gabungkan semua pola menjadi satu regex
useless_words = r"|".join(patterns)

def from_roman(match):
   value = match.group()
   try:
      return str(roman.fromRoman(value.upper()))
   except roman.InvalidRomanNumeralError:
      return value  # ignore non-Roman numbers


def clean_address(address):
   address = ', '.join(address)
   address = re.sub(r'\b[IVXLCDM]+\b', lambda match: str(from_roman(match)), address)
   address = address.lower()
   address = re.sub(r'[^\w\s,]',' ', address)
   address = re.sub(r'\bjalan(\s+raya)?\b|\bjln?(\s+raya)?\b|\bstreet\b|\bst\b','jl', address)
   address = re.sub(r'\bgang\b|\bgg\b|\bgn\b','gg', address)
   address = re.sub(r'\bdesa\b|\bkecamatan\b|\bkelurahan\b|\bkabupaten\b|\bkota\b|\bregency\b|\bkel\b|\bkec\b|\bkab\b|\bresidence\b|\bpantai\b','', address)
   address = re.sub(r'\bsouth (\w+)|(\w+) sel\b', r'\1 selatan', address)
   address = re.sub(r'\bnorth (\w+)', r'\1 utara', address)
   address = re.sub(r'\beast (\w+)', r'\1 timur', address)
   address = re.sub(r'\bwest (\w+)', r'\1 barat', address)
   try:
      zip_code = re.search(r'\b\d{5}\b', address).group().strip()
      address = re.sub(zip_code, '', address)
   except:
      zip_code = ''
   address = re.sub(r'\s+',' ', address).strip()
   address = re.split(r'\s*,\s*', address)
   address = set(address)
   return address, zip_code

def clean_all_text(text):
   text = text.replace('w/', 'with').lower()
   text = re.sub(useless_words, "", text)
   text = re.sub(r'[^\x00-\x7F]', ' ', text)
   text = remove_emojis(text) # hapus emoji
   text = re.sub(r"\s+", " ", text.strip()) # hapus spasi berlebih
   lang = detect(text) # deteksi bahasa
   if lang != "en": # translate ke bahasa Inggris
      inputs = tokenizer(text, return_tensors="pt", padding=True)
      translated = translate_model.generate(**inputs)
      text = tokenizer.decode(translated[0], skip_special_tokens=True)
   return text

def lemmatize(text):
   text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
   text = re.sub(r"\s+", " ", text.strip()) # hapus spasi berlebih lagi
   doc  = nlp_en(text) # inisialisasi lemmatizer
   text = " ".join([word.lemma_ for word in doc if word.text not in stop_words])  # lemmatization bahasa Inggris
   return text

def get_details(lodging_list, picture_url, lodging_url, name, author, date_since):
   print(lodging_url)
   res = session.get(lodging_url)
   soup = BeautifulSoup(res.content, 'html.parser')
   lodging_data = {}
   lodging_data['author']      = author
   lodging_data['name']        = name
   lodging_data['lodging_url'] = lodging_url
   lodging_data['picture_url'] = picture_url
   try    : lodging_data['airbnb_url']  = soup.select_one('a:-soup-contains("Book")')['href']
   except : pass

   try:
      lodging_data['months_since'] = int(date_since.split()[0])
      if 'years' in date_since:
         lodging_data['months_since'] = lodging_data['months_since'] * 12
   except:
      pass

   address = []
   try : address_section = soup.find('div','property-address-wrap')
   except : pass
   else :
      try    :
         lodging_data['address_original'] = address_section.select_one('li.detail-address>span').get_text(' ', True)
         address.append(lodging_data['address_original'])
      except : pass
      try    : address.append(address_section.select_one('li.detail-state>span').get_text(' ', True))
      except : pass
      try    : address.append(address_section.select_one('li.detail-area>span').get_text(' ', True))
      except : pass
      try    : address.append(address_section.select_one('li.detail-country>span').get_text(' ', True))
      except : pass
      
   lodging_data['address'], lodging_data['zip_code'] = clean_address(address)
   [address_entities.add(entity.strip()) for entity in lodging_data['address']]
   lodging_data['address'] = list(lodging_data['address'])
   
   try    : lodging_data['gmap_url'] = address_section.select_one('div.block-title-wrap a')['href']
   except : pass
   if lodging_data['zip_code'] == '':
      try    : lodging_data['zip_code'] = address_section.select_one('li.detail-zip>span').get_text(' ', True)
      except : pass
         
   try    :
      last_update = soup.find('h2', string='Details').find_next_sibling('span').get_text(strip=True)
   except :
      try: lodging_data['update_days_ago'] = lodging_data['months_since'] * 30
      except: pass
   else:
      last_update = datetime.strptime(last_update, date_format)
      lodging_data['update_days_ago'] = (today - last_update).days
   
   try :
      other_detail = soup.select_one('div.detail-wrap')
   except :
      pass
   else :
      try    : lodging_data['property_id'] = other_detail.find('strong', string='Property ID:').find_next_sibling('span').get_text(strip=True)
      except : pass
      try    : lodging_data['bedrooms']    = float(other_detail.find('strong', string='Bedrooms:').find_next_sibling('span').get_text(strip=True))
      except : pass
      try    : lodging_data['rooms']       = float(other_detail.find('strong', string='Rooms:').find_next_sibling('span').get_text(strip=True))
      except : pass
      try    : lodging_data['bathrooms']   = float(other_detail.find('strong', string='Bathrooms:').find_next_sibling('span').get_text(strip=True))
      except : pass
      try    : lodging_data['garages']     = float(other_detail.find('strong', string='Garage:').find_next_sibling('span').get_text(strip=True))
      except : pass
      try    : lodging_data['max_guests']  = float(other_detail.find('strong', string='Guest Number:').find_next_sibling('span').get_text(strip=True))
      except : pass
   
      try    : price = other_detail.find('strong', string='Price:').find_next_sibling('span').get_text(strip=True)
      except : pass
      else   :
         if re.search(r'month|bulan', price, re.IGNORECASE):
            price_period = 30
         elif re.search(r'2 nights|2 malam', price, re.IGNORECASE):
            price_period = 2
            price = re.sub(r'2 nights|2 malam', '', price, flags=re.IGNORECASE)
         else:
            price_period = 1

         price_match = "".join(filter(str.isdigit, price))
         lodging_data['price_per_night'] = int(price_match) / price_period
         if 'Rp' in price:
            response = HTMLSession().get(exchage_rate_url).json()
            idr_to_usd = response["conversion_rates"]["IDR"]
            lodging_data['price_per_night'] = lodging_data['price_per_night'] / idr_to_usd

      try    : property_type   = other_detail.find('strong', string='Property Type:').find_next_sibling('span').get_text(strip=True)   
      except : property_type   = ''
      try    : property_status = other_detail.find('strong', string='Property Status:').find_next_sibling('span').get_text(strip=True)   
      except : property_status = ''

   try    : description = soup.select_one('.property-description-wrap .block-content-wrap').get_text(' ', True)
   except : description = soup.select_one('div[data-elementor-type="wp-post"]').get_text(' ', True)
      
   all_text = f"{name} description: {description} tags: {property_type} {property_status}"
   lodging_data['all_text'] = clean_all_text(all_text) # for semantic search
   lodging_data['all_text_clean'] = lemmatize(lodging_data['all_text']) # for keyword search

   lodging_list.append(lodging_data)
   print(len(lodging_list), name)

session = HTMLSession()
lodging_list = []

page_num = 1
while True:
   url = f'https://www.bukitvista.com/search-results/page/{page_num}'
   print(url)
   res = session.get(url)
   soup = BeautifulSoup(res.content, 'html.parser')
   lodgings = soup.select('.item-listing-wrap')
   for lodging in lodgings:
      picture_url = lodging.select_one('img')['src']
      lodging_url = lodging.select_one('h2.item-title>a')['href']
      name        = lodging.select_one('h2.item-title>a').get_text(strip=True)
      author      = lodging.select_one('div.item-author').get_text(strip=True)
      date_since  = lodging.select_one('div.item-date').get_text(strip=True)
      get_details(lodging_list, picture_url, lodging_url, name, author, date_since)
   count = soup.select_one('.listing-tools-wrap strong').text
   count = int(count.split()[0])
   if 1+count//9 == page_num:
      break
   page_num += 1

# simpan data sebagai dataframe
df = pd.DataFrame(lodging_list)
df.to_csv("data/penginapan_bukitvista.csv", index=False) # buat backup/kalo mau lihat2

df_adr = pd.DataFrame(list(address_entities), columns=["address"])
df_adr.to_parquet("data/known_addresses.parquet", index=False)

# init embedding model and Qdrant client
model = SentenceTransformer("BAAI/bge-m3")
index_name = "penginapan-bukitvista"

pc = Pinecone(api_key=pinecone_api_key)
index = pc.Index(index_name)

if index_name not in pc.list_indexes().names():
   pc.create_index(
      name=index_name,
      dimension=model.get_sentence_embedding_dimension(),
      metric="cosine",
      spec=ServerlessSpec(
         cloud="aws",
         region="us-east-1"
      )
   )
   # delete all vectors to refresh the index
if index.describe_index_stats()["total_vector_count"] != 0:
   index.delete(delete_all=True)
   print("Vector count after deletion:", index.describe_index_stats()["total_vector_count"])

# Build list of dicts for upserting
vectors_to_upsert = []
for record in lodging_list:
   vector = model.encode(record["all_text"])

   item = {
      "id": str(uuid.uuid4()),
      "values": vector.tolist(),
      "metadata": {k: record[k] for k in record}
      }

   vectors_to_upsert.append(item)

# Upsert to Pinecone
index.upsert(vectors=vectors_to_upsert)
time.sleep(3)