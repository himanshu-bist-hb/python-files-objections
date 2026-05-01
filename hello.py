import warnings
warnings.filterwarnings("ignore")

import re
import os
import pandas as pd
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from umap import UMAP
from hdbscan import HDBSCAN
from sklearn.feature_extraction.text import CountVectorizer


def load_data(filepath):
    df = pd.read_excel(filepath, dtype={"CLM_NUM": str})
    df.columns = df.columns.str.strip()
    return df


def preprocess(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"\d{1,2}/\d{1,2}/\d{2,4}", "", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def main():
    EXCEL_FILE = "claims.xlsx"       # <-- change to your file path
    OUTPUT_DIR = "bertopic_outputs"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Load & preprocess
    df = load_data(EXCEL_FILE)
    df["Cleaned_Notes"] = df["Claim_Notes"].apply(preprocess)

    valid_mask = df["Cleaned_Notes"].str.strip().str.len() > 10
    df_valid = df[valid_mask].copy().reset_index(drop=True)
    docs = df_valid["Cleaned_Notes"].tolist()
    print(f"Total documents for modelling: {len(docs)}")

    # 2. Build model components
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

    umap_model = UMAP(
        n_neighbors=15,
        n_components=5,
        min_dist=0.0,
        metric="cosine",
        random_state=42,
    )

    hdbscan_model = HDBSCAN(
        min_cluster_size=max(5, len(docs) // 50),
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )

    vectorizer_model = CountVectorizer(
        stop_words="english",
        min_df=2,
        ngram_range=(1, 2),
    )

    # 3. Fit BERTopic
    topic_model = BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer_model,
        top_n_words=10,
        nr_topics="auto",
        calculate_probabilities=True,
        verbose=True,
    )

    topics, probs = topic_model.fit_transform(docs)

    # 4. Attach results to dataframe
    df_valid["Topic_ID"] = topics
    df_valid["Topic_Probability"] = [p.max() if hasattr(p, "__len__") else p for p in probs]

    topic_info = topic_model.get_topic_info()
    label_map = dict(zip(topic_info["Topic"], topic_info["Name"]))
    df_valid["Topic_Label"] = df_valid["Topic_ID"].map(label_map)

    # 5. Print topic summary
    print("\n" + "=" * 60)
    print("TOPIC SUMMARY")
    print("=" * 60)
    print(topic_info[["Topic", "Count", "Name"]].to_string(index=False))

    print("\nTop keywords per topic:")
    for topic_id in sorted(topic_info["Topic"].unique()):
        if topic_id == -1:
            continue
        keywords = topic_model.get_topic(topic_id)
        kw_str = ", ".join([w for w, _ in keywords[:8]])
        print(f"  Topic {topic_id:>3}: {kw_str}")

    # 6. Save outputs
    results_path = os.path.join(OUTPUT_DIR, "claim_topic_results.xlsx")
    df_valid[["CLM_NUM", "Claim_Notes", "Topic_ID", "Topic_Label", "Topic_Probability"]].to_excel(
        results_path, index=False
    )
    print(f"\nResults saved -> {results_path}")

    topic_info_path = os.path.join(OUTPUT_DIR, "topic_info.xlsx")
    topic_info.to_excel(topic_info_path, index=False)
    print(f"Topic info saved -> {topic_info_path}")


if __name__ == "__main__":
    main()