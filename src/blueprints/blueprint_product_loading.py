"""
Enhanced Product Loading Allocation Blueprint
Allows selecting specific items (not just item types) based on characteristics
and assigning percentage allocations for each month.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime

bp = Blueprint('product_loading', __name__, url_prefix='/product-loading')


def get_db():
    """Get database connection for current request."""
    from app import get_db as app_get_db
    return app_get_db()


@bp.get('/<int:product_id>')
def enhanced_allocation_interface(product_id):
    """
    Enhanced product loading allocation interface.
    Allows filtering and selecting specific items with percentage allocation.
    """
    db = get_db()

    # Get product details
    product = db.get_item_by_id(product_id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('products.list_products'))

    # Verify it's a product
    product_type = db.get_itemtype_by_id(product['fkitemtype'])
    if not product_type or product_type['typename'] != 'PRODUCT':
        flash('Item is not a product.', 'danger')
        return redirect(url_for('products.list_products'))

    # Get all item types (excluding PRODUCT)
    all_itemtypes = db.list_itemtypes()
    item_types = [it for it in all_itemtypes if it['typename'] != 'PRODUCT']

    # Get unique characteristic keys
    char_keys_query = '''
        SELECT DISTINCT itemkey 
        FROM itemcharacteristics 
        ORDER BY itemkey
    '''
    char_keys = [row['itemkey'] for row in db._execute(char_keys_query).fetchall()]

    # Get month range - default to current year
    current_year = datetime.now().year
    default_months = [f"{current_year}-{str(m).zfill(2)}" for m in range(1, 13)]

    # Get existing allocations for this product
    existing_allocations_query = '''
        SELECT 
            il.id,
            il.fkitem,
            i.itemname,
            it.typename,
            il.monthyear,
            il.percent
        FROM itemloading il
        JOIN items i ON il.fkitem = i.id
        JOIN itemtypes it ON i.fkitemtype = it.id
        WHERE il.fkproduct = ?
        ORDER BY il.monthyear, i.itemname
    '''
    existing_allocations = db._execute(existing_allocations_query, (product_id,)).fetchall()

    return render_template(
        'product_loading_enhanced.html',
        product=product,
        item_types=item_types,
        char_keys=char_keys,
        default_months=default_months,
        existing_allocations=existing_allocations
    )


@bp.get('/view/<int:product_id>')
def view_product_loading(product_id):
    """
    View product loading profile - shows month-by-month resource requirements.
    This is the standard view (not the enhanced allocation interface).
    """
    db = get_db()

    # Get product details
    product = db.get_item_by_id(product_id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('products.list_products'))

    # Verify it's a product
    product_type = db.get_itemtype_by_id(product['fkitemtype'])
    if not product_type or product_type['typename'] != 'PRODUCT':
        flash('Item is not a product.', 'danger')
        return redirect(url_for('products.list_products'))

    # Get loading data for this product
    loading_query = '''
        SELECT 
            il.monthyear,
            i.itemname,
            it.typename,
            il.percent
        FROM itemloading il
        JOIN items i ON il.fkitem = i.id
        JOIN itemtypes it ON i.fkitemtype = it.id
        WHERE il.fkproduct = ?
        ORDER BY il.monthyear, i.itemname
    '''
    loading_data_rows = db._execute(loading_query, (product_id,)).fetchall()

    # Convert Row objects to dictionaries for JSON serialization
    loading_data = [dict(row) for row in loading_data_rows]

    return render_template(
        'product_loading_profile.html',
        product=product,
        loading_data=loading_data
    )


@bp.post('/<int:product_id>/filter-items')
def filter_items(product_id):
    """
    AJAX endpoint to filter items based on type and characteristics.
    Returns JSON list of matching items.
    """
    db = get_db()

    try:
        # Get filter parameters
        itemtype_id = request.form.get('itemtype_id', type=int)
        char_key = request.form.get('char_key', '').strip()
        char_value = request.form.get('char_value', '').strip()
        itemname_filter = request.form.get('itemname_filter', '').strip()

        # Build query
        query = '''
            SELECT DISTINCT
                i.id,
                i.itemname,
                it.typename
            FROM items i
            JOIN itemtypes it ON i.fkitemtype = it.id
        '''

        where_clauses = []
        params = []

        # Exclude products
        where_clauses.append("it.typename != 'PRODUCT'")

        # Item type filter
        if itemtype_id:
            where_clauses.append('i.fkitemtype = ?')
            params.append(itemtype_id)

        # Characteristic filters
        if char_key and char_value:
            query += '''
                JOIN itemcharacteristics ic ON i.id = ic.fkitem
            '''
            where_clauses.append('ic.itemkey = ?')
            where_clauses.append('ic.itemvalue LIKE ?')
            params.append(char_key)
            params.append(f'%{char_value}%')

        # Item name filter
        if itemname_filter:
            where_clauses.append('i.itemname LIKE ?')
            params.append(f'%{itemname_filter}%')

        # Add WHERE clause
        if where_clauses:
            query += ' WHERE ' + ' AND '.join(where_clauses)

        query += ' ORDER BY i.itemname'

        # Execute query
        items = db._execute(query, tuple(params)).fetchall()

        # Convert to JSON-serializable format
        items_list = [
            {
                'id': item['id'],
                'itemname': item['itemname'],
                'typename': item['typename']
            }
            for item in items
        ]

        return jsonify({
            'success': True,
            'items': items_list,
            'count': len(items_list)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.post('/<int:product_id>/get-allocations')
def get_allocations(product_id):
    """
    AJAX endpoint to get existing allocations for selected items and month.
    """
    db = get_db()

    try:
        month = request.form.get('month')
        item_ids = request.form.getlist('item_ids[]')

        if not month or not item_ids:
            return jsonify({
                'success': False,
                'error': 'Missing month or item_ids'
            }), 400

        # Get existing allocations
        placeholders = ','.join(['?'] * len(item_ids))
        query = f'''
            SELECT fkitem, percent
            FROM itemloading
            WHERE fkproduct = ?
            AND monthyear = ?
            AND fkitem IN ({placeholders})
        '''

        params = [product_id, month] + [int(id) for id in item_ids]
        results = db._execute(query, tuple(params)).fetchall()

        # Convert to dict
        allocations = {row['fkitem']: row['percent'] for row in results}

        return jsonify({
            'success': True,
            'allocations': allocations
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.post('/<int:product_id>/save-allocations')
def save_allocations(product_id):
    """
    Save allocation percentages for items to this product.
    """
    db = get_db()

    try:
        allocations = request.json

        if not allocations:
            return jsonify({
                'success': False,
                'error': 'No allocations provided'
            }), 400

        # Process each allocation
        for alloc in allocations:
            item_id = alloc['item_id']
            month = alloc['month']
            percent = alloc['percent']

            # Check if allocation exists
            existing_query = '''
                SELECT id FROM itemloading
                WHERE fkitem = ? AND fkproduct = ? AND monthyear = ?
            '''
            existing = db._execute(existing_query, (item_id, product_id, month)).fetchone()

            if percent == 0 and existing:
                # Delete if percent is 0
                db._execute('DELETE FROM itemloading WHERE id = ?', (existing['id'],))
            elif percent > 0:
                if existing:
                    # Update existing
                    db._execute(
                        'UPDATE itemloading SET percent = ? WHERE id = ?',
                        (percent, existing['id'])
                    )
                else:
                    # Insert new
                    db._execute(
                        'INSERT INTO itemloading (fkitem, fkproduct, monthyear, percent) VALUES (?, ?, ?, ?)',
                        (item_id, product_id, month, percent)
                    )

        db.con.commit()

        return jsonify({
            'success': True,
            'message': f'Saved {len(allocations)} allocation(s)'
        })

    except Exception as e:
        db.con.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500