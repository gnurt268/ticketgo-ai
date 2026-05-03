import os
import random

import numpy as np
import pandas as pd

RANDOM_SEED = 42
NUM_RECORDS = 2000
BOT_RATIO = 0.3
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "bot_dataset.csv")


def generate_dataset(n: int = NUM_RECORDS, bot_ratio: float = BOT_RATIO) -> pd.DataFrame:
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    records = []
    for _ in range(n):
        is_bot = random.random() < bot_ratio
        if is_bot:
            record = {
                "time_since_event_open_sec": np.random.uniform(0, 2),
                "fingerprint_entropy": np.random.uniform(0, 1.5),
                "is_authenticated": 0 if random.random() < 0.9 else 1,
                "requests_per_minute": np.random.uniform(50, 200),
                "user_agent_score": np.random.uniform(0, 2.5),
                "label": 1,
            }
        else:
            record = {
                "time_since_event_open_sec": np.random.uniform(1, 300),
                "fingerprint_entropy": np.random.uniform(3, 8),
                "is_authenticated": random.randint(0, 1),
                "requests_per_minute": np.random.uniform(1, 20),
                "user_agent_score": np.random.uniform(5, 10),
                "label": 0,
            }
        records.append(record)

    return pd.DataFrame(records)


def main() -> None:
    df = generate_dataset()
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Dataset saved to {OUTPUT_PATH}")
    print(f"Total records: {len(df)}")
    print(f"Bot records: {int(df['label'].sum())}")
    print(f"Human records: {int((df['label'] == 0).sum())}")


if __name__ == "__main__":
    main()
