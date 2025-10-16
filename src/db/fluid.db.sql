BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "item_product_map" (
	"fkitem"	INTEGER NOT NULL,
	"fkproduct"	INTEGER NOT NULL,
	PRIMARY KEY("fkitem","fkproduct"),
	FOREIGN KEY("fkitem") REFERENCES "items"("id") ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY("fkproduct") REFERENCES "items"("id") ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE IF NOT EXISTS "itemcharacteristics" (
	"id"	INTEGER,
	"fkitem"	INTEGER NOT NULL,
	"itemkey"	TEXT NOT NULL,
	"itemvalue"	TEXT NOT NULL,
	"itemkeyvaluetype"	TEXT,
	UNIQUE("fkitem","itemkey"),
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("fkitem") REFERENCES "items"("id") ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE IF NOT EXISTS "itemloading" (
	"id"	INTEGER,
	"fkitem"	INTEGER NOT NULL,
	"dailyrollupexists"	INTEGER NOT NULL CHECK("dailyrollupexists" IN (0, 1)),
	"monthyear"	TEXT NOT NULL CHECK(length("monthyear") = 7 AND substr("monthyear", 5, 1) = '-' AND CAST(substr("monthyear", 1, 4) AS INTEGER) BETWEEN 2000 AND 2100 AND CAST(substr("monthyear", 6, 2) AS INTEGER) BETWEEN 1 AND 12),
	"percent"	REAL NOT NULL CHECK("percent" BETWEEN 0 AND 100),
	"fkproduct"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("fkitem") REFERENCES "items"("id") ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY("fkproduct") REFERENCES "items"("id")
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
INSERT INTO "itemcharacteristics" VALUES (1,6,'Location','Ottawa','str');
INSERT INTO "itemloading" VALUES (1,6,0,'2025-01',14.0,NULL);
INSERT INTO "itemloading" VALUES (2,6,0,'2025-02',22.0,NULL);
INSERT INTO "itemloading" VALUES (3,6,0,'2025-03',22.0,NULL);
INSERT INTO "itemloading" VALUES (4,6,0,'2025-04',22.0,NULL);
INSERT INTO "itemloading" VALUES (5,6,0,'2025-05',22.0,NULL);
INSERT INTO "items" VALUES (1,'DV-JAGUAR',3);
INSERT INTO "items" VALUES (2,'DV-NISSAN',3);
INSERT INTO "items" VALUES (3,'Gabor Farkas',4);
INSERT INTO "items" VALUES (4,'Steven Luo',4);
INSERT INTO "items" VALUES (5,'Alexey Smirnov',4);
INSERT INTO "items" VALUES (6,'DV-SPYKER',3);
INSERT INTO "items" VALUES (7,'UNALLOCATED',6);
INSERT INTO "items" VALUES (8,'BEEHIVE 300G',6);
INSERT INTO "items" VALUES (9,'GENERIC 300L',6);
INSERT INTO "items" VALUES (10,'R64-72',6);
INSERT INTO "items" VALUES (11,'BEEHIVE R304',6);
INSERT INTO "itemtypes" VALUES (3,'STATION');
INSERT INTO "itemtypes" VALUES (4,'RESOURCE');
INSERT INTO "itemtypes" VALUES (5,'UNIT');
INSERT INTO "itemtypes" VALUES (6,'PRODUCT');
CREATE INDEX IF NOT EXISTS "idx_item_product_map_fkproduct" ON "item_product_map" (
	"fkproduct"
);
CREATE INDEX IF NOT EXISTS "idx_itemcharacteristics_fkitem" ON "itemcharacteristics" (
	"fkitem"
);
CREATE INDEX IF NOT EXISTS "idx_itemloading_fkitem" ON "itemloading" (
	"fkitem"
);
COMMIT;
