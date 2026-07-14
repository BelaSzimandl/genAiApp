from __future__ import annotations

from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def save_chart(aggregation: pd.DataFrame, output_dir: str | Path, chart_type: str = "bar") -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = output_path / f"chart_{timestamp}.png"

    fig, ax = plt.subplots(figsize=(10, 5))

    if "bucket" in aggregation.columns and "count" in aggregation.columns:
        x = aggregation["bucket"].astype(str)
        y = aggregation["count"]
        title = "Log Trend Over Time"
        xlabel = "Time Bucket"
    elif "log_level" in aggregation.columns and "count" in aggregation.columns:
        x = aggregation["log_level"]
        y = aggregation["count"]
        title = "Logs by Level"
        xlabel = "Log Level"
    elif "component" in aggregation.columns:
        count_col = "count" if "count" in aggregation.columns else "error_rate"
        x = aggregation["component"]
        y = aggregation[count_col]
        title = "Logs by Component" if count_col == "count" else "Error Rate by Component"
        xlabel = "Component"
    else:
        raise ValueError("Unsupported aggregation format for charting.")

    if chart_type == "line":
        ax.plot(range(len(x)), y, marker="o")
        ax.set_xticks(range(len(x)))
        ax.set_xticklabels(x, rotation=45, ha="right")
    else:
        ax.bar(range(len(x)), y)
        ax.set_xticks(range(len(x)))
        ax.set_xticklabels(x, rotation=45, ha="right")

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Count" if "error_rate" not in aggregation.columns else "Error Rate (%)")
    fig.tight_layout()
    fig.savefig(file_path, dpi=120)
    plt.close(fig)

    return file_path