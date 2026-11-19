import os
import pandas as pd
from sqlalchemy import create_engine

# ==========================================
# CONFIGURATION
# ==========================================
# Replace 'your_root_password_here' with your actual MySQL root password
DB_USER = "root"
DB_PASSWORD = "133113"  # <--- UPDATE THIS
DB_HOST = "localhost"
DB_PORT = "3306"
DB_NAME = "olist_analytics_warehouse"

# Create SQLAlchemy connection engine
connection_string = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(connection_string)

DIRTY_DIR = "./dirty_data"

print("🚀 Starting Staging Ingestion into MySQL...")

# Map your CSV files to their target staging table names in MySQL
staging_files = {
    "stg_orders.csv": "stg_orders",
    "stg_order_items.csv": "stg_order_items",
    "stg_order_payments.csv": "stg_order_payments",
    "stg_customers.csv": "stg_customers",
    "stg_order_reviews.csv": "stg_order_reviews",
    "stg_products.csv": "stg_products",
    "stg_sellers.csv": "stg_sellers",
    "stg_category_translation.csv": "stg_category_translation",
    "fact_category_budget.csv": "stg_category_budget"
}

for filename, table_name in staging_files.items():
    file_path = os.path.join(DIRTY_DIR, filename)
    
    if os.path.exists(file_path):
        print(f"📥 Loading {filename} into MySQL table `{table_name}`...")
        df = pd.read_csv(file_path)
        
        # Write dataframe to MySQL (replaces table if it already exists, chunked for performance)
        df.to_sql(table_name, con=engine, if_exists='replace', index=False, chunksize=10000)
        print(f"✅ Successfully loaded {len(df):,} rows into `{table_name}`.")
    else:
        print(f"❌ Warning: {file_path} not found!")

print("\n🎉 Staging Layer Complete! All raw data is now safely stored in MySQL.")