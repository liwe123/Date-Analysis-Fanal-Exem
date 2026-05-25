import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd


def file_size_mb(path: Path) -> float:
    return path.stat().st_size / (1024 * 1024)


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "artifacts"
    data_dir.mkdir(parents=True, exist_ok=True)

    num_rows = 1_000_000

    t0 = time.perf_counter()
    df = pd.DataFrame(
        {
            "transaction_id": range(num_rows),
            "user_name": [f"User_Number_{i}" for i in range(num_rows)],
            "category": np.random.choice(
                ["Electronics", "Books", "Clothing", "Home"], num_rows
            ),
            "price": np.random.uniform(10.0, 500.0, num_rows),
            "timestamp": pd.date_range(start="2024-01-01", periods=num_rows, freq="s"),
        }
    )
    build_time_sec = time.perf_counter() - t0

    memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)

    csv_path = data_dir / "data.csv"
    json_path = data_dir / "data.json"
    parquet_path = data_dir / "data.parquet"

    t0 = time.perf_counter()
    df.to_csv(csv_path, index=False)
    csv_write_sec = time.perf_counter() - t0

    t0 = time.perf_counter()
    df.to_json(json_path, orient="records", lines=True)
    json_write_sec = time.perf_counter() - t0

    t0 = time.perf_counter()
    df.to_parquet(parquet_path, engine="pyarrow", compression="snappy")
    parquet_write_sec = time.perf_counter() - t0

    csv_mb = file_size_mb(csv_path)
    json_mb = file_size_mb(json_path)
    parquet_mb = file_size_mb(parquet_path)

    parquet_vs_json_reduce_pct = (1 - parquet_mb / json_mb) * 100
    parquet_vs_csv_reduce_pct = (1 - parquet_mb / csv_mb) * 100

    t0 = time.perf_counter()
    df_csv = pd.read_csv(csv_path)
    csv_read_sec = time.perf_counter() - t0
    csv_mean_price = float(df_csv["price"].mean())

    t0 = time.perf_counter()
    df_parquet = pd.read_parquet(parquet_path, columns=["price"])
    parquet_read_sec = time.perf_counter() - t0
    parquet_mean_price = float(df_parquet["price"].mean())

    speedup_ratio = csv_read_sec / parquet_read_sec if parquet_read_sec > 0 else None

    broken_error = None
    broken_df = pd.DataFrame(
        [
            {
                "transaction_id": 1_000_001,
                "user_name": "Broken_User",
                "category": "Electronics",
                "price": "Expensive",
                "timestamp": pd.Timestamp("2024-12-31"),
            }
        ]
    )
    try:
        broken_df["price"] = broken_df["price"].astype(float)
    except Exception as exc:  # noqa: BLE001
        broken_error = str(exc)

    metrics = {
        "rows": num_rows,
        "build_time_sec": build_time_sec,
        "memory_mb": memory_mb,
        "write_time_sec": {
            "csv": csv_write_sec,
            "json": json_write_sec,
            "parquet": parquet_write_sec,
        },
        "file_size_mb": {"csv": csv_mb, "json": json_mb, "parquet": parquet_mb},
        "reduction_pct": {
            "parquet_vs_json": parquet_vs_json_reduce_pct,
            "parquet_vs_csv": parquet_vs_csv_reduce_pct,
        },
        "mean_price": {"csv": csv_mean_price, "parquet": parquet_mean_price},
        "read_time_sec": {"csv": csv_read_sec, "parquet_price_only": parquet_read_sec},
        "speedup_ratio_csv_over_parquet": speedup_ratio,
        "broken_data_error": broken_error,
    }

    metrics_path = base_dir / "metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    summary_lines = [
        f"Rows: {num_rows}",
        f"DataFrame memory (MB): {memory_mb:.2f}",
        f"File size MB - CSV: {csv_mb:.2f}, JSON: {json_mb:.2f}, Parquet: {parquet_mb:.2f}",
        "Reduction % (formula 1 - Parquet/JSON): "
        f"{parquet_vs_json_reduce_pct:.2f}%",
        f"Reduction % (1 - Parquet/CSV): {parquet_vs_csv_reduce_pct:.2f}%",
        f"Read time sec - CSV: {csv_read_sec:.4f}, Parquet(price-only): {parquet_read_sec:.4f}",
        f"Read speedup (CSV/Parquet): {speedup_ratio:.2f}x",
        f"Mean price CSV: {csv_mean_price:.6f}",
        f"Mean price Parquet: {parquet_mean_price:.6f}",
        f"Broken data protection error: {broken_error}",
    ]
    (base_dir / "summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")

    print("\n".join(summary_lines))


if __name__ == "__main__":
    main()
