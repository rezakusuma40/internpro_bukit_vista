import json
import re
import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz
from sentence_transformers import SentenceTransformer
from transformers import MarianMTModel, MarianTokenizer
from pinecone import Pinecone
import numpy as np
from langdetect import detect

# --- config & model init ---
# with open("cred.json", "r") as file:
#   config = json.load(file)
config = st.secrets
pinecone_api_key = config['PINECONE_API_KEY']

pc = Pinecone(api_key=pinecone_api_key)
index = pc.Index("penginapan-bukitvista")

@st.cache_resource
def load_embedding_model():
  return SentenceTransformer("BAAI/bge-m3")

@st.cache_resource
def load_translation_model():
  tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-mul-en")
  model = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-mul-en")
  return tokenizer, model

embedding_model = load_embedding_model()
translation_tokenizer, translation_model = load_translation_model()

# known addresses list for fuzzy matching
df = pd.read_parquet("data/known_addresses.parquet")
known_addresses = df["address"].tolist()
known_addresses = [x.strip() for x in known_addresses]

# --- utility functions ---
def translate_text(text):
  batch = translation_tokenizer.prepare_seq2seq_batch([text], return_tensors="pt")
  translated = translation_model.generate(**batch)
  return translation_tokenizer.decode(translated[0], skip_special_tokens=True)

def correct_typo(text, choices):
  match, score, _ = process.extractOne(text, choices, scorer=fuzz.WRatio)
  return match if score > 75 else None

def clean_query(text):
  text = re.sub(r'\W+', ' ', text.lower())
  return text.strip()

def is_english(text):
  try:
    return detect(text) == "en"
  except:
    return False

# --- main query handler ---
def hybrid_query(
    user_text: str = "",
    user_address: str = "",
    filters: dict = None,
    top_k: int = 20,
    alpha: float = 0.5
):
  if filters is None:
    filters = {}

  # --- handle user_text ---
  text_vector = None
  keyword_terms = None
  if user_text:
    if is_english(user_text):
      corrected = correct_typo(user_text, known_addresses + user_text.split())
      keyword_terms = clean_query(corrected or user_text)
      text_vector = embedding_model.encode(user_text)
    else:
      translated = translate_text(user_text)
      keyword_terms = clean_query(translated)
      text_vector = embedding_model.encode(translated)

  # --- handle address box ---
  address_filter = None
  zip_filter = None
  if user_address:
    match = correct_typo(user_address, known_addresses)
    if match:
      address_filter = match

    zip_match = re.search(r'\b\d{5}\b', user_address)
    if zip_match:
      zip_filter = zip_match.group()

  # --- build filter ---
  filter_dict = {}

  if address_filter:
    filter_dict["address"] = {"$eq": address_filter}
  if zip_filter:
    filter_dict["zip_code"] = {"$eq": zip_filter}

  for key, val in filters.items():
    if key == "price_per_night" and isinstance(val, dict):
      min_price = val.get("min")
      max_price = val.get("max")
      if min_price is not None and max_price is not None:
        filter_dict[key] = {"$gte": min_price, "$lte": max_price}
      elif min_price is not None:
        filter_dict[key] = {"$gte": min_price}
      elif max_price is not None:
        filter_dict[key] = {"$lte": max_price}
    elif isinstance(val, dict) and "$eq" in val:
      filter_dict[key] = {"$eq": val["$eq"]}

  query_result = index.query(
    vector=text_vector.tolist() if text_vector is not None else [0.0] * 1024,
    filter=filter_dict or None,
    top_k=top_k,
    include_metadata=True,
    include_values=False
  )

  results = query_result["matches"]
  if keyword_terms:
    for item in results:
      meta_text = item["metadata"].get("all_text_clean", "")
      item["keyword_score"] = fuzz.token_sort_ratio(keyword_terms, meta_text)
  else:
    for item in results:
      item["keyword_score"] = 0

  for item in results:
    hybrid_score = alpha * item["score"] + (1-alpha) * (item["keyword_score"] / 100)
    item["hybrid_score"] = hybrid_score
  results = sorted(results, key=lambda x: x["hybrid_score"], reverse=True)

  return results