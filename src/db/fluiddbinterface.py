import sqlite3
from typing import Optional, Dict, Any, Iterable, Tuple, List

class VerificationDB:
    """
    SQLite helper for your schema with:
      • add / update / delete for each table
      • clear lookup helpers to get `index` using any other field(s)

    Notes:
      - 'items.index' is UNIQUE (used as identifier here).
      - FK definitions in the schema reference items(itemname), which SQLite
        won't enforce as a real FK due to type mismatch; we still provide
        convenience resolvers by name or index.
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
        index_col: str,
        filters: Dict[str, Any],
    ) -> List[int]:
        """
        Generic: return list of indices for rows in `table` that match non-None filters.
        Example:
            _indices_by_fields("items", "index", {"itemname": "Station-01"})
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
            f'SELECT "{index_col}" AS idx FROM "{table}" WHERE {where_sql};',
            tuple(params),
        )
        return [int(r["idx"]) for r in cur.fetchall()]

    # ====================================================
    # itemtypes
    # ====================================================

    def add_itemtype(self, typename: str) -> int:
        """Insert a new item type. Returns new row PK (itemtypes.index)."""
        cur = self._execute('INSERT INTO "itemtypes" ("typename") VALUES (?);', (typename,))
        return cur.lastrowid

    def update_itemtype(self, index: int, typename: Optional[str] = None) -> None:
        """Update fields for itemtypes by primary key."""
        set_clause, params = self._update_set_clause({"typename": typename})
        self._execute(f'UPDATE "itemtypes" SET {set_clause} WHERE "index" = ?;', params + (index,))

    def delete_itemtype(self, index: int) -> None:
        """Delete an itemtype by primary key."""
        self._execute('DELETE FROM "itemtypes" WHERE "index" = ?;', (index,))

    # ---- Lookups (index by other fields)
    def get_itemtype_index_by_typename(self, typename: str) -> Optional[int]:
        """
        Return the index for an itemtype by typename (None if not found).
        """
        ids = self._indices_by_fields("itemtypes", "index", {"typename": typename})
        return ids[0] if ids else None

    # ====================================================
    # items
    # ====================================================

    def add_item(self, index: int, itemname: str, fkitemtype: int) -> int:
        """
        Insert into items. 'index' is UNIQUE (not PK). Returns provided index.
        """
        self._execute(
            'INSERT INTO "items" ("index","itemname","fkitemtype") VALUES (?,?,?);',
            (index, itemname, fkitemtype),
        )
        return index

    def update_item(
        self,
        index: int,
        itemname: Optional[str] = None,
        fkitemtype: Optional[int] = None,
    ) -> None:
        """Update items row identified by its UNIQUE 'index'."""
        set_clause, params = self._update_set_clause(
            {"itemname": itemname, "fkitemtype": fkitemtype}
        )
        self._execute(f'UPDATE "items" SET {set_clause} WHERE "index" = ?;', params + (index,))

    def delete_item(self, index: int) -> None:
        """Delete an item by its UNIQUE 'index'."""
        self._execute('DELETE FROM "items" WHERE "index" = ?;', (index,))

    # Existing convenience lookups
    def get_item_by_index(self, index: int) -> Optional[sqlite3.Row]:
        cur = self._execute('SELECT * FROM "items" WHERE "index" = ?;', (index,))
        return cur.fetchone()

    def get_item_by_name(self, itemname: str) -> Optional[sqlite3.Row]:
        cur = self._execute('SELECT * FROM "items" WHERE "itemname" = ?;', (itemname,))
        return cur.fetchone()

    # ---- New: index lookups by other fields
    def get_item_index_by_name(self, itemname: str) -> Optional[int]:
        """
        Return items.index for a given itemname (None if not found).
        """
        ids = self._indices_by_fields("items", "index", {"itemname": itemname})
        return ids[0] if ids else None

    def get_item_index_by_fkitemtype(self, fkitemtype: int) -> Optional[int]:
        """
        Return items.index for a given fkitemtype.
        NOTE: fkitemtype is UNIQUE in your schema, so this returns at most one.
        """
        ids = self._indices_by_fields("items", "index", {"fkitemtype": fkitemtype})
        return ids[0] if ids else None

    # ====================================================
    # itemdates
    # ====================================================

    def add_itemdate(
        self,
        fkitem: int,
        dailyrollupexists: int,
        monthyear: str,
        index: Optional[int] = None,
    ) -> int:
        """
        Insert into itemdates. If 'index' is None, AUTOINCREMENT applies.
        Returns row PK (itemdates.index).
        """
        if index is None:
            cur = self._execute(
                'INSERT INTO "itemdates" ("fkitem","dailyrollupexists","monthyear") VALUES (?,?,?);',
                (fkitem, dailyrollupexists, monthyear),
            )
        else:
            cur = self._execute(
                'INSERT INTO "itemdates" ("index","fkitem","dailyrollupexists","monthyear") VALUES (?,?,?,?);',
                (index, fkitem, dailyrollupexists, monthyear),
            )
        return cur.lastrowid

    def update_itemdate(
        self,
        index: int,
        fkitem: Optional[int] = None,
        dailyrollupexists: Optional[int] = None,
        monthyear: Optional[str] = None,
    ) -> None:
        """Update itemdates by primary key 'index'."""
        set_clause, params = self._update_set_clause(
            {"fkitem": fkitem, "dailyrollupexists": dailyrollupexists, "monthyear": monthyear}
        )
        self._execute(f'UPDATE "itemdates" SET {set_clause} WHERE "index" = ?;', params + (index,))

    def delete_itemdate(self, index: int) -> None:
        """Delete from itemdates by primary key 'index'."""
        self._execute('DELETE FROM "itemdates" WHERE "index" = ?;', (index,))

    # ---- Lookups (indices by other fields; may return multiple)
    def find_itemdates_indices(
        self,
        fkitem: Optional[int] = None,
        dailyrollupexists: Optional[int] = None,
        monthyear: Optional[str] = None,
    ) -> List[int]:
        """
        Return list of itemdates.index values matching provided filters.
        At least one filter must be provided.
        """
        return self._indices_by_fields(
            "itemdates",
            "index",
            {"fkitem": fkitem, "dailyrollupexists": dailyrollupexists, "monthyear": monthyear},
        )

    # ====================================================
    # itemcharacteristics
    # ====================================================

    def add_itemcharacteristic(
        self,
        index: int,
        fkitem: int,
        itemkey: str,
        itemvalue: str,
        itemkeyvaluetype: Optional[str] = None,
    ) -> int:
        """
        Insert into itemcharacteristics. 'index' is PRIMARY KEY (no AUTOINCREMENT).
        Returns the provided index.
        """
        self._execute(
            'INSERT INTO "itemcharacteristics" ("index","fkitem","itemkey","itemvalue","itemkeyvaluetype") '
            'VALUES (?,?,?,?,?);',
            (index, fkitem, itemkey, itemvalue, itemkeyvaluetype),
        )
        return index

    def update_itemcharacteristic(
        self,
        index: int,
        fkitem: Optional[int] = None,
        itemkey: Optional[str] = None,
        itemvalue: Optional[str] = None,
        itemkeyvaluetype: Optional[str] = None,
    ) -> None:
        """Update itemcharacteristics by primary key 'index'."""
        set_clause, params = self._update_set_clause(
            {
                "fkitem": fkitem,
                "itemkey": itemkey,
                "itemvalue": itemvalue,
                "itemkeyvaluetype": itemkeyvaluetype,
            }
        )
        self._execute(
            f'UPDATE "itemcharacteristics" SET {set_clause} WHERE "index" = ?;',
            params + (index,),
        )

    def delete_itemcharacteristic(self, index: int) -> None:
        """Delete from itemcharacteristics by primary key 'index'."""
        self._execute('DELETE FROM "itemcharacteristics" WHERE "index" = ?;', (index,))

    # ---- Lookups (indices by other fields; may return multiple)
    def find_itemcharacteristics_indices(
        self,
        fkitem: Optional[int] = None,
        itemkey: Optional[str] = None,
        itemvalue: Optional[str] = None,
        itemkeyvaluetype: Optional[str] = None,
    ) -> List[int]:
        """
        Return list of itemcharacteristics.index values matching provided filters.
        At least one filter must be provided.
        """
        return self._indices_by_fields(
            "itemcharacteristics",
            "index",
            {
                "fkitem": fkitem,
                "itemkey": itemkey,
                "itemvalue": itemvalue,
                "itemkeyvaluetype": itemkeyvaluetype,
            },
        )

    # ====================================================
    # Listing helpers
    # ====================================================

    def list_items(self) -> Iterable[sqlite3.Row]:
        return self._execute('SELECT * FROM "items" ORDER BY "index";').fetchall()

    def list_itemtypes(self) -> Iterable[sqlite3.Row]:
        return self._execute('SELECT * FROM "itemtypes" ORDER BY "index";').fetchall()

    def list_itemdates_for_item(self, fkitem: int) -> Iterable[sqlite3.Row]:
        return self._execute(
            'SELECT * FROM "itemdates" WHERE "fkitem" = ? ORDER BY "index";', (fkitem,)
        ).fetchall()

    def list_characteristics_for_item(self, fkitem: int) -> Iterable[sqlite3.Row]:
        return self._execute(
            'SELECT * FROM "itemcharacteristics" WHERE "fkitem" = ? ORDER BY "index";', (fkitem,)
        ).fetchall()

    # ====================================================
    # Convenience: resolve fkitem from itemname (since FK points to itemname in schema)
    # ====================================================

    def resolve_fkitem_from_name(self, itemname: str) -> Optional[int]:
        """
        Return items.index for a given itemname, or None if not found.
        """
        row = self.get_item_by_name(itemname)
        return int(row["index"]) if row else None
