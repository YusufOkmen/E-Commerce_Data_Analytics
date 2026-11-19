import os
import pandas as pd
import numpy as np

# Set random seed so your results are 100% reproducible
np.random.seed(42)

RAW_DIR = "./raw_data"
DIRTY_DIR = "./dirty_data"

print("🚀 Starting Phase 1: Inspecting Raw Data & Generating Company Simulation...")

# 1. Load the core tables we need to manipulate
orders = pd.read_csv(f"{RAW_DIR}/olist_orders_dataset.csv")
items = pd.read_csv(f"{RAW_DIR}/olist_order_items_dataset.csv")
payments = pd.read_csv(f"{RAW_DIR}/olist_order_payments_dataset.csv")
products = pd.read_csv(f"{RAW_DIR}/olist_products_dataset.csv")
translations = pd.read_csv(f"{RAW_DIR}/product_category_name_translation.csv")

print(f"✅ Loaded Orders: {len(orders):,} rows")
print(f"✅ Loaded Order Items: {len(items):,} rows")
print(f"✅ Loaded Payments: {len(payments):,} rows")

# ==============================================================================
# PART A: GENERATE MONTHLY CATEGORY BUDGETS (For Power BI 'Budget vs. Actuals')
# ==============================================================================
print("\n📊 Generating Monthly Category Budgets...")

# Merge items with orders (for dates) and products + translations (for English category names)
merged = items.merge(orders[['order_id', 'order_purchase_timestamp']], on='order_id', how='left')
merged = merged.merge(products[['product_id', 'product_category_name']], on='product_id', how='left')
merged = merged.merge(translations, on='product_category_name', how='left')

merged[' product_category_name_english'] = merged['product_category_name_english'].fillna('uncategorized')
merged['month_start_date'] = pd.to_datetime(merged['order_purchase_timestamp']).dt.to_period('M').dt.to_timestamp()

# Calculate actual monthly revenue per category
monthly_actuals = (
    merged.groupby(['month_start_date', 'product_category_name_english'])['price']
    .sum()
    .reset_index()
    .rename(columns={'product_category_name_english': 'category_name', 'price': 'actual_revenue'})
)

# Simulate realistic corporate budgets (Actuals multiplied by a random factor between 0.85 and 1.20)
random_multipliers = np.random.uniform(0.85, 1.20, size=len(monthly_actuals))
monthly_actuals['budget_amount'] = (monthly_actuals['actual_revenue'] * random_multipliers).round(2)

budgets_df = monthly_actuals[['month_start_date', 'category_name', 'budget_amount']]
budgets_df.to_csv(f"{DIRTY_DIR}/fact_category_budget.csv", index=False)
print(f"✅ Created fact_category_budget.csv ({len(budgets_df):,} rows)")

# ==============================================================================
# PART B: INJECT REALISTIC PRODUCTION BUGS (For SQL ETL Cleaning)
# ==============================================================================
print("\n🛠️ Injecting realistic production bugs into staging files...")

# BUG 1: Duplicate 500 rows in Orders (Simulating webhook double-firing)
duplicate_orders = orders.sample(n=500, random_state=42)
dirty_orders = pd.concat([orders, duplicate_orders], ignore_index=True)
dirty_orders.to_csv(f"{DIRTY_DIR}/stg_orders.csv", index=False)
print(f"⚠️ stg_orders.csv saved with 500 duplicate rows (Total: {len(dirty_orders):,})")

# BUG 2: Locale comma bug in 2% of Order Items prices (e.g., '190.40' -> '190,40')
dirty_items = items.copy()
dirty_items['price'] = dirty_items['price'].astype(str)
corrupt_indices = dirty_items.sample(frac=0.02, random_state=42).index
dirty_items.loc[corrupt_indices, 'price'] = dirty_items.loc[corrupt_indices, 'price'].str.replace('.', ',', regex=False)
dirty_items.to_csv(f"{DIRTY_DIR}/stg_order_items.csv", index=False)
print(f"⚠️ stg_order_items.csv saved with {len(corrupt_indices):,} comma-formatted price strings")

# BUG 3: Payment gateway discrepancies (3% underpaid/overpaid) + 100 Orphan Payments
dirty_payments = payments.copy()
mismatch_indices = dirty_payments.sample(frac=0.03, random_state=42).index
dirty_payments.loc[mismatch_indices, 'payment_value'] = (
    dirty_payments.loc[mismatch_indices, 'payment_value'] * np.random.uniform(0.5, 0.9, size=len(mismatch_indices))
).round(2)

# Create 100 orphan payments (payments where the order_id doesn't exist in the orders table)
orphan_payments = dirty_payments.sample(n=100, random_state=99).copy()
orphan_payments['order_id'] = [f"orphan_order_{i}" for i in range(100)]
dirty_payments = pd.concat([dirty_payments, orphan_payments], ignore_index=True)
dirty_payments.to_csv(f"{DIRTY_DIR}/stg_order_payments.csv", index=False)
print(f"⚠️ stg_order_payments.csv saved with {len(mismatch_indices):,} value mismatches and 100 orphan records")

# Copy the remaining untouched tables directly to dirty_data as staging files
untouched_files = {
    "olist_customers_dataset.csv": "stg_customers.csv",
    "olist_order_reviews_dataset.csv": "stg_order_reviews.csv",
    "olist_products_dataset.csv": "stg_products.csv",
    "olist_sellers_dataset.csv": "stg_sellers.csv",
    "product_category_name_translation.csv": "stg_category_translation.csv"
}

for src, dest in untouched_files.items():
    df_temp = pd.read_csv(f"{RAW_DIR}/{src}")
    df_temp.to_csv(f"{DIRTY_DIR}/{dest}", index=False)
    print(f"✅ Copied {src} -> {dest}")

print("\n🎉 Phase 1 Complete! All staging files are ready in ./dirty_data/")