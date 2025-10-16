"""
Migration script to add fkproduct column to itemloading table
and create UNALLOCATED product for existing data.

Run this once: python migrate_itemloading_add_product.py
"""
import sqlite3
import os

# Path to your database

DB_PATH = r'C:\Projects\Python\Fluid\src\db\fluid.db'

def migrate():
    """Add fkproduct column and migrate existing data to UNALLOCATED product."""

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Step 1: Check if PRODUCT item type exists, create if not
        cursor.execute('SELECT id FROM itemtypes WHERE typename = ?', ('PRODUCT',))
        product_type = cursor.fetchone()

        if not product_type:
            print("Creating PRODUCT item type...")
            cursor.execute('INSERT INTO itemtypes (typename) VALUES (?)', ('PRODUCT',))
            product_type_id = cursor.lastrowid
        else:
            product_type_id = product_type['id']
            print(f"PRODUCT item type already exists with ID: {product_type_id}")

        # Step 2: Check if UNALLOCATED product exists, create if not
        cursor.execute('''
            SELECT id FROM items 
            WHERE itemname = ? AND fkitemtype = ?
        ''', ('UNALLOCATED', product_type_id))
        unallocated_product = cursor.fetchone()

        if not unallocated_product:
            print("Creating UNALLOCATED product item...")
            cursor.execute('''
                INSERT INTO items (itemname, fkitemtype) 
                VALUES (?, ?)
            ''', ('UNALLOCATED', product_type_id))
            unallocated_id = cursor.lastrowid
            print(f"Created UNALLOCATED product with ID: {unallocated_id}")
        else:
            unallocated_id = unallocated_product['id']
            print(f"UNALLOCATED product already exists with ID: {unallocated_id}")

        # Step 3: Check if fkproduct column already exists
        cursor.execute('PRAGMA table_info(itemloading)')
        columns = [col['name'] for col in cursor.fetchall()]

        if 'fkproduct' in columns:
            print("Column fkproduct already exists in itemloading table.")
        else:
            print("Adding fkproduct column to itemloading table...")

            # SQLite doesn't support ALTER TABLE ADD COLUMN with FOREIGN KEY directly
            # So we need to recreate the table

            # Step 3a: Create new table with fkproduct column
            cursor.execute('''
                CREATE TABLE itemloading_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fkitem INTEGER NOT NULL,
                    dailyrollupexists INTEGER NOT NULL CHECK(dailyrollupexists IN (0, 1)),
                    monthyear TEXT NOT NULL CHECK(
                        length(monthyear) = 7 AND substr(monthyear, 5, 1) = '-' AND
                        CAST(substr(monthyear, 1, 4) AS INTEGER) BETWEEN 2000 AND 2100 AND
                        CAST(substr(monthyear, 6, 2) AS INTEGER) BETWEEN 1 AND 12
                    ),
                    percent REAL NOT NULL CHECK(percent BETWEEN 0 AND 100),
                    fkproduct INTEGER NOT NULL,
                    FOREIGN KEY(fkitem) REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE,
                    FOREIGN KEY(fkproduct) REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
                )
            ''')

            # Step 3b: Copy existing data, setting fkproduct to UNALLOCATED
            print(f"Migrating existing itemloading data to UNALLOCATED (ID: {unallocated_id})...")
            cursor.execute(f'''
                INSERT INTO itemloading_new (id, fkitem, dailyrollupexists, monthyear, percent, fkproduct)
                SELECT id, fkitem, dailyrollupexists, monthyear, percent, {unallocated_id}
                FROM itemloading
            ''')

            rows_migrated = cursor.rowcount
            print(f"Migrated {rows_migrated} rows to new structure.")

            # Step 3c: Drop old table and rename new one
            cursor.execute('DROP TABLE itemloading')
            cursor.execute('ALTER TABLE itemloading_new RENAME TO itemloading')

            # Step 3d: Recreate indexes
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_itemloading_fkitem 
                ON itemloading (fkitem)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_itemloading_fkproduct 
                ON itemloading (fkproduct)
            ''')

            print("Successfully added fkproduct column and recreated indexes.")

        # Step 4: Verify the migration
        cursor.execute('SELECT COUNT(*) as count FROM itemloading WHERE fkproduct = ?', (unallocated_id,))
        unallocated_count = cursor.fetchone()['count']
        print(f"\nVerification: {unallocated_count} rows are allocated to UNALLOCATED product.")

        # Commit all changes
        conn.commit()
        print("\n✅ Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    print("=" * 60)
    print("ITEMLOADING MIGRATION: Adding fkproduct column")
    print("=" * 60)
    print()

    # Confirm before proceeding
    response = input("This will modify your database. Backup recommended. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled.")
        exit(0)

    migrate()