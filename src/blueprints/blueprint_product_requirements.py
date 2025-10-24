"""
Product Requirements Blueprint
Allows defining specific item requirements for products month-to-month.

NOMENCLATURE:
- productrequirements table = What specific items are REQUIRED/PLANNED for products
- itemloading table = What specific items are actually ALLOCATED/ASSIGNED to products

This creates a "requirements profile" that can be compared against actual item allocations
to identify gaps and overallocations.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime

bp = Blueprint('product_requirements', __name__, url_prefix='/product-requirements')


def get_db():
    """Get database connection for current request."""
    from app import get_db as app_get_db
    return app_get_db()


@bp.get('/view/<int:product_id>')
def view_product_requirements(product_id):
    """
    View product requirements profile.
    Shows month-by-month specific item requirements.
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

    # Get product requirements for this product
    product_requirements = db.list_product_requirements_for_product(product_id)

    # Organize by month
    monthly_data = {}
    sorted_months = []

    for requirement in product_requirements:
        month = requirement['monthyear']
        if month not in monthly_data:
            monthly_data[month] = []
            sorted_months.append(month)
        monthly_data[month].append(requirement)

    sorted_months.sort()

    return render_template(
        'product_requirements_view.html',
        product=product,
        monthly_data=monthly_data,
        sorted_months=sorted_months
    )


