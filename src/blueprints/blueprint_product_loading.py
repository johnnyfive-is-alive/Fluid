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
        month = request.form.get('month', '').strip()
        item_ids = request.form.getlist('item_ids[]', type=int)

        if not month or not item_ids:
            return jsonify({'success': False, 'error': 'Missing parameters'}), 400

        # Get existing allocations
        placeholders = ','.join(['?'] * len(item_ids))
        query = f'''
            SELECT 
                il.fkitem,
                il.percent
            FROM itemloading il
            WHERE il.fkproduct = ?
                AND il.monthyear = ?
                AND il.fkitem IN ({placeholders})
        '''

        params = [product_id, month] + item_ids
        results = db._execute(query, tuple(params)).fetchall()

        # Convert to dict
        allocations = {
            row['fkitem']: row['percent']
            for row in results
        }

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
    Save product loading allocations for selected items and months.
    Handles multiple items and multiple months.
    """
    db = get_db()

    try:
        # Get product
        product = db.get_item_by_id(product_id)
        if not product:
            return jsonify({
                'success': False,
                'error': 'Product not found'
            }), 404

        # Get form data
        allocations_data = request.get_json()

        if not allocations_data:
            return jsonify({
                'success': False,
                'error': 'No allocation data provided'
            }), 400

        saved_count = 0
        updated_count = 0
        deleted_count = 0

        # Process each allocation
        for allocation in allocations_data:
            item_id = allocation.get('item_id')
            month = allocation.get('month')
            percent = allocation.get('percent')

            if not item_id or not month:
                continue

            # Handle deletion (percent = 0 or None)
            if percent is None or float(percent) <= 0:
                # Delete existing allocation
                delete_query = '''
                    DELETE FROM itemloading 
                    WHERE fkitem = ? 
                        AND monthyear = ? 
                        AND fkproduct = ?
                '''
                db._execute(delete_query, (item_id, month, product_id))
                deleted_count += 1
            else:
                # Check if allocation exists
                check_query = '''
                    SELECT id, percent 
                    FROM itemloading 
                    WHERE fkitem = ? 
                        AND monthyear = ? 
                        AND fkproduct = ?
                '''
                existing = db._execute(check_query, (item_id, month, product_id)).fetchone()

                if existing:
                    # Update existing
                    if float(existing['percent']) != float(percent):
                        update_query = '''
                            UPDATE itemloading 
                            SET percent = ? 
                            WHERE id = ?
                        '''
                        db._execute(update_query, (float(percent), existing['id']))
                        updated_count += 1
                else:
                    # Insert new
                    insert_query = '''
                        INSERT INTO itemloading 
                        (fkitem, monthyear, percent, fkproduct, dailyrollupexists) 
                        VALUES (?, ?, ?, ?, 0)
                    '''
                    db._execute(insert_query, (item_id, month, float(percent), product_id))
                    saved_count += 1

        # Commit transaction
        db.con.commit()

        return jsonify({
            'success': True,
            'message': f'Saved {saved_count} new, updated {updated_count}, deleted {deleted_count} allocations',
            'saved': saved_count,
            'updated': updated_count,
            'deleted': deleted_count
        })

    except Exception as e:
        db.con.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.post('/<int:product_id>/get-characteristic-values')
def get_characteristic_values(product_id):
    """
    AJAX endpoint to get unique values for a characteristic key.
    Helps populate the characteristic value dropdown.
    """
    db = get_db()

    try:
        char_key = request.form.get('char_key', '').strip()

        if not char_key:
            return jsonify({'success': False, 'error': 'No key provided'}), 400

        query = '''
            SELECT DISTINCT itemvalue 
            FROM itemcharacteristics 
            WHERE itemkey = ? 
            ORDER BY itemvalue
        '''

        values = db._execute(query, (char_key,)).fetchall()

        values_list = [row['itemvalue'] for row in values]

        return jsonify({
            'success': True,
            'values': values_list
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500