import os
import requests
from inventory_sync.database import SessionLocal
from inventory_sync.models import Product
from dotenv import load_dotenv

load_dotenv()

SHOPIFY_DOMAIN = os.getenv("SHOPIFY_STORE_DOMAIN")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2023-07")

def fetch_shopify_inventory():
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/{SHOPIFY_API_VERSION}/products.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json"
    }
    products = []
    page_info = None
    while True:
        params = {}
        if page_info:
            params["page_info"] = page_info
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        result = response.json().get("products", [])
        if not result:
            break
        products.extend(result)
        # Shopify now paginates with link headers; check for 'rel="next"'
        link_header = response.headers.get("Link")
        if link_header and 'rel="next"' in link_header:
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    page_info = part.split(";")[0].split("page_info=")[-1].strip(" <>")
                    break
        else:
            break
    return products

def save_products_to_db(products):
    db = SessionLocal()
    for item in products:
        sku = item['variants'][0]['sku']
        name = item['title']
        price = float(item['variants'][0]['price'])
        quantity = int(item['variants'][0]['inventory_quantity'])
        # Upsert logic (update if exists, create if not)
        db_product = db.query(Product).filter(Product.sku == sku).first()
        if db_product:
            db_product.name = name
            db_product.price = price
            db_product.quantity = quantity
        else:
            db_product = Product(sku=sku, name=name, price=price, quantity=quantity)
            db.add(db_product)
    db.commit()
    db.close()

def main():
    print("Fetching inventory from Shopify...")
    products = fetch_shopify_inventory()
    print(f"Fetched {len(products)} products.")
    save_products_to_db(products)
    print("✅ Shopify inventory saved to database.")

if __name__ == "__main__":
    main()