@bp.get('/edit/<int:product_id>')
def edit_form(product_id):
    """
    Display form to edit product requirements.
    Allows setting percentage requirements for specific items by month.
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

    # Get all non-product item types
    all_itemtypes = db.list_itemtypes()
    item_types = [it for it in all_itemtypes if it['typename'] != 'PRODUCT']

    # Get month range - default to current year
    current_year = datetime.now().year
    all_months = [f"{current_year}-{str(m).zfill(2)}" for m in range(1, 13)]

    # Get existing requirements for this product
    existing_requirements = db.list_product_requirements_for_product(product_id)

    # Organize by month and item
    requirements_matrix = {}
    for req in existing_requirements:
        month = req['monthyear']
        item_id = req['fkitem']
        if month not in requirements_matrix:
            requirements_matrix[month] = {}
        requirements_matrix[month][item_id] = {
            'percent': req['percent'],
            'notes': req['notes']
        }

    return render_template(
        'product_requirements_edit.html',
        product=product,
        item_types=item_types,
        all_months=all_months,
        requirements_matrix=requirements_matrix
    )


@bp.post('/save/<int:product_id>')
def save_requirements(product_id):
    """
    Save product requirements for specific items.
    Expects form data with structure: requirements[month][item_id] = percent
    """
    db = get_db()

    try:
        # Get product
        product = db.get_item_by_id(product_id)
        if not product:
            flash('Product not found.', 'danger')
            return redirect(url_for('products.list_products'))

        # Parse form data
        # Expected format: requirements[2025-01][item_5] = 50.0
        updates_made = 0
        deletes_made = 0

        for key, value in request.form.items():
            if not key.startswith('requirements['):
                continue

            # Parse: requirements[2025-01][item_5]
            try:
                parts = key.replace('requirements[', '').replace(']', '').split('[')
                month = parts[0]
                item_str = parts[1].replace('item_', '')
                item_id = int(item_str)

                # Get notes if provided
                notes_key = f'notes[{month}][item_{item_id}]'
                notes = request.form.get(notes_key, '').strip() or None

                if value and value.strip():
                    # Has a value - upsert
                    try:
                        percent = float(value)
                        db.upsert_product_requirement(
                            fkproduct=product_id,
                            fkitem=item_id,
                            monthyear=month,
                            percent=percent,
                            notes=notes
                        )
                        updates_made += 1
                    except ValueError:
                        flash(f'Invalid percentage value for item {item_id} in {month}: "{value}"', 'warning')
                else:
                    # Empty value - delete the requirement if it exists
                    existing_ids = db.find_product_requirement_ids(
                        fkproduct=product_id,
                        fkitem=item_id,
                        monthyear=month
                    )

                    for existing_id in existing_ids:
                        db.delete_product_requirement(existing_id)
                        deletes_made += 1

            except (ValueError, IndexError) as e:
                flash(f'Error parsing {key}: {e}', 'warning')
                continue

        # Commit all changes
        db.con.commit()

        # Success message
        if updates_made > 0 or deletes_made > 0:
            flash(
                f'Product requirements updated: {updates_made} saved, {deletes_made} removed.',
                'success'
            )
        else:
            flash('No changes made.', 'info')

        return redirect(url_for('product_requirements.view_product_requirements', product_id=product_id))

    except Exception as e:
        db.con.rollback()
        flash(f'Error saving product requirements: {e}', 'danger')
        return redirect(url_for('product_requirements.edit_form', product_id=product_id))


@bp.get('/<int:product_id>')
def enhanced_requirements_interface(product_id):
    """
    Enhanced interface for defining specific item requirements for a product.
    Allows filtering items by type and characteristics, then setting percentage requirements.
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

    # Get existing requirements for this product (from productrequirements table)
    existing_requirements_query = '''
        SELECT 
            pr.id,
            pr.fkitem,
            i.itemname,
            it.typename,
            pr.monthyear,
            pr.percent
        FROM productrequirements pr
        JOIN items i ON pr.fkitem = i.id
        JOIN itemtypes it ON i.fkitemtype = it.id
        WHERE pr.fkproduct = ?
        ORDER BY pr.monthyear, i.itemname
    '''
    existing_requirements = db._execute(existing_requirements_query, (product_id,)).fetchall()

    return render_template(
        'product_requirements_enhanced.html',
        product=product,
        item_types=item_types,
        char_keys=char_keys,
        default_months=default_months,
        existing_requirements=existing_requirements
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


@bp.get('/<int:product_id>/get-item-characteristics/<int:item_id>')
def get_item_characteristics(product_id, item_id):
    """
    AJAX endpoint to get characteristics for a specific item.
    Returns JSON list of characteristics.
    """
    db = get_db()

    try:
        # Get characteristics for this item
        query = '''
            SELECT itemkey, itemvalue
            FROM itemcharacteristics
            WHERE fkitem = ?
            ORDER BY itemkey
        '''

        results = db._execute(query, (item_id,)).fetchall()

        # Convert to JSON-serializable format
        characteristics = [
            {
                'itemkey': row['itemkey'],
                'itemvalue': row['itemvalue']
            }
            for row in results
        ]

        return jsonify({
            'success': True,
            'characteristics': characteristics,
            'count': len(characteristics)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.post('/<int:product_id>/get-requirements')
def get_requirements(product_id):
    """
    AJAX endpoint to get existing requirements for selected items and month.
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

        # Get existing requirements from productrequirements table
        placeholders = ','.join(['?'] * len(item_ids))
        query = f'''
            SELECT fkitem, percent
            FROM productrequirements
            WHERE fkproduct = ?
            AND monthyear = ?
            AND fkitem IN ({placeholders})
        '''

        params = [product_id, month] + [int(id) for id in item_ids]
        results = db._execute(query, tuple(params)).fetchall()

        # Convert to dict
        requirements = {row['fkitem']: row['percent'] for row in results}

        return jsonify({
            'success': True,
            'requirements': requirements
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.post('/<int:product_id>/save-requirements')
def save_requirements_ajax(product_id):
    """
    Save requirement percentages for items to this product.
    This updates the productrequirements table (what's REQUIRED/PLANNED).
    """
    db = get_db()

    try:
        data = request.get_json()
        requirements = data if isinstance(data, list) else data.get('requirements', [])

        if not requirements:
            return jsonify({
                'success': False,
                'error': 'No requirements provided'
            }), 400

        # Process each requirement
        saved_count = 0
        deleted_count = 0

        for req in requirements:
            item_id = req.get('item_id')
            month = req.get('month')
            percent = req.get('percent')

            if item_id is None or not month:
                continue

            # Validate percent
            try:
                percent = float(percent) if percent else 0
                if percent < 0:
                    percent = 0
                if percent > 100:
                    percent = 100
            except (ValueError, TypeError):
                percent = 0

            # If percent is 0, delete the entry
            if percent == 0:
                # Check if exists and delete
                cur = db._execute(
                    '''SELECT id FROM productrequirements 
                       WHERE fkitem = ? AND monthyear = ? AND fkproduct = ?''',
                    (item_id, month, product_id)
                )
                existing = cur.fetchone()
                if existing:
                    db.delete_product_requirement(existing['id'])
                    deleted_count += 1
            else:
                # Upsert the requirement
                db.upsert_product_requirement(
                    fkproduct=product_id,
                    fkitem=item_id,
                    monthyear=month,
                    percent=percent,
                    notes=None
                )
                saved_count += 1

        db.con.commit()

        return jsonify({
            'success': True,
            'message': f'Successfully saved {saved_count} requirement(s) and removed {deleted_count} requirement(s).',
            'saved_count': saved_count,
            'deleted_count': deleted_count
        })

    except Exception as e:
        db.con.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.get('/compare/<int:product_id>/<monthyear>')
def compare_requirements_vs_allocations(product_id, monthyear):
    """
    Compare requirements (planned) vs allocations (actual) for a product in a month.
    Shows gaps and excess allocations.
    """
    db = get_db()

    # Get product
    product = db.get_item_by_id(product_id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('products.list_products'))

    # Get comparison data
    comparison = db.compare_requirements_vs_allocations(product_id, monthyear)

    return render_template(
        'product_requirements_comparison.html',
        product=product,
        monthyear=monthyear,
        comparison=comparison
    )