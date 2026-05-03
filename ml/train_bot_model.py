import os
import pickle

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

RANDOM_SEED = 42
DATASET_PATH = os.path.join(os.path.dirname(__file__), "bot_dataset.csv")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "bot_model.pkl")

FEATURE_COLUMNS = [
    "time_since_event_open_sec",
    "fingerprint_entropy",
    "is_authenticated",
    "requests_per_minute",
    "user_agent_score",
]


def main() -> None:
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(
            f"Dataset not found at {DATASET_PATH}. "
            "Run `python ml/generate_dataset.py` first."
        )

    df = pd.read_csv(DATASET_PATH)
    X = df[FEATURE_COLUMNS]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print("Classification report:")
    print(classification_report(y_test, y_pred, target_names=["human", "bot"]))
    print("Confusion matrix:")
    print(confusion_matrix(y_test, y_pred))

    with open(MODEL_PATH, "wb") as f:
        pickle.dump({"model": model, "features": FEATURE_COLUMNS}, f)

    print(f"Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    main()
