
import numpy as np


def predict_next_revenue(sales):
    """Estimate next revenue using a linear trend."""

    if len(sales) < 2:
        raise ValueError(
            "At least two months of sales data are required."
        )

    revenues = []

    for sale in sales:
        revenue = float(sale["revenue"])

        if not np.isfinite(revenue) or revenue < 0:
            raise ValueError(
                "Revenue must be a valid non-negative number."
            )

        revenues.append(revenue)

    x_values = np.arange(len(revenues), dtype=float)
    y_values = np.array(revenues, dtype=float)

    slope, intercept = np.polyfit(
        x_values,
        y_values,
        1,
    )

    prediction = slope * len(revenues) + intercept

    return {
        "predicted_revenue": round(max(0.0, float(prediction)), 2),
        "average_revenue": round(float(np.mean(y_values)), 2),
        "monthly_trend": round(float(slope), 2),
        "months_used": len(revenues),
        "method": "NumPy Linear Regression",
        "note": "Trend-based estimate, not a guarantee of future sales.",
    }
