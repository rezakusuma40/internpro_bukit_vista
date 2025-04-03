import pandas as pd
import re
from nltk.corpus import stopwords
from langdetect import detect
import spacy
import stanza
import string

# load model SpaCy untuk bahasa Inggris
nlp_en = spacy.load("en_core_web_sm")
nlp_id = stanza.Pipeline("id")

# daftar frasa yang akan dihapus (gunakan regex untuk variasi)
patterns = [
  r"carefully managed by bukit vista",
  r"exclusively managed by bukit vista",
  r"carefully curated by bukit vista",
  r"exclusively curated by bukit vista",
  r"managed by bukit vista",
  r"curated by bukit vista",
  r"by bukit vista",
  r"bukit vista",
  r"welcome",
  r"about this space",
  r"the space",
  r"guest access",
  r"other things to note",
  r"note: price valid until \w+ \d+",
  r"this property availability is updated daily",
  r"availability of this \w is updated daily",
  r"book\w{0,3} now on airbnb",
  r"book now",
]

# gabungkan semua pola menjadi satu regex
pattern_regex = r"|".join(patterns)

def preprocess_desc(text):
  if pd.isna(text):  # handle missing values
    return ""

  # hapus kata/frase tertentu
  text = re.sub(pattern_regex, "", text).strip()
  
  # hapus simbol yang tidak perlu
  text = re.sub(r"[^a-zA-Z0-9\s]", "", text)

  lang = detect(text)  # deteksi bahasa
  if lang == "en":
    # inisialisasi stopwords dan lemmatizer
    stop_words = set(stopwords.words("english"))
    doc = nlp_en(text)
    text = " ".join([word.lemma_ for word in doc if word.text not in stop_words])  # lemmatization bahasa Inggris
  elif lang == "id":
    # inisialisasi stopwords dan lemmatizer
    stop_words = set(stopwords.words("indonesian"))
    doc = nlp_id(text)
    text = " ".join([word.lemma for sentence in doc.sentences for word in sentence.words if word.text not in stop_words])
  
  return re.sub(r"\s+", " ", text.strip())  # hapus spasi berlebih

# Fungsi untuk menghapus emoji
def remove_emoji(text):
  emoji_pattern = re.compile("["
    u"\U0001F600-\U0001F64F"  # Emotikon
    u"\U0001F300-\U0001F5FF"  # Simbol & Piktogram
    u"\U0001F680-\U0001F6FF"  # Transportasi & Simbol lainnya
    u"\U0001F700-\U0001F77F"  # Simbol Alkimia
    u"\U0001F780-\U0001F7FF"  # Simbol Geometris Tambahan
    u"\U0001F800-\U0001F8FF"  # Simbol Suara & Musik
    u"\U0001F900-\U0001F9FF"  # Simbol Misc
    u"\U0001FA00-\U0001FA6F"  # Simbol Game & Olahraga
    u"\U0001FA70-\U0001FAFF"  # Simbol Barang Rumah Tangga
    u"\U00002702-\U000027B0"  # Simbol Misc Lainnya
    u"\U000024C2-\U0001F251"  # Simbol Enclosed
    "]+", flags=re.UNICODE)
  return emoji_pattern.sub(r"", text)

# Fungsi untuk menghapus tanda baca
def remove_punctuation(text):
  return text.translate(str.maketrans("", "", string.punctuation))

# baca CSV
df = pd.read_csv("data/processed_penginapan_bukitvista.csv")

# Bersihkan teks
df["processed_description"] = df["description"].astype(str).apply(lambda x: remove_punctuation(remove_emoji(x)))

# terapkan preprocessing ke kolom description
df["processed_description"] = df["processed_description"].apply(preprocess_desc)

# simpan hasilnya
df.to_csv("data/desc_processed_penginapan_bukitvista.csv", index=False)