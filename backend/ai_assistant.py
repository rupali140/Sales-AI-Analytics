
def generate_sales_insights(sales):
    """Generate rule-based business insights from monthly sales data."""

    if not sales:
        return {
            "status": "no_data",
            "summary": "No sales data available. Import sales data first.",
            "insights": [],
            "recommendations": [],
        }

    sales = sorted(
        sales,
        key=lambda item: [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
        ].index(item["month"])
    )

    total_revenue = sum(float(s["revenue"]) for s in sales)
    total_profit = sum(float(s["profit"]) for s in sales)
    total_orders = sum(int(s["orders"]) for s in sales)

    best_revenue_month = max(sales, key=lambda s: float(s["revenue"]))
    best_profit_month = max(sales, key=lambda s: float(s["profit"]))

    insights = []
    recommendations = []

    insights.append(
        f"Total revenue is {total_revenue:,.2f} across {len(sales)} recorded months."
    )

    insights.append(
        f"{best_revenue_month['month']} has the highest revenue "
        f"({float(best_revenue_month['revenue']):,.2f})."
    )

    insights.append(
        f"{best_profit_month['month']} has the highest profit "
        f"({float(best_profit_month['profit']):,.2f})."
    )

    if total_revenue > 0:
        profit_margin = (total_profit / total_revenue) * 100
        insights.append(f"Overall profit margin is {profit_margin:.2f}%.")

        if profit_margin < 10:
            recommendations.append(
                "Profit margin is below 10%. Review operating costs and pricing."
            )
        elif profit_margin < 20:
            recommendations.append(
                "Look for ways to improve profit margin through cost control."
            )
        else:
            recommendations.append(
                "Maintain profitability while monitoring costs and revenue."
            )

    if len(sales) >= 2:
        previous_revenue = float(sales[-2]["revenue"])
        latest_revenue = float(sales[-1]["revenue"])

        if previous_revenue > 0:
            change = (
                (latest_revenue - previous_revenue)
                / previous_revenue
            ) * 100

            if change > 0:
                insights.append(
                    f"Revenue increased by {change:.2f}% from "
                    f"{sales[-2]['month']} to {sales[-1]['month']}."
                )
                recommendations.append(
                    "Review what worked in the latest month and repeat successful actions."
                )
            elif change < 0:
                insights.append(
                    f"Revenue decreased by {abs(change):.2f}% from "
                    f"{sales[-2]['month']} to {sales[-1]['month']}."
                )
                recommendations.append(
                    "Investigate the revenue decline and review orders, pricing, and sales activity."
                )
            else:
                insights.append("Revenue remained unchanged between the latest two months.")
        else:
            insights.append(
                "Previous month's revenue was zero, so percentage change cannot be calculated."
            )

    if total_orders > 0:
        average_order_value = total_revenue / total_orders
        insights.append(f"Average revenue per order is {average_order_value:,.2f}.")
    else:
        recommendations.append(
            "No orders are recorded. Verify the order data before evaluating sales performance."
        )

    if not recommendations:
        recommendations.append(
            "Continue tracking monthly revenue, profit, and orders to identify trends."
        )

    return {
        "status": "success",
        "summary": f"Analyzed {len(sales)} months of sales data.",
        "total_revenue": round(total_revenue, 2),
        "total_profit": round(total_profit, 2),
        "total_orders": total_orders,
        "best_revenue_month": best_revenue_month["month"],
        "best_profit_month": best_profit_month["month"],
        "insights": insights,
        "recommendations": recommendations,
        "method": "Rule-based Sales Analysis",
        "note": "These insights are generated from the available data, not from a generative AI model.",
    }
