import warnings
warnings.filterwarnings("ignore")

import re
import os
import pandas as pd
import numpy as np
from gensim import corpora
from gensim.models import LdaModel
from gensim.parsing.preprocessing import STOPWORDS
from nltk.stem import WordNetLemmatizer
import nltk

nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)


# ─────────────────────────────────────────
# 1. LOAD DATA
# ─────────────────────────────────────────
def load_data(filepath):
    df = pd.read_excel(filepath, dtype={"CLM_NUM": str})
    df.columns = df.columns.str.strip()
    return df


# ─────────────────────────────────────────
# 2. PREPROCESS
# ─────────────────────────────────────────
lemmatizer = WordNetLemmatizer()

def preprocess(text):
    if not isinstance(text, str):
        return []
    text = text.lower()
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"\d{1,2}/\d{1,2}/\d{2,4}", "", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    tokens = text.split()
    tokens = [lemmatizer.lemmatize(t) for t in tokens if t not in STOPWORDS and len(t) > 2]
    return tokens


# ─────────────────────────────────────────
# 3. MAIN
# ─────────────────────────────────────────
def main():
    EXCEL_FILE = "claims.xlsx"       # <-- change to your file path
    OUTPUT_DIR = "lda_outputs"
    NUM_TOPICS = 10                  # <-- change number of topics as needed
    NUM_WORDS  = 10                  # top keywords per topic
    PASSES     = 10                  # training passes over corpus

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load
    df = load_data(EXCEL_FILE)
    df["Tokens"] = df["Claim_Notes"].apply(preprocess)

    # Drop rows with too few tokens
    valid_mask = df["Tokens"].apply(len) >= 3
    df_valid = df[valid_mask].copy().reset_index(drop=True)
    tokenized_docs = df_valid["Tokens"].tolist()
    print(f"Total documents for modelling: {len(tokenized_docs)}")

    # Build dictionary & corpus
    dictionary = corpora.Dictionary(tokenized_docs)
    dictionary.filter_extremes(no_below=2, no_above=0.9)   # remove very rare/common words
    corpus = [dictionary.doc2bow(doc) for doc in tokenized_docs]

    # Train LDA
    print(f"\nTraining LDA with {NUM_TOPICS} topics...")
    lda_model = LdaModel(
        corpus=corpus,
        id2word=dictionary,
        num_topics=NUM_TOPICS,
        passes=PASSES,
        random_state=42,
        alpha="auto",
        eta="auto",
        per_word_topics=True,
    )

    # ─── Print topics ───────────────────────
    print("\n" + "=" * 60)
    print("TOPIC KEYWORDS")
    print("=" * 60)
    for topic_id in range(NUM_TOPICS):
        words = lda_model.show_topic(topic_id, topn=NUM_WORDS)
        kw_str = ", ".join([f"{w}({round(p, 3)})" for w, p in words])
        print(f"  Topic {topic_id:>2}: {kw_str}")

    # ─── Assign dominant topic per claim ────
    def get_dominant_topic(bow):
        topic_dist = lda_model.get_document_topics(bow, minimum_probability=0)
        dominant = max(topic_dist, key=lambda x: x[1])
        return dominant[0], round(dominant[1], 4)

    dominant = [get_dominant_topic(bow) for bow in corpus]
    df_valid["Topic_ID"]          = [d[0] for d in dominant]
    df_valid["Topic_Probability"] = [d[1] for d in dominant]

    # Build readable topic label from top 4 words
    topic_labels = {
        i: "_".join([w for w, _ in lda_model.show_topic(i, topn=4)])
        for i in range(NUM_TOPICS)
    }
    df_valid["Topic_Label"] = df_valid["Topic_ID"].map(topic_labels)

    # ─── Save results ────────────────────────
    results_path = os.path.join(OUTPUT_DIR, "claim_topic_results.xlsx")
    df_valid[["CLM_NUM", "Claim_Notes", "Topic_ID", "Topic_Label", "Topic_Probability"]].to_excel(
        results_path, index=False
    )
    print(f"\nResults saved -> {results_path}")

    # Topic summary with doc counts
    topic_summary = (
        df_valid.groupby(["Topic_ID", "Topic_Label"])
        .size()
        .reset_index(name="Doc_Count")
        .sort_values("Topic_ID")
    )

    # Add keywords column
    topic_summary["Keywords"] = topic_summary["Topic_ID"].apply(
        lambda i: ", ".join([w for w, _ in lda_model.show_topic(i, topn=NUM_WORDS)])
    )

    topic_summary_path = os.path.join(OUTPUT_DIR, "topic_summary.xlsx")
    topic_summary.to_excel(topic_summary_path, index=False)
    print(f"Topic summary saved -> {topic_summary_path}")

    # Print topic distribution
    print("\n" + "=" * 60)
    print("TOPIC DISTRIBUTION")
    print("=" * 60)
    print(topic_summary[["Topic_ID", "Doc_Count", "Topic_Label"]].to_string(index=False))

    print(f"\nModel perplexity : {lda_model.log_perplexity(corpus):.4f}")


if __name__ == "__main__":
    main()