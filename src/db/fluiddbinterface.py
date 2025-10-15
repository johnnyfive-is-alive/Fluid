import sqlite3
from typing import Optional, Dict, Any, Iterable, Tuple, List


class VerificationDB:
    """
    SQLite helper for your schema with:
      • add / update / delete for each table
      • lookup helpers to get `id` using any other field(s)

    Notes:
      - All tables use 'id' as PRIMARY KEY AUTOINCREMENT
      - FK definitions reference proper id fields
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
        """
        Build a 'SET col1=?, col2=?' clause from a dict, skipping None values.
        """
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
        """
        Generic: return list of ids for rows in `table` that match non-None filters.
        """
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
        """Insert a new item type. Returns new row PK (itemtypes.id)."""
        cur = self._execute('INSERT INTO "itemtypes" ("typename") VALUES (?);', (typename,))
        return cur.lastrowid

    def update_itemtype(self, id: int, typename: Optional[str] = None) -> None:
        """Update fields for itemtypes by primary key."""
        set_clause, params = self._update_set_clause({"typename": typename})
        self._execute(f'UPDATE "itemtypes" SET {set_clause} WHERE "id" = ?;', params + (id,))

    def delete_itemtype(self, id: int) -> None:
        """Delete an itemtype by primary key."""
        self._execute('DELETE FROM "itemtypes" WHERE "id" = ?;', (id,))

    def get_itemtype_id_by_typename(self, typename: str) -> Optional[int]:
        """Return the id for an itemtype by typename (None if not found)."""
        ids = self._indices_by_fields("itemtypes", "id", {"typename": typename})
        return ids[0] if ids else None

    # ====================================================
    # items
    # ====================================================

    def add_item(self, itemname: str, fkitemtype: int) -> int:
        """Insert into items. Returns auto-generated id."""
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
        """Update items row identified by its id."""
        set_clause, params = self._update_set_clause(
            {"itemname": itemname, "fkitemtype": fkitemtype}
        )
        self._execute(f'UPDATE "items" SET {set_clause} WHERE "id" = ?;', params + (id,))

    def delete_item(self, id: int) -> None:
        """Delete an item by its id."""
        self._execute('DELETE FROM "items" WHERE "id" = ?;', (id,))

    def get_item_by_id(self, id: int) -> Optional[sqlite3.Row]:
        cur = self._execute('SELECT * FROM "items" WHERE "id" = ?;', (id,))
        return cur.fetchone()

    def get_item_by_name(self, itemname: str) -> Optional[sqlite3.Row]:
        cur = self._execute('SELECT * FROM "items" WHERE "itemname" = ?;', (itemname,))
        return cur.fetchone()

    def get_item_id_by_name(self, itemname: str) -> Optional[int]:
        """Return items.id for a given itemname (None if not found)."""
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
        """
        Insert into itemcharacteristics. Returns auto-generated id.
        """
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
        """Update itemcharacteristics by primary key 'id'."""
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
        """Delete from itemcharacteristics by primary key 'id'."""
        self._execute('DELETE FROM "itemcharacteristics" WHERE "id" = ?;', (id,))

    def find_itemcharacteristics_ids(
            self,
            fkitem: Optional[int] = None,
            itemkey: Optional[str] = None,
            itemvalue: Optional[str] = None,
            itemkeyvaluetype: Optional[str] = None,
    ) -> List[int]:
        """Return list of itemcharacteristics.id values matching provided filters."""
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
    # itemloading
    # ====================================================

    def add_loading(
            self,
            fkitem: int,
            dailyrollupexists: int,
            monthyear: str,
            percent: float,
    ) -> int:
        """Insert into itemloading. Returns auto-generated id."""
        cur = self._execute(
            'INSERT INTO "itemloading" ("fkitem","dailyrollupexists","monthyear","percent") '
            'VALUES (?,?,?,?);',
            (fkitem, dailyrollupexists, monthyear, percent),
        )
        return cur.lastrowid

    def update_loading(
            self,
            id: int,
            fkitem: Optional[int] = None,
            dailyrollupexists: Optional[int] = None,
            monthyear: Optional[str] = None,
            percent: Optional[float] = None,
    ) -> None:
        """Update itemloading by primary key 'id'."""
        set_clause, params = self._update_set_clause(
            {
                "fkitem": fkitem,
                "dailyrollupexists": dailyrollupexists,
                "monthyear": monthyear,
                "percent": percent,
            }
        )
        self._execute(f'UPDATE "itemloading" SET {set_clause} WHERE "id" = ?;', params + (id,))

    def delete_loading(self, id: int) -> None:
        """Delete from itemloading by primary key 'id'."""
        self._execute('DELETE FROM "itemloading" WHERE "id" = ?;', (id,))

    def upsert_loading(self, fkitem: int, monthyear: str, percent: float) -> None:
        """
        Insert or update loading percentage for a given item and month.
        Uses dailyrollupexists=0 as default for new records.
        """
        cur = self._execute(
            'SELECT "id" FROM "itemloading" WHERE "fkitem" = ? AND "monthyear" = ?;',
            (fkitem, monthyear),
        )
        existing = cur.fetchone()

        if existing:
            self._execute(
                'UPDATE "itemloading" SET "percent" = ? WHERE "id" = ?;',
                (percent, existing["id"]),
            )
        else:
            self.add_loading(fkitem, 0, monthyear, percent)

    def get_loadings_for_items(self, item_ids: List[int]) -> Dict[Tuple[int, str], float]:
        """
        Return dict of (item_id, monthyear) -> percent for given items.
        """
        if not item_ids:
            return {}

        placeholders = ",".join("?" * len(item_ids))
        cur = self._execute(
            f'SELECT "fkitem", "monthyear", "percent" FROM "itemloading" '
            f'WHERE "fkitem" IN ({placeholders});',
            tuple(item_ids),
        )

        result = {}
        for row in cur.fetchall():
            key = (row["fkitem"], row["monthyear"])
            result[key] = row["percent"]
        return result

    def find_loading_ids(
            self,
            fkitem: Optional[int] = None,
            monthyear: Optional[str] = None,
    ) -> List[int]:
        """Return list of itemloading.id values matching provided filters."""
        return self._indices_by_fields(
            "itemloading",
            "id",
            {"fkitem": fkitem, "monthyear": monthyear},
        )

    # ====================================================
    # Listing helpers
    # ====================================================

    def list_items(self) -> Iterable[sqlite3.Row]:
        return self._execute('SELECT * FROM "items" ORDER BY "id";').fetchall()

    def list_itemtypes(self) -> Iterable[sqlite3.Row]:
        return self._execute('SELECT * FROM "itemtypes" ORDER BY "id";').fetchall()

    def list_characteristics_for_item(self, fkitem: int) -> Iterable[sqlite3.Row]:
        return self._execute(
            'SELECT * FROM "itemcharacteristics" WHERE "fkitem" = ? ORDER BY "id";', (fkitem,)
        ).fetchall()

    def list_loadings_for_item(self, fkitem: int) -> Iterable[sqlite3.Row]:
        return self._execute(
            'SELECT * FROM "itemloading" WHERE "fkitem" = ? ORDER BY "monthyear";', (fkitem,)
        ).fetchall()

    def list_months(self) -> List[str]:
        """Return sorted list of distinct monthyear values from itemloading."""
        cur = self._execute(
            'SELECT DISTINCT "monthyear" FROM "itemloading" ORDER BY "monthyear";'
        )
        return [row["monthyear"] for row in cur.fetchall()]