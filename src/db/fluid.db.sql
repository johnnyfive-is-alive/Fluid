BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "itemcharacteristics" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "fkitem" INTEGER NOT NULL,
  "itemkey" TEXT NOT NULL,
  "itemvalue" TEXT NOT NULL,
  "itemkeyvaluetype" TEXT,
  UNIQUE("fkitem","itemkey"),
  FOREIGN KEY("fkitem") REFERENCES "items"("id")
    ON DELETE CASCADE
    ON UPDATE CASCADE
);
CREATE TABLE IF NOT EXISTS "itemloading" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "fkitem" INTEGER NOT NULL,
  "dailyrollupexists" INTEGER NOT NULL CHECK("dailyrollupexists" IN (0, 1)),
  "monthyear" TEXT NOT NULL CHECK(
    length("monthyear") = 7 AND substr("monthyear", 5, 1) = '-' AND
    CAST(substr("monthyear", 1, 4) AS INTEGER) BETWEEN 2000 AND 2100 AND
    CAST(substr("monthyear", 6, 2) AS INTEGER) BETWEEN 1 AND 12
  ),
  "percent" REAL NOT NULL CHECK("percent" BETWEEN 0 AND 100),
  -- Optional but recommended:
  -- UNIQUE("fkitem","monthyear"),
  FOREIGN KEY("fkitem") REFERENCES "items"("id")
    ON DELETE CASCADE
    ON UPDATE CASCADE
);
CREATE TABLE IF NOT EXISTS "items" (
	"id"	INTEGER NOT NULL,
	"itemname"	TEXT NOT NULL,
	"fkitemtype"	INTEGER NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("fkitemtype") REFERENCES "itemtypes"("id")
);
CREATE TABLE IF NOT EXISTS "itemtypes" (
	"id"	INTEGER NOT NULL,
	"typename"	TEXT NOT NULL UNIQUE,
	PRIMARY KEY("id" AUTOINCREMENT)
);
INSERT INTO "itemtypes" VALUES (3,'STATION');
INSERT INTO "itemtypes" VALUES (4,'RESOURCE');
INSERT INTO "itemtypes" VALUES (5,'UNIT');
CREATE INDEX "idx_itemcharacteristics_fkitem" ON "itemcharacteristics" ("fkitem");
CREATE INDEX "idx_itemloading_fkitem" ON "itemloading" (
	"fkitem"
);
COMMIT;
