from inventory_sync.database import engine, Base
from inventory_sync import models

def main():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")

if __name__ == "__main__":
    main()
