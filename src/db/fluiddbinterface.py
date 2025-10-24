import sqlite3
from typing import Optional, Dict, Any, Iterable, Tuple, List


class VerificationDB:
    """
    SQLite helper matching fluid.db.sql schema with product support.

    Tables:
      - itemtypes: id (PK), typename (UNIQUE)
      - items: id (PK), itemname, fkitemtype
      - itemcharacteristics: id (PK), fkitem, itemkey, itemvalue, itemkeyvaluetype
      - itemloading: id (PK), fkitem, dailyrollupexists, monthyear, percent, fkproduct (nullable)
      - item_product_map: fkitem, fkproduct (composite PK)
      - productloading: id (PK), fkproduct, fkitemtype, monthyear, percent, notes
    """

    def __init__(self, path: str):
        self.path = path
        self.con: Optional[sqlite3.Connection] = None

    # ---------- Connection & context management ----------

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.con is not None:
            if exc_type is None:
                self.con.commit()
            else:
                self.con.rollback()
        self.close()

    def connect(self):
        if self.con is None:
            self.con = sqlite3.connect(self.path)
            self.con.row_factory = sqlite3.Row
            self.con.execute("PRAGMA foreign_keys = ON;")

    def close(self):
        if self.con is not None:
            self.con.close()
            self.con = None

    # ---------- Helpers ----------

    def _execute(self, sql: str, params: Tuple[Any, ...] = ()) -> sqlite3.Cursor:
        if self.con is None:
            self.connect()
        return self.con.execute(sql, params)

    def _update_set_clause(self, data: Dict[str, Any]) -> Tuple[str, Tuple[Any, ...]]:
        """Build a 'SET col1=?, col2=?' clause from a dict, skipping None values."""
        cols, vals = [], []
        for k, v in data.items():
            if v is not None:
                cols.append(f'"{k}" = ?')
                vals.append(v)
        if not cols:
            raise ValueError("No fields to update.")
        return ", ".join(cols), tuple(vals)

    def _indices_by_fields(
            self,
            table: str,
            id_col: str,
            filters: Dict[str, Any],
    ) -> List[int]:
        """Generic: return list of ids for rows in table that match non-None filters."""
        where_parts, params = [], []
        for col, val in filters.items():
            if val is not None:
                where_parts.append(f'"{col}" = ?')
                params.append(val)
        if not where_parts:
            raise ValueError("At least one filter must be provided.")
        where_sql = " AND ".join(where_parts)
        cur = self._execute(
            f'SELECT "{id_col}" AS idx FROM "{table}" WHERE {where_sql};',
            tuple(params),
        )
        return [int(r["idx"]) for r in cur.fetchall()]

    # ====================================================
    # itemtypes
    # ====================================================

    def add_itemtype(self, typename: str) -> int:
        """Insert a new item type. Returns new row id."""
        cur = self._execute('INSERT INTO "itemtypes" ("typename") VALUES (?);', (typename,))
        return cur.lastrowid

    def update_itemtype(self, id: int, typename: Optional[str] = None) -> None:
        """Update itemtype by id."""
        set_clause, params = self._update_set_clause({"typename": typename})
        self._execute(f'UPDATE "itemtypes" SET {set_clause} WHERE "id" = ?;', params + (id,))

    def delete_itemtype(self, id: int) -> None:
        """Delete itemtype by id."""
        self._execute('DELETE FROM "itemtypes" WHERE "id" = ?;', (id,))

    def get_itemtype_id_by_typename(self, typename: str) -> Optional[int]:
        """Return the id for an itemtype by typename."""
        ids = self._indices_by_fields("itemtypes", "id", {"typename": typename})
        return ids[0] if ids else None

    def get_itemtype_by_id(self, id: int) -> Optional[sqlite3.Row]:
        """Get itemtype row by id."""
        cur = self._execute('SELECT * FROM "itemtypes" WHERE "id" = ?;', (id,))
        return cur.fetchone()

    # ====================================================
    # items
    # ====================================================

    def add_item(self, itemname: str, fkitemtype: int) -> int:
        """Insert item. Returns auto-generated id."""
        cur = self._execute(
            'INSERT INTO "items" ("itemname","fkitemtype") VALUES (?,?);',
            (itemname, fkitemtype),
        )
        return cur.lastrowid

    def update_item(
            self,
            id: int,
            itemname: Optional[str] = None,
            fkitemtype: Optional[int] = None,
    ) -> None:
        """Update item by id."""
        set_clause, params = self._update_set_clause(
            {"itemname": itemname, "fkitemtype": fkitemtype}
        )
        self._execute(f'UPDATE "items" SET {set_clause} WHERE "id" = ?;', params + (id,))

    def delete_item(self, id: int) -> None:
        """Delete item by id."""
        self._execute('DELETE FROM "items" WHERE "id" = ?;', (id,))

    def get_item_by_id(self, id: int) -> Optional[sqlite3.Row]:
        """Get item by id."""
        cur = self._execute('SELECT * FROM "items" WHERE "id" = ?;', (id,))
        return cur.fetchone()

    def get_item_by_name(self, itemname: str) -> Optional[sqlite3.Row]:
        """Get item by name."""
        cur = self._execute('SELECT * FROM "items" WHERE "itemname" = ?;', (itemname,))
        return cur.fetchone()

    def get_item_id_by_name(self, itemname: str) -> Optional[int]:
        """Return items.id for a given itemname."""
        ids = self._indices_by_fields("items", "id", {"itemname": itemname})
        return ids[0] if ids else None

    # ====================================================
    # itemcharacteristics
    # ====================================================

    def add_characteristic(
            self,
            fkitem: int,
            itemkey: str,
            itemvalue: str,
            itemkeyvaluetype: Optional[str] = None,
    ) -> int:
        """Insert characteristic. Returns auto-generated id."""
        cur = self._execute(
            'INSERT INTO "itemcharacteristics" ("fkitem","itemkey","itemvalue","itemkeyvaluetype") '
            'VALUES (?,?,?,?);',
            (fkitem, itemkey, itemvalue, itemkeyvaluetype),
        )
        return cur.lastrowid

    def update_itemcharacteristic(
            self,
            id: int,
            fkitem: Optional[int] = None,
            itemkey: Optional[str] = None,
            itemvalue: Optional[str] = None,
            itemkeyvaluetype: Optional[str] = None,
    ) -> None:
        """Update itemcharacteristic by id."""
        set_clause, params = self._update_set_clause(
            {
                "fkitem": fkitem,
                "itemkey": itemkey,
                "itemvalue": itemvalue,
                "itemkeyvaluetype": itemkeyvaluetype,
            }
        )
        self._execute(
            f'UPDATE "itemcharacteristics" SET {set_clause} WHERE "id" = ?;',
            params + (id,),
        )

    def delete_itemcharacteristic(self, id: int) -> None:
        """Delete itemcharacteristic by id."""
        self._execute('DELETE FROM "itemcharacteristics" WHERE "id" = ?;', (id,))

    def get_itemcharacteristic_by_id(self, id: int) -> Optional[sqlite3.Row]:
        """Get itemcharacteristic by id."""
        cur = self._execute('SELECT * FROM "itemcharacteristics" WHERE "id" = ?;', (id,))
        return cur.fetchone()

    def find_itemcharacteristics_ids(
            self,
            fkitem: Optional[int] = None,
            itemkey: Optional[str] = None,
            itemvalue: Optional[str] = None,
            itemkeyvaluetype: Optional[str] = None,
    ) -> List[int]:
        """Return list of itemcharacteristics.id values matching filters."""
        return self._indices_by_fields(
            "itemcharacteristics",
            "id",
            {
                "fkitem": fkitem,
                "itemkey": itemkey,
                "itemvalue": itemvalue,
                "itemkeyvaluetype": itemkeyvaluetype,
            },
        )

    # ====================================================
    # itemloading (with product support)
    # ====================================================

    def add_loading(
            self,
            fkitem: int,
            dailyrollupexists: int,
            monthyear: str,
            percent: float,
            fkproduct: Optional[int] = None,
    ) -> int:
        """Insert itemloading. Returns auto-generated id."""
        cur = self._execute(
            'INSERT INTO "itemloading" ("fkitem","dailyrollupexists","monthyear","percent","fkproduct") '
            'VALUES (?,?,?,?,?);',
            (fkitem, dailyrollupexists, monthyear, percent, fkproduct),
        )
        return cur.lastrowid

    def update_loading(
            self,
            id: int,
            fkitem: Optional[int] = None,
            dailyrollupexists: Optional[int] = None,
            monthyear: Optional[str] = None,
            percent: Optional[float] = None,
            fkproduct: Optional[int] = None,
    ) -> None:
        """Update itemloading by id."""
        set_clause, params = self._update_set_clause(
            {
                "fkitem": fkitem,
                "dailyrollupexists": dailyrollupexists,
                "monthyear": monthyear,
                "percent": percent,
                "fkproduct": fkproduct,
            }
        )
        self._execute(f'UPDATE "itemloading" SET {set_clause} WHERE "id" = ?;', params + (id,))

    def delete_loading(self, id: int) -> None:
        """Delete itemloading by id."""
        self._execute('DELETE FROM "itemloading" WHERE "id" = ?;', (id,))

    def get_loading_by_id(self, id: int) -> Optional[sqlite3.Row]:
        """Get itemloading by id."""
        cur = self._execute('SELECT * FROM "itemloading" WHERE "id" = ?;', (id,))
        return cur.fetchone()

    def upsert_loading(
            self,
            fkitem: int,
            monthyear: str,
            percent: float,
            fkproduct: Optional[int] = None
    ) -> None:
        """Insert or update loading percentage for item, month, and product."""
        cur = self._execute(
            'SELECT "id" FROM "itemloading" WHERE "fkitem" = ? AND "monthyear" = ? AND '
            '("fkproduct" = ? OR ("fkproduct" IS NULL AND ? IS NULL));',
            (fkitem, monthyear, fkproduct, fkproduct),
        )
        existing = cur.fetchone()

        if existing:
            self._execute(
                'UPDATE "itemloading" SET "percent" = ? WHERE "id" = ?;',
                (percent, existing["id"]),
            )
        else:
            self.add_loading(fkitem, 0, monthyear, percent, fkproduct)

    def upsert_item_loading(
            self,
            fkitem: int,
            monthyear: str,
            percent: float,
            fkproduct: Optional[int] = None
    ) -> None:
        """Alias for upsert_loading for consistency."""
        self.upsert_loading(fkitem, monthyear, percent, fkproduct)

    def get_loadings_for_items(
            self,
            item_ids: List[int]
    ) -> Dict[Tuple[int, str, Optional[int]], float]:
        """Return dict of (item_id, monthyear, product_id) -> percent for given items."""
        if not item_ids:
            return {}

        placeholders = ",".join("?" * len(item_ids))
        cur = self._execute(
            f'SELECT "fkitem", "monthyear", "fkproduct", "percent" FROM "itemloading" '
            f'WHERE "fkitem" IN ({placeholders});',
            tuple(item_ids),
        )

        result = {}
        for row in cur.fetchall():
            key = (row["fkitem"], row["monthyear"], row["fkproduct"])
            result[key] = row["percent"]
        return result

    def find_loading_ids(
            self,
            fkitem: Optional[int] = None,
            monthyear: Optional[str] = None,
            dailyrollupexists: Optional[int] = None,
            fkproduct: Optional[int] = None,
    ) -> List[int]:
        """Return list of itemloading.id values matching filters."""
        return self._indices_by_fields(
            "itemloading",
            "id",
            {
                "fkitem": fkitem,
                "monthyear": monthyear,
                "dailyrollupexists": dailyrollupexists,
                "fkproduct": fkproduct,
            },
        )

    # ====================================================
    # item_product_map
    # ====================================================

    def add_item_product_mapping(self, fkitem: int, fkproduct: int) -> None:
        """Create item-product relationship."""
        self._execute(
            'INSERT OR IGNORE INTO "item_product_map" ("fkitem", "fkproduct") VALUES (?, ?);',
            (fkitem, fkproduct),
        )

    def remove_item_product_mapping(self, fkitem: int, fkproduct: int) -> None:
        """Remove item-product relationship."""
        self._execute(
            'DELETE FROM "item_product_map" WHERE "fkitem" = ? AND "fkproduct" = ?;',
            (fkitem, fkproduct),
        )

    def get_products_for_item(self, fkitem: int) -> List[sqlite3.Row]:
        """Get all products associated with an item."""
        cur = self._execute(
            'SELECT i.* FROM "items" i '
            'JOIN "item_product_map" ipm ON i.id = ipm.fkproduct '
            'WHERE ipm.fkitem = ? ORDER BY i.itemname;',
            (fkitem,),
        )
        return cur.fetchall()

    def get_items_for_product(self, fkproduct: int) -> List[sqlite3.Row]:
        """Get all items associated with a product."""
        cur = self._execute(
            'SELECT i.* FROM "items" i '
            'JOIN "item_product_map" ipm ON i.id = ipm.fkitem '
            'WHERE ipm.fkproduct = ? ORDER BY i.itemname;',
            (fkproduct,),
        )
        return cur.fetchall()

    # ====================================================
    # Listing helpers
    # ====================================================

    def list_items(self) -> Iterable[sqlite3.Row]:
        """Get all items ordered by id."""
        return self._execute('SELECT * FROM "items" ORDER BY "id";').fetchall()

    def list_itemtypes(self) -> Iterable[sqlite3.Row]:
        """Get all itemtypes ordered by id."""
        return self._execute('SELECT * FROM "itemtypes" ORDER BY "id";').fetchall()

    def list_products(self) -> Iterable[sqlite3.Row]:
        """Get all items of type PRODUCT."""
        cur = self._execute(
            'SELECT i.* FROM "items" i '
            'JOIN "itemtypes" it ON i.fkitemtype = it.id '
            'WHERE it.typename = ? ORDER BY i.itemname;',
            ('PRODUCT',),
        )
        return cur.fetchall()

    def list_characteristics_for_item(self, fkitem: int) -> Iterable[sqlite3.Row]:
        """Get all characteristics for an item."""
        return self._execute(
            'SELECT * FROM "itemcharacteristics" WHERE "fkitem" = ? ORDER BY "id";', (fkitem,)
        ).fetchall()

    def list_loadings_for_item(self, fkitem: int) -> Iterable[sqlite3.Row]:
        """Get all loadings for an item."""
        return self._execute(
            'SELECT * FROM "itemloading" WHERE "fkitem" = ? ORDER BY "monthyear";', (fkitem,)
        ).fetchall()

    def list_months(self) -> List[str]:
        """Return sorted list of distinct monthyear values from itemloading."""
        cur = self._execute(
            'SELECT DISTINCT "monthyear" FROM "itemloading" ORDER BY "monthyear";'
        )
        return [row["monthyear"] for row in cur.fetchall()]

    def generate_month_range(self, start_month: str, end_month: str) -> List[str]:
        """Generate list of months between start_month and end_month (YYYY-MM format)."""
        from datetime import datetime
        from dateutil import rrule

        try:
            start_date = datetime.strptime(start_month, '%Y-%m')
            end_date = datetime.strptime(end_month, '%Y-%m')

            months = []
            for dt in rrule.rrule(rrule.MONTHLY, dtstart=start_date, until=end_date):
                months.append(dt.strftime('%Y-%m'))

            return months
        except ValueError:
            return []

    # ====================================================
    # Convenience helpers
    # ====================================================

    def resolve_fkitem_from_name(self, itemname: str) -> Optional[int]:
        """Return items.id for a given itemname, or None if not found."""
        row = self.get_item_by_name(itemname)
        return int(row["id"]) if row else None

    def get_or_create_unallocated_product(self) -> int:
        """Get or create the UNALLOCATED product, return its id."""
        # Get PRODUCT type id
        product_type_id = self.get_itemtype_id_by_typename('PRODUCT')
        if not product_type_id:
            product_type_id = self.add_itemtype('PRODUCT')
            self.con.commit()

        # Get or create UNALLOCATED product
        unallocated = self.get_item_by_name('UNALLOCATED')
        if unallocated:
            return unallocated['id']

        unallocated_id = self.add_item('UNALLOCATED', product_type_id)
        self.con.commit()
        return unallocated_id

    # ====================================================
    # Product Loading Methods
    # ====================================================

    def add_product_loading(
            self,
            fkproduct: int,
            fkitemtype: int,
            monthyear: str,
            percent: float,
            notes: Optional[str] = None,
    ) -> int:
        """Insert product loading requirement. Returns auto-generated id."""
        cur = self._execute(
            'INSERT INTO "productloading" ("fkproduct","fkitemtype","monthyear","percent","notes") '
            'VALUES (?,?,?,?,?);',
            (fkproduct, fkitemtype, monthyear, percent, notes),
        )
        return cur.lastrowid

    def update_product_loading(
            self,
            id: int,
            fkproduct: Optional[int] = None,
            fkitemtype: Optional[int] = None,
            monthyear: Optional[str] = None,
            percent: Optional[float] = None,
            notes: Optional[str] = None,
    ) -> None:
        """Update product loading by id."""
        set_clause, params = self._update_set_clause(
            {
                "fkproduct": fkproduct,
                "fkitemtype": fkitemtype,
                "monthyear": monthyear,
                "percent": percent,
                "notes": notes,
            }
        )
        self._execute(f'UPDATE "productloading" SET {set_clause} WHERE "id" = ?;', params + (id,))

    def delete_product_loading(self, id: int) -> None:
        """Delete product loading by id."""
        self._execute('DELETE FROM "productloading" WHERE "id" = ?;', (id,))

    def get_product_loading_by_id(self, id: int) -> Optional[sqlite3.Row]:
        """Get product loading by id."""
        cur = self._execute('SELECT * FROM "productloading" WHERE "id" = ?;', (id,))
        return cur.fetchone()

    def upsert_product_loading(
            self,
            fkproduct: int,
            fkitemtype: int,
            monthyear: str,
            percent: float,
            notes: Optional[str] = None
    ) -> None:
        """Insert or update product loading requirement for product, item type, and month."""
        cur = self._execute(
            'SELECT "id" FROM "productloading" WHERE "fkproduct" = ? AND "fkitemtype" = ? AND "monthyear" = ?;',
            (fkproduct, fkitemtype, monthyear),
        )
        existing = cur.fetchone()

        if existing:
            self._execute(
                'UPDATE "productloading" SET "percent" = ?, "notes" = ? WHERE "id" = ?;',
                (percent, notes, existing["id"]),
            )
        else:
            self.add_product_loading(fkproduct, fkitemtype, monthyear, percent, notes)

    def list_product_loadings_for_product(self, fkproduct: int) -> Iterable[sqlite3.Row]:
        """Get all loading requirements for a product."""
        return self._execute(
            'SELECT pl.*, it.typename FROM "productloading" pl '
            'JOIN "itemtypes" it ON pl.fkitemtype = it.id '
            'WHERE pl."fkproduct" = ? ORDER BY pl."monthyear", it.typename;',
            (fkproduct,)
        ).fetchall()

    def get_product_loadings_for_month(self, monthyear: str) -> List[sqlite3.Row]:
        """Get all product loading requirements for a specific month."""
        cur = self._execute(
            'SELECT pl.*, i.itemname as productname, it.typename '
            'FROM "productloading" pl '
            'JOIN "items" i ON pl.fkproduct = i.id '
            'JOIN "itemtypes" it ON pl.fkitemtype = it.id '
            'WHERE pl."monthyear" = ? '
            'ORDER BY i.itemname, it.typename;',
            (monthyear,)
        )
        return cur.fetchall()

    def find_product_loading_ids(
            self,
            fkproduct: Optional[int] = None,
            fkitemtype: Optional[int] = None,
            monthyear: Optional[str] = None,
    ) -> List[int]:
        """Return list of productloading.id values matching filters."""
        return self._indices_by_fields(
            "productloading",
            "id",
            {
                "fkproduct": fkproduct,
                "fkitemtype": fkitemtype,
                "monthyear": monthyear,
            },
        )

    def list_product_requirements_for_product(self, product_id: int) -> list:
        """
        Get all requirements for a specific product.
        Returns list of requirements with item details.

        Args:
            product_id: ID of the product

        Returns:
            List of dicts with keys: id, fkproduct, fkitem, itemname, typename,
                                      monthyear, percent, notes
        """
        query = '''
            SELECT 
                pr.id,
                pr.fkproduct,
                pr.fkitem,
                i.itemname,
                it.typename,
                pr.monthyear,
                pr.percent,
                pr.notes
            FROM productrequirements pr
            JOIN items i ON pr.fkitem = i.id
            JOIN itemtypes it ON i.fkitemtype = it.id
            WHERE pr.fkproduct = ?
            ORDER BY pr.monthyear, it.typename, i.itemname
        '''
        return self._execute(query, (product_id,)).fetchall()

    def get_product_requirement(self, requirement_id: int) -> dict:
        """
        Get a specific requirement by ID.

        Args:
            requirement_id: ID of the requirement

        Returns:
            Dict with requirement details or None if not found
        """
        query = '''
            SELECT 
                pr.id,
                pr.fkproduct,
                pr.fkitem,
                i.itemname,
                it.typename,
                pr.monthyear,
                pr.percent,
                pr.notes
            FROM productrequirements pr
            JOIN items i ON pr.fkitem = i.id
            JOIN itemtypes it ON i.fkitemtype = it.id
            WHERE pr.id = ?
        '''
        return self._execute(query, (requirement_id,)).fetchone()

    def add_product_requirement(self, fkproduct: int, fkitem: int, monthyear: str,
                                percent: float, notes: str = None) -> int:
        """
        Add a new product requirement.

        Args:
            fkproduct: ID of the product
            fkitem: ID of the specific item required
            monthyear: Month in YYYY-MM format
            percent: Percentage requirement (0-100+)
            notes: Optional notes

        Returns:
            ID of the new requirement
        """
        query = '''
            INSERT INTO productrequirements (fkproduct, fkitem, monthyear, percent, notes)
            VALUES (?, ?, ?, ?, ?)
        '''
        cur = self._execute(query, (fkproduct, fkitem, monthyear, percent, notes))
        return cur.lastrowid

    def update_product_requirement(self, requirement_id: int, fkproduct: int = None,
                                   fkitem: int = None, monthyear: str = None,
                                   percent: float = None, notes: str = None) -> None:
        """
        Update an existing product requirement.
        Only updates provided parameters (others remain unchanged).

        Args:
            requirement_id: ID of the requirement to update
            fkproduct: New product ID (optional)
            fkitem: New item ID (optional)
            monthyear: New month (optional)
            percent: New percentage (optional)
            notes: New notes (optional)
        """
        updates = []
        params = []

        if fkproduct is not None:
            updates.append('fkproduct = ?')
            params.append(fkproduct)

        if fkitem is not None:
            updates.append('fkitem = ?')
            params.append(fkitem)

        if monthyear is not None:
            updates.append('monthyear = ?')
            params.append(monthyear)

        if percent is not None:
            updates.append('percent = ?')
            params.append(percent)

        if notes is not None:
            updates.append('notes = ?')
            params.append(notes)

        if not updates:
            return

        params.append(requirement_id)
        query = f"UPDATE productrequirements SET {', '.join(updates)} WHERE id = ?"
        self._execute(query, tuple(params))

    def delete_product_requirement(self, requirement_id: int) -> None:
        """
        Delete a product requirement.

        Args:
            requirement_id: ID of the requirement to delete
        """
        query = 'DELETE FROM productrequirements WHERE id = ?'
        self._execute(query, (requirement_id,))

    def upsert_product_requirement(self, fkproduct: int, fkitem: int, monthyear: str,
                                   percent: float, notes: str = None) -> int:
        """
        Insert or update a product requirement.
        If requirement exists for this product-item-month, updates it.
        Otherwise, creates a new one.

        Args:
            fkproduct: ID of the product
            fkitem: ID of the specific item
            monthyear: Month in YYYY-MM format
            percent: Percentage requirement
            notes: Optional notes

        Returns:
            ID of the requirement (existing or new)
        """
        # Check if exists
        check_query = '''
            SELECT id FROM productrequirements
            WHERE fkproduct = ? AND fkitem = ? AND monthyear = ?
        '''
        existing = self._execute(check_query, (fkproduct, fkitem, monthyear)).fetchone()

        if existing:
            # Update existing
            update_query = '''
                UPDATE productrequirements
                SET percent = ?, notes = ?
                WHERE id = ?
            '''
            self._execute(update_query, (percent, notes, existing['id']))
            return existing['id']
        else:
            # Insert new
            return self.add_product_requirement(fkproduct, fkitem, monthyear, percent, notes)

    def find_product_requirement_ids(self, fkproduct: int = None, fkitem: int = None,
                                     monthyear: str = None) -> list:
        """
        Find requirement IDs matching the given criteria.

        Args:
            fkproduct: Filter by product ID (optional)
            fkitem: Filter by item ID (optional)
            monthyear: Filter by month (optional)

        Returns:
            List of requirement IDs
        """
        where_clauses = []
        params = []

        if fkproduct is not None:
            where_clauses.append('fkproduct = ?')
            params.append(fkproduct)

        if fkitem is not None:
            where_clauses.append('fkitem = ?')
            params.append(fkitem)

        if monthyear is not None:
            where_clauses.append('monthyear = ?')
            params.append(monthyear)

        where_clause = ' AND '.join(where_clauses) if where_clauses else '1=1'
        query = f'SELECT id FROM productrequirements WHERE {where_clause}'

        results = self._execute(query, tuple(params)).fetchall()
        return [row['id'] for row in results]

    def get_requirements_by_month(self, product_id: int, monthyear: str) -> list:
        """
        Get all requirements for a product in a specific month.

        Args:
            product_id: ID of the product
            monthyear: Month in YYYY-MM format

        Returns:
            List of requirements with item details
        """
        query = '''
            SELECT 
                pr.id,
                pr.fkitem,
                i.itemname,
                it.typename,
                pr.percent,
                pr.notes
            FROM productrequirements pr
            JOIN items i ON pr.fkitem = i.id
            JOIN itemtypes it ON i.fkitemtype = it.id
            WHERE pr.fkproduct = ? AND pr.monthyear = ?
            ORDER BY it.typename, i.itemname
        '''
        return self._execute(query, (product_id, monthyear)).fetchall()

    def get_requirements_for_item(self, item_id: int) -> list:
        """
        Get all products that require a specific item.

        Args:
            item_id: ID of the item

        Returns:
            List of requirements showing which products need this item
        """
        query = '''
            SELECT 
                pr.id,
                pr.fkproduct,
                p.itemname as productname,
                pr.monthyear,
                pr.percent,
                pr.notes
            FROM productrequirements pr
            JOIN items p ON pr.fkproduct = p.id
            WHERE pr.fkitem = ?
            ORDER BY pr.monthyear, p.itemname
        '''
        return self._execute(query, (item_id,)).fetchall()

    def compare_requirements_vs_allocations(self, product_id: int, monthyear: str) -> dict:
        """
        Compare requirements (what's needed) vs allocations (what's assigned)
        for a product in a specific month.

        Args:
            product_id: ID of the product
            monthyear: Month in YYYY-MM format

        Returns:
            Dict with keys:
              - requirements: List of required items with percentages
              - allocations: List of allocated items with percentages
              - gaps: List of items required but not allocated
              - excess: List of items allocated but not required
        """
        # Get requirements
        requirements_query = '''
            SELECT 
                pr.fkitem,
                i.itemname,
                it.typename,
                pr.percent as required_percent
            FROM productrequirements pr
            JOIN items i ON pr.fkitem = i.id
            JOIN itemtypes it ON i.fkitemtype = it.id
            WHERE pr.fkproduct = ? AND pr.monthyear = ?
        '''
        requirements = self._execute(requirements_query, (product_id, monthyear)).fetchall()

        # Get allocations
        allocations_query = '''
            SELECT 
                il.fkitem,
                i.itemname,
                it.typename,
                il.percent as allocated_percent
            FROM itemloading il
            JOIN items i ON il.fkitem = i.id
            JOIN itemtypes it ON i.fkitemtype = it.id
            WHERE il.fkproduct = ? AND il.monthyear = ?
        '''
        allocations = self._execute(allocations_query, (product_id, monthyear)).fetchall()

        # Convert to dicts for comparison
        req_dict = {r['fkitem']: r for r in requirements}
        alloc_dict = {a['fkitem']: a for a in allocations}

        # Find gaps (required but not allocated)
        gaps = []
        for item_id, req in req_dict.items():
            if item_id not in alloc_dict:
                gaps.append({
                    'fkitem': item_id,
                    'itemname': req['itemname'],
                    'typename': req['typename'],
                    'required_percent': req['required_percent'],
                    'allocated_percent': 0,
                    'gap_percent': req['required_percent']
                })
            else:
                alloc = alloc_dict[item_id]
                gap = req['required_percent'] - alloc['allocated_percent']
                if gap > 0:
                    gaps.append({
                        'fkitem': item_id,
                        'itemname': req['itemname'],
                        'typename': req['typename'],
                        'required_percent': req['required_percent'],
                        'allocated_percent': alloc['allocated_percent'],
                        'gap_percent': gap
                    })

        # Find excess (allocated but not required)
        excess = []
        for item_id, alloc in alloc_dict.items():
            if item_id not in req_dict:
                excess.append({
                    'fkitem': item_id,
                    'itemname': alloc['itemname'],
                    'typename': alloc['typename'],
                    'required_percent': 0,
                    'allocated_percent': alloc['allocated_percent'],
                    'excess_percent': alloc['allocated_percent']
                })
            else:
                req = req_dict[item_id]
                excess_amt = alloc['allocated_percent'] - req['required_percent']
                if excess_amt > 0:
                    excess.append({
                        'fkitem': item_id,
                        'itemname': alloc['itemname'],
                        'typename': alloc['typename'],
                        'required_percent': req['required_percent'],
                        'allocated_percent': alloc['allocated_percent'],
                        'excess_percent': excess_amt
                    })

        return {
            'requirements': requirements,
            'allocations': allocations,
            'gaps': gaps,
            'excess': excess
        }


