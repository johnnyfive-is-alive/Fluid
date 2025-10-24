"""
Product Loading Requirements Blueprint
Allows defining resource requirements (by item type) for products month-to-month.
This creates a "requirements profile" that can be compared against actual item allocations.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime

bp = Blueprint('product_loading', __name__, url_prefix='/product-loading')


def get_db():
    """Get database connection for current request."""
    from app import get_db as app_get_db
    return app_get_db()


@bp.get('/view/<int:product_id>')
def view_product_loading(product_id):
    """
    View product loading requirements profile.
    Shows month-by-month resource type requirements (STATION, RESOURCE, UNIT percentages).
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

    # Get product loading requirements for this product
    product_loadings = db.list_product_loadings_for_product(product_id)

    # Organize by month
    monthly_data = {}
    sorted_months = []

    for loading in product_loadings:
        month = loading['monthyear']
        if month not in monthly_data:
            monthly_data[month] = []
            sorted_months.append(month)
        monthly_data[month].append(loading)

    sorted_months.sort()

    return render_template(
        'product_loading_view.html',
        product=product,
        monthly_data=monthly_data,
        sorted_months=sorted_months
    )


@bp.get('/edit/<int:product_id>')
def edit_form(product_id):
    """
    Display form to edit product loading requirements.
    Allows setting percentage requirements for each resource type by month.
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

    # Get existing product loading requirements
    product_loadings = db.list_product_loadings_for_product(product_id)

    # Build a matrix: loading_matrix[month][typename] = {percent, notes, id}
    loading_matrix = {}
    all_months = set()

    for loading in product_loadings:
        month = loading['monthyear']
        typename = loading['typename']

        if month not in loading_matrix:
            loading_matrix[month] = {}

        loading_matrix[month][typename] = {
            'id': loading['id'],
            'percent': loading['percent'],  # Changed from quantity to percent
            'notes': loading['notes']
        }
        all_months.add(month)

    # Sort months
    all_months = sorted(all_months) if all_months else []

    return render_template(
        'product_loading_edit.html',
        product=product,
        item_types=item_types,
        loading_matrix=loading_matrix,
        all_months=all_months
    )


@bp.post('/api/generate-months')
def api_generate_months():
    """
    API endpoint to generate a list of months between start and end dates.
    Returns JSON array of months in YYYY-MM format.
    """
    try:
        data = request.get_json()
        start_month = data.get('start_month', '')
        end_month = data.get('end_month', '')

        if not start_month or not end_month:
            return jsonify({
                'success': False,
                'error': 'Missing start_month or end_month'
            }), 400

        # Use database's generate_month_range method
        db = get_db()
        months = db.generate_month_range(start_month, end_month)

        if not months:
            return jsonify({
                'success': False,
                'error': 'Invalid date range'
            }), 400

        return jsonify({
            'success': True,
            'months': months
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.post('/save/<int:product_id>')
def save_loading(product_id):
    """
    Save product loading requirements from the edit form.
    Processes all percentage inputs and notes for each month/resource type combination.
    """
    db = get_db()

    try:
        # Get product
        product = db.get_item_by_id(product_id)
        if not product:
            flash('Product not found.', 'danger')
            return redirect(url_for('products.list_products'))

        # Get all item types
        all_itemtypes = db.list_itemtypes()
        item_types = [it for it in all_itemtypes if it['typename'] != 'PRODUCT']

        # Parse form data: loading[YYYY-MM][TYPENAME] = percent
        #                  notes[YYYY-MM][TYPENAME] = text
        updates_made = 0
        deletes_made = 0

        # Get all form keys to find months and types
        months_in_form = set()
        for key in request.form.keys():
            if key.startswith('loading['):
                # Extract month from loading[2025-01][STATION]
                month_start = key.index('[') + 1
                month_end = key.index(']')
                month = key[month_start:month_end]
                months_in_form.add(month)

        # Process each month/typename combination
        for month in months_in_form:
            for itemtype in item_types:
                typename = itemtype['typename']
                itemtype_id = itemtype['id']

                # Get form values
                loading_key = f'loading[{month}][{typename}]'
                notes_key = f'notes[{month}][{typename}]'

                percent_str = request.form.get(loading_key, '').strip()
                notes = request.form.get(notes_key, '').strip()

                # Convert percent to float
                if percent_str:
                    try:
                        percent = float(percent_str)

                        # Validate
                        if percent < 0:
                            flash(f'Warning: Negative percentage for {typename} in {month} set to 0', 'warning')
                            percent = 0

                        # Upsert the loading requirement
                        db.upsert_product_loading(
                            fkproduct=product_id,
                            fkitemtype=itemtype_id,
                            monthyear=month,
                            percent=percent,  # Changed from quantity to percent
                            notes=notes if notes else None
                        )
                        updates_made += 1

                    except ValueError:
                        flash(f'Invalid percentage value for {typename} in {month}: "{percent_str}"', 'warning')
                else:
                    # Empty value - delete the requirement if it exists
                    existing_ids = db.find_product_loading_ids(
                        fkproduct=product_id,
                        fkitemtype=itemtype_id,
                        monthyear=month
                    )

                    for existing_id in existing_ids:
                        db.delete_product_loading(existing_id)
                        deletes_made += 1

        # Commit all changes
        db.con.commit()

        # Success message
        if updates_made > 0 or deletes_made > 0:
            flash(
                f'Product loading requirements updated: {updates_made} saved, {deletes_made} removed.',
                'success'
            )
        else:
            flash('No changes made.', 'info')

        return redirect(url_for('product_loading.view_product_loading', product_id=product_id))

    except Exception as e:
        db.con.rollback()
        flash(f'Error saving product loading requirements: {e}', 'danger')
        return redirect(url_for('product_loading.edit_form', product_id=product_id))


@bp.get('/<int:product_id>')
def enhanced_allocation_interface(product_id):
    """
    Enhanced interface for allocating specific items to a product.
    Allows filtering items by type and characteristics, then setting percentage allocations.
    This is DIFFERENT from product loading requirements - this assigns actual items.
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

    # Get existing allocations for this product (from itemloading table)
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
        month = request.form.get('month')
        item_ids = request.form.getlist('item_ids[]')

        if not month or not item_ids:
            return jsonify({
                'success': False,
                'error': 'Missing month or item_ids'
            }), 400

        # Get existing allocations from itemloading table
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
    This updates the itemloading table (actual item assignments), not product loading requirements.
    """
    db = get_db()

    try:
        data = request.get_json()
        allocations = data.get('allocations', [])

        if not allocations:
            return jsonify({
                'success': False,
                'error': 'No allocations provided'
            }), 400

        # Process each allocation
        saved_count = 0
        for alloc in allocations:
            item_id = alloc.get('item_id')
            month = alloc.get('month')
            percent = alloc.get('percent')

            if item_id is None or not month or percent is None:
                continue

            # Validate percent
            try:
                percent = float(percent)
                if percent < 0:
                    percent = 0
                if percent > 100:
                    percent = 100
            except (ValueError, TypeError):
                continue

            # Upsert the loading (from itemloading table)
            db.upsert_item_loading(
                fkitem=item_id,
                monthyear=month,
                percent=percent,
                fkproduct=product_id
            )
            saved_count += 1

        db.con.commit()

        return jsonify({
            'success': True,
            'saved_count': saved_count
        })

    except Exception as e:
        db.con.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500