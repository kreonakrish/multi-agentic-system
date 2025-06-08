import sys
import os
import faiss                   # pip install faiss-cpu
import pandas as pd
from pathlib import Path
import json
import numpy as np
import uuid
import pickle

print("Starting test_faiss_ingestion.py")
print("Python version:", sys.version)
print("__file__:", __file__)

# --- Sample input, as per your parameters ---

dataset_nm = "nfl-favorite-team"
metadata = {
    "tool": "github_tool",
    "dataset": "nfl-favorite-team",
    "source_url": "https://raw.githubusercontent.com/fivethirtyeight/data/refs/heads/master/nfl-favorite-team/team-picking-categories.csv",
    "dataset_info": {
        "name": "nfl-favorite-team",
        "path": "nfl-favorite-team"
    }
}
location = {
    "location": r"C:\multi-agentic-system\python-ml\data\github_tool\nfl-favorite-team.json",
    "type": "local_file"
}

print("About to load data from:", location["location"])

# --- 1. Load data from the JSON file ---
with open(location["location"], "r") as f:
    data = json.load(f)

print(f"Loaded {len(data)} rows from JSON.")

# For FAISS, join all columns as one document string per row
df = pd.DataFrame(data)
documents = df.astype(str).apply(lambda row: " | ".join(row), axis=1).tolist()

print("Loaded data with", len(documents), "documents")

# Generate dummy embeddings (random floats, size 384)
embedding_dim = 384
embeddings = np.random.rand(len(documents), embedding_dim).astype('float32')  # FAISS requires float32

# --- Flatten metadata so it contains only simple types ---
def flatten_metadata(metadata, prefix=""):
    items = []
    for k, v in metadata.items():
        new_key = f"{prefix}_{k}" if prefix else k
        if isinstance(v, (str, int, float, bool)) or v is None:
            items.append((new_key, v))
        elif isinstance(v, dict):
            items.extend(flatten_metadata(v, new_key).items())
        elif isinstance(v, (list, tuple)):
            items.append((new_key, str(v)))  # convert list/tuple to string
        else:
            items.append((new_key, str(v)))  # fallback: stringify anything else
    return dict(items)

flat_metadata = flatten_metadata(metadata)
metadatas = [flat_metadata for _ in range(len(documents))]
ids = [str(uuid.uuid4()) for _ in range(len(documents))]

# --- 2. Setup FAISS Index ---
index_dir = Path(__file__).parent / "faiss_data"
index_dir.mkdir(parents=True, exist_ok=True)
faiss_index_path = index_dir / f"{dataset_nm}.index"
meta_path = index_dir / f"{dataset_nm}_meta.pkl"

print("Created/using index dir:", index_dir)
print("Directory contents:", os.listdir(index_dir))

# Build FAISS index (L2 or cosine, here using L2)
faiss_index = faiss.IndexFlatL2(embedding_dim)  # Simple L2 index

print("Adding embeddings to FAISS index...")
faiss_index.add(embeddings)
print("Added embeddings.")

# Save the index and meta info
faiss.write_index(faiss_index, str(faiss_index_path))
print(f"Saved FAISS index to {faiss_index_path}")

# Save accompanying metadata (including docs and metadatas)
with open(meta_path, "wb") as f:
    pickle.dump({"ids": ids, "documents": documents, "metadatas": metadatas}, f)
print(f"Saved metadata to {meta_path}")

print(f"Inserted {len(documents)} docs into FAISS index '{dataset_nm}'.")

# --- 3. Query FAISS for the first embedding ---
print("Querying FAISS with first embedding...")
D, I = faiss_index.search(embeddings[0:1], 3)  # Query top 3 nearest neighbors

# Load metadata
with open(meta_path, "rb") as f:
    meta_loaded = pickle.load(f)

print("Query results:")
for idx, dist in zip(I[0], D[0]):
    doc = meta_loaded["documents"][idx]
    meta = meta_loaded["metadatas"][idx]
    print(f"Doc: {doc[:60]}..., Meta: {meta}, Distance: {dist:.4f}")

print("Script finished successfully!")
