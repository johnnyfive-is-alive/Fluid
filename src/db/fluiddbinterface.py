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