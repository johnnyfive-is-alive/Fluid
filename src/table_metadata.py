"""
Metadata configuration for database tables.
Helps AI understand formatting conventions and business rules.
"""

TABLE_METADATA = {
    'itemtypes': {
        'description': 'Categories/types for items',
        'capitalization': 'UPPERCASE',
        'columns': {
            'id': {
                'description': 'Primary key',
                'format': 'Integer'
            },
            'typename': {
                'description': 'Type name (always uppercase)',
                'format': 'UPPERCASE',
                'examples': ['STATION', 'RESOURCE', 'UNIT', 'PRODUCT'],
                'validation': 'Must be unique and uppercase'
            }
        },
        'common_queries': [
            'List all item types',
            'Count items by type'
        ]
    },

    'items': {
        'description': 'Individual items (stations, resources, products, etc.)',
        'capitalization': 'TYPE_DEPENDENT',
        'columns': {
            'id': {
                'description': 'Primary key',
                'format': 'Integer'
            },
            'itemname': {
                'description': 'Item name (capitalization depends on item type)',
                'format': 'TYPE_DEPENDENT',
                'examples': ['DV-SPYKER', 'BEEHIVE 300G', 'Gabor Farkas', 'UNALLOCATED'],
                'validation': 'Must be unique',
                'capitalization_rules': {
                    'STATION': 'UPPERCASE - Station names are always uppercase (e.g., DV-SPYKER, DV-JAGUAR)',
                    'PRODUCT': 'UPPERCASE - Product names are always uppercase (e.g., BEEHIVE 300G, GENERIC 300L, UNALLOCATED)',
                    'RESOURCE': 'MIXED - Resource names may be mixed case (e.g., person names like Gabor Farkas)',
                    'UNIT': 'MIXED - Unit names may be mixed case'
                }
            },
            'fkitemtype': {
                'description': 'Foreign key to itemtypes',
                'format': 'Integer'
            }
        },
        'business_rules': [
            'Stations (type=STATION) ALWAYS have UPPERCASE names',
            'Products (type=PRODUCT) ALWAYS have UPPERCASE names',
            'Resources (type=RESOURCE) may be person names in mixed case',
            'UNALLOCATED is a special system product',
            'When filtering stations or products, use uppercase: WHERE itemname = \'DV-SPYKER\' or WHERE itemname LIKE \'%BEEHIVE%\''
        ],
        'common_queries': [
            'List all items with their types',
            'Find items of a specific type',
            'Search items by name pattern'
        ]
    },

    'itemcharacteristics': {
        'description': 'Key-value properties for items',
        'capitalization': 'MIXED',
        'columns': {
            'id': {
                'description': 'Primary key',
                'format': 'Integer'
            },
            'fkitem': {
                'description': 'Foreign key to items',
                'format': 'Integer'
            },
            'itemkey': {
                'description': 'Characteristic name',
                'format': 'Mixed case',
                'examples': ['Location', 'Capacity', 'Status', 'Temperature']
            },
            'itemvalue': {
                'description': 'Characteristic value',
                'format': 'Mixed case or numeric',
                'examples': ['Ottawa', '500', 'Active', '72.5']
            },
            'itemkeyvaluetype': {
                'description': 'Data type hint (optional)',
                'format': 'Lowercase',
                'examples': ['str', 'int', 'float', 'bool']
            }
        },
        'constraints': [
            'Unique constraint on (fkitem, itemkey) - one key per item'
        ],
        'common_queries': [
            'Get all characteristics for an item',
            'Find items with specific characteristic values',
            'List all unique characteristic keys'
        ]
    },

    'itemloading': {
        'description': 'Loading/capacity allocation by month and product',
        'capitalization': 'N/A',
        'columns': {
            'id': {
                'description': 'Primary key',
                'format': 'Integer'
            },
            'fkitem': {
                'description': 'Foreign key to items',
                'format': 'Integer'
            },
            'dailyrollupexists': {
                'description': 'Flag for daily data (0 or 1)',
                'format': 'Boolean integer',
                'values': [0, 1]
            },
            'monthyear': {
                'description': 'Month in YYYY-MM format',
                'format': 'YYYY-MM',
                'examples': ['2025-01', '2025-12', '2024-09'],
                'validation': 'Must match pattern YYYY-MM with valid year/month'
            },
            'percent': {
                'description': 'Loading percentage',
                'format': 'Decimal',
                'range': '0 to 100',
                'examples': [14.5, 50.0, 100.0]
            },
            'fkproduct': {
                'description': 'Foreign key to items (product type), NULL = UNALLOCATED',
                'format': 'Integer or NULL',
                'notes': 'NULL represents unallocated/inactive capacity'
            }
        },
        'business_rules': [
            'Loading percentages for an item-month should sum to ≤100%',
            'NULL fkproduct represents UNALLOCATED/INACTIVE capacity',
            'Each row represents allocation to one product for one month',
            'Multiple rows per item-month allowed (one per product)'
        ],
        'common_queries': [
            'Total loading by product across months',
            'Items with loading >50% in any month',
            'Monthly loading trends for specific items',
            'Unallocated capacity by month'
        ]
    },

    'item_product_map': {
        'description': 'Many-to-many relationship between items and products',
        'capitalization': 'N/A',
        'columns': {
            'fkitem': {
                'description': 'Foreign key to items (non-product)',
                'format': 'Integer'
            },
            'fkproduct': {
                'description': 'Foreign key to items (product type)',
                'format': 'Integer'
            }
        },
        'constraints': [
            'Composite primary key on (fkitem, fkproduct)',
            'Defines which items can work on which products'
        ],
        'business_rules': [
            'An item can be mapped to multiple products',
            'Only items can be allocated to products via loading',
            'Products themselves are not mapped to other products'
        ],
        'common_queries': [
            'Which products can an item work on?',
            'Which items are mapped to a product?',
            'Items with no product mappings'
        ]
    }
}


def get_table_metadata(table_name: str) -> dict:
    """Get metadata for a specific table."""
    return TABLE_METADATA.get(table_name, {})


def get_column_format(table_name: str, column_name: str) -> str:
    """Get formatting information for a specific column."""
    table = TABLE_METADATA.get(table_name, {})
    columns = table.get('columns', {})
    column = columns.get(column_name, {})
    return column.get('format', 'Unknown')


def get_table_examples(table_name: str) -> list:
    """Get example queries for a table."""
    table = TABLE_METADATA.get(table_name, {})
    return table.get('common_queries', [])


def get_business_rules(table_name: str) -> list:
    """Get business rules for a table."""
    table = TABLE_METADATA.get(table_name, {})
    return table.get('business_rules', [])