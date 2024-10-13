import sys
import streamlit as st
import altair as alt
import matplotlib.pyplot as plt
sys.path.append("src")
from main import query_data
import pandas as pd

# Set up Streamlit
st.title("Sales and Revenue Report")


# 1. Average User Transaction Amount for the Last 6 Months
def plot_avg_user_transaction():
    query = """
    select
        DATE_TRUNC('month',
        date_utc) as month,
        AVG(total) as avg_transaction
    from
        fct_transaction ft
    where
        date_utc >= NOW() - interval '6 months'
    group by
        month
    order by
        month desc 
    limit 6;
    """
    avg_transaction_df = query_data(query)

    # Plotting with Altair
    chart = alt.Chart(avg_transaction_df).mark_line(point=True).encode(
        x='month:T',
        y='avg_transaction:Q'
    ).properties(
        title='Average User Transaction Amount (Last 6 Months)'
    )
    st.altair_chart(chart, use_container_width=True)


# 2. Product Category with the Highest Total Sales
def plot_highest_sales_category():
    query = """
    select dp.product
        , sum(ft.total) as total_sales
    from fct_transaction ft 
        inner join dim_product dp 
            on ft.subscription_id = dp.subscription_id
    group by 1
    order by 2 desc 
    limit 1;
    """
    highest_sales_df = query_data(query)

    # Display the result
    highest_product = highest_sales_df['product'][0]
    total_sales = highest_sales_df['total_sales'][0]
    st.metric(label="Product Category with the Highest Total Sales", value=highest_product,
              delta=f"${total_sales:,.2f}")


# 3. Monthly Revenue Growth for the Last 6 Months
def plot_monthly_revenue_growth():
    query = """
    WITH monthly_revenue AS (
            SELECT 
                DATE_TRUNC('month', date_utc) AS month,
                SUM(total) AS monthly_revenue
            FROM 
                fct_transaction
            WHERE 
                date_utc >= NOW() - INTERVAL '6 months'
            GROUP BY 
                month
            ORDER BY 
                month
        ),
    result as (
        SELECT
            month,
            monthly_revenue,
            LAG(monthly_revenue) OVER (ORDER BY month) AS prev_month_revenue,
            CASE
                WHEN LAG(monthly_revenue) OVER (ORDER BY month) IS NOT NULL
                THEN ((monthly_revenue - LAG(monthly_revenue) OVER (ORDER BY month))
                        / LAG(monthly_revenue) OVER (ORDER BY month)) * 100
                ELSE 0
            END AS revenue_growth
        FROM
            monthly_revenue)
    SELECT * FROM result
    WHERE prev_month_revenue IS NOT NULL;
    """
    revenue_growth_df = query_data(query)

    # Ensure 'month' is a datetime column if needed
    if not pd.api.types.is_datetime64_any_dtype(revenue_growth_df['month']):
        revenue_growth_df['month'] = pd.to_datetime(revenue_growth_df['month'])

    # Convert the revenue growth to a percentage for better readability
    revenue_growth_df['revenue_growth'] = revenue_growth_df['revenue_growth'].round(2)

    # Define colors: green for growth, red for drop
    colors = ['green' if x >= 0 else 'red' for x in revenue_growth_df['revenue_growth']]

    # Plotting with Matplotlib
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(revenue_growth_df['month'].dt.strftime('%Y-%m'), revenue_growth_df['revenue_growth'], color=colors)

    # Formatting the plot
    ax.set_xlabel('Month', fontsize=12)
    ax.set_ylabel('Revenue Growth (%)', fontsize=12)
    ax.set_title('Monthly Revenue Growth (Last 6 Months)', fontsize=14)

    # Rotate x-axis labels for better readability
    ax.set_xticklabels(revenue_growth_df['month'].dt.strftime('%Y-%m'), rotation=45, ha='right')

    # Add grid for better visibility
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)

    # Display the plot in Streamlit
    st.pyplot(fig)


if __name__ == '__main__':
    # Display the results
    st.header("1. Average User Transaction Amount (Last 6 Months)")
    plot_avg_user_transaction()

    st.header("2. Product Category with the Highest Total Sales")
    plot_highest_sales_category()

    st.header("3. Monthly Revenue Growth (Last 6 Months)")
    plot_monthly_revenue_growth()