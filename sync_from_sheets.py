import os
import gspread
from google.oauth2.service_account import Credentials
from inventory_sync.database import SessionLocal
from inventory_sync.models import Product
from config import GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEET_ID

# Define the scope for Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_sheets_client():
    """Initialize and return Google Sheets client"""
    creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client

def fetch_sheet_data():
    """Fetch all data from Google Sheets"""
    print("Connecting to Google Sheets...")
    client = get_sheets_client()
    sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
    
    # Get all values from the sheet
    all_data = sheet.get_all_records()
    print(f"Fetched {len(all_data)} rows from Google Sheets.")
    return all_data

def sync_to_database(sheet_data):
    """Sync data from Google Sheets to local database"""
    db = SessionLocal()
    
    try:
        for row in sheet_data:
            # Map Google Sheets columns to database fields
            # Adjust column names to match your actual Google Sheets headers
            product_name = row.get('Product Name', '')
            game = row.get('Game', '')
            set_code = row.get('Set Code', '')
            collector_number = row.get('Collector Number', '')
            condition = row.get('Condition', '')
            finish = row.get('Finish', '')
            
            # Create a composite SKU or use existing SKU column
            # Format: GAME-SETCODE-COLLNUM-CONDITION-FINISH
            if row.get('Shopify Variant ID'):
                sku = str(row.get('Shopify Variant ID'))
            else:
                # Generate SKU from product details
                sku = f"{game}-{set_code}-{collector_number}-{condition}-{finish}".replace(' ', '-')
            
            # Get master price and quantity from Google Sheets
            master_price = float(row.get('Master Price', 0)) if row.get('Master Price') else 0.0
            master_quantity = int(row.get('Master Quantity', 0)) if row.get('Master Quantity') else 0
            
            # Create full product name with details
            name = f"{product_name} ({game} - {set_code} #{collector_number} - {condition} - {finish})"
            
            # Skip if no price or quantity (empty row)
            if not master_price and not master_quantity:
                continue
            
            # Check if product exists in database
            db_product = db.query(Product).filter(Product.sku == sku).first()
            
            if db_product:
                # Update existing product
                db_product.name = name
                db_product.price = master_price
                db_product.quantity = master_quantity
                print(f"Updated: {sku} - {name}")
            else:
                # Create new product
                db_product = Product(
                    sku=sku,
                    name=name,
                    price=master_price,
                    quantity=master_quantity
                )
                db.add(db_product)
                print(f"Created: {sku} - {name}")
        
        db.commit()
        print("✅ Successfully synced Google Sheets to database.")
        
    except Exception as e:
        print(f"❌ Error syncing to database: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    print("Starting Google Sheets to Database sync...")
    sheet_data = fetch_sheet_data()
    sync_to_database(sheet_data)
    print("✅ Sync complete!")

if __name__ == "__main__":
    main()
