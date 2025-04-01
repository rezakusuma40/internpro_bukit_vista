import pandas as pd
import re
import nltk
from nltk.corpus import stopwords
from langdetect import detect
import spacy
import stanza

nltk.download("punkt")
nltk.download("punkt_tab")
nltk.download("stopwords")
stanza.download("id")

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

# baca CSV
df = pd.read_csv("../data/processed_penginapan_bukitvista.csv")

# terapkan preprocessing ke kolom description
df["processed_description"] = df["description"].apply(preprocess_desc)

# simpan hasilnya
df.to_csv("../data/desc_processed_penginapan_bukitvista.csv", index=False)