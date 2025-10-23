"""
Migration script to add productloading table for storing product resource requirements.

This table tracks how many generic resources (heads/stations/units) a product needs
on a month-by-month basis, independent of which specific items are allocated.

Run this once: python migrate_add_productloading.py
"""
import sqlite3
import os

# Path to your database
DB_PATH = r'C:\Projects\Python\Fluid\src\db\fluid.db'


def migrate():
    """Add productloading table for product resource requirements."""

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='productloading'
        """)

        if cursor.fetchone():
            print("Table 'productloading' already exists. Skipping creation.")
            return

        # Create productloading table
        print("Creating productloading table...")
        cursor.execute("""
            CREATE TABLE productloading (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fkproduct INTEGER NOT NULL,
                fkitemtype INTEGER NOT NULL,
                monthyear TEXT NOT NULL 
                    CHECK(length(monthyear) = 7 
                          AND substr(monthyear, 5, 1) = '-' 
                          AND CAST(substr(monthyear, 1, 4) AS INTEGER) BETWEEN 2000 AND 2100 
                          AND CAST(substr(monthyear, 6, 2) AS INTEGER) BETWEEN 1 AND 12),
                quantity REAL NOT NULL CHECK(quantity >= 0),
                notes TEXT,
                UNIQUE(fkproduct, fkitemtype, monthyear),
                FOREIGN KEY(fkproduct) REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY(fkitemtype) REFERENCES itemtypes(id) ON DELETE CASCADE ON UPDATE CASCADE
            )
        """)

        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX idx_productloading_product_month 
            ON productloading(fkproduct, monthyear)
        """)

        cursor.execute("""
            CREATE INDEX idx_productloading_type_month 
            ON productloading(fkitemtype, monthyear)
        """)

        conn.commit()
        print("✅ Successfully created productloading table with indexes")

        # Show table structure
        cursor.execute("PRAGMA table_info(productloading)")
        columns = cursor.fetchall()
        print("\nTable structure:")
        for col in columns:
            print(f"  - {col['name']} ({col['type']}){' NOT NULL' if col['notnull'] else ''}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error during migration: {e}")
        raise

    finally:
        conn.close()


if __name__ == '__main__':
    print("=== Product Loading Allocation Migration ===\n")
    migrate()
    print("\n=== Migration Complete ===")