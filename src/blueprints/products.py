from flask import Blueprint, render_template, request, redirect, url_for, flash

bp = Blueprint('products', __name__)


def get_db():
    """Get database connection for current request."""
    from app import get_db as app_get_db
    return app_get_db()


@bp.get('/')
def list_products():
    """
    Display list of all products with usage statistics.
    Shows how many items/loadings are associated with each product.
    """
    db = get_db()

    # Get all products with usage counts
    products_query = '''
        SELECT 
            i.id, 
            i.itemname,
            COUNT(DISTINCT ipm.fkitem) as mapped_items,
            COUNT(DISTINCT il.id) as loading_count
        FROM items i
        JOIN itemtypes it ON i.fkitemtype = it.id
        LEFT JOIN item_product_map ipm ON i.id = ipm.fkproduct
        LEFT JOIN itemloading il ON i.id = il.fkproduct
        WHERE it.typename = 'PRODUCT'
        GROUP BY i.id, i.itemname
        ORDER BY i.itemname
    '''
    products = db._execute(products_query).fetchall()

    return render_template('products_list.html', products=products)


@bp.get('/add')
def add_form():
    """Display form to add a new product."""
    return render_template('products_add.html')


@bp.post('/add')
def add_product():
    """
    Process form submission to add a new product.
    Creates an item with type PRODUCT.
    """
    db = get_db()

    try:
        # Get form data
        productname = request.form['productname'].strip().upper()

        # Validate product name
        if not productname:
            flash('Product name is required.', 'warning')
            return redirect(url_for('products.add_form'))

        # Check if product already exists
        existing = db.get_item_by_name(productname)
        if existing:
            flash(f'Product "{productname}" already exists.', 'warning')
            return redirect(url_for('products.add_form'))

        # Get or create PRODUCT type
        product_type_id = db.get_itemtype_id_by_typename('PRODUCT')
        if not product_type_id:
            product_type_id = db.add_itemtype('PRODUCT')

        # Add the product
        product_id = db.add_item(productname, product_type_id)
        db.con.commit()

        flash(f'Product "{productname}" added successfully with ID {product_id}.', 'success')
        return redirect(url_for('products.list_products'))

    except Exception as e:
        db.con.rollback()
        flash(f'Error adding product: {e}', 'danger')

    return redirect(url_for('products.add_form'))


@bp.get('/edit/<int:id>')
def edit_form(id):
    """
    Display form to edit an existing product.
    Shows current name pre-filled.
    """
    db = get_db()

    # Get the product
    product = db.get_item_by_id(id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('products.list_products'))

    # Verify it's actually a product
    itemtype = db.get_itemtype_by_id(product['fkitemtype'])
    if not itemtype or itemtype['typename'] != 'PRODUCT':
        flash('This item is not a product.', 'danger')
        return redirect(url_for('products.list_products'))

    return render_template('products_edit.html', product=product)


@bp.post('/edit/<int:id>')
def edit_product(id):
    """
    Process form submission to update an existing product.
    Only allows changing the name.
    """
    db = get_db()

    try:
        # Get form data
        productname = request.form['productname'].strip().upper()

        # Validate
        if not productname:
            flash('Product name is required.', 'warning')
            return redirect(url_for('products.edit_form', id=id))

        # Check for conflicts
        existing = db.get_item_by_name(productname)
        if existing and existing['id'] != id:
            flash(f'Another product with name "{productname}" already exists.', 'warning')
            return redirect(url_for('products.edit_form', id=id))

        # Update the product
        db.update_item(id, itemname=productname)
        db.con.commit()

        flash(f'Product updated to "{productname}" successfully.', 'success')
        return redirect(url_for('products.list_products'))

    except Exception as e:
        db.con.rollback()
        flash(f'Error updating product: {e}', 'danger')

    return redirect(url_for('products.edit_form', id=id))


@bp.post('/delete/<int:id>')
def delete_product(id):
    """
    Delete a product from the database.
    Checks if product is in use before deletion.
    """
    db = get_db()

    try:
        # Get product info
        product = db.get_item_by_id(id)
        if not product:
            flash('Product not found.', 'danger')
            return redirect(url_for('products.list_products'))

        productname = product['itemname']

        # Prevent deletion of UNALLOCATED
        if productname == 'UNALLOCATED':
            flash('Cannot delete the UNALLOCATED product (system reserved).', 'danger')
            return redirect(url_for('products.list_products'))

        # Check if product is in use
        usage_query = '''
            SELECT 
                COUNT(DISTINCT ipm.fkitem) as mapped_items,
                COUNT(DISTINCT il.id) as loading_count
            FROM items i
            LEFT JOIN item_product_map ipm ON i.id = ipm.fkproduct
            LEFT JOIN itemloading il ON i.id = il.fkproduct
            WHERE i.id = ?
        '''
        usage = db._execute(usage_query, (id,)).fetchone()

        if usage['mapped_items'] > 0 or usage['loading_count'] > 0:
            flash(
                f'Cannot delete "{productname}": '
                f'{usage["mapped_items"]} item mapping(s) and '
                f'{usage["loading_count"]} loading record(s) exist.',
                'danger'
            )
            return redirect(url_for('products.list_products'))

        # Delete the product
        db.delete_item(id)
        db.con.commit()

        flash(f'Product "{productname}" deleted successfully.', 'success')

    except Exception as e:
        db.con.rollback()
        flash(f'Error deleting product: {e}', 'danger')

    return redirect(url_for('products.list_products'))


@bp.get('/mappings/<int:id>')
def view_mappings(id):
    """
    View which items are using this product (either through explicit mappings or loading records).
    Shows the item-product relationships and detailed loading statistics.
    """
    db = get_db()

    # Get product info
    product = db.get_item_by_id(id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('products.list_products'))

    # Get items that have loading records for this product (actual usage)
    items_with_loading_query = '''
        SELECT DISTINCT 
            i.id, 
            i.itemname,
            it.typename,
            COUNT(DISTINCT il.id) as loading_count
        FROM items i
        JOIN itemtypes it ON i.fkitemtype = it.id
        JOIN itemloading il ON i.id = il.fkitem
        WHERE il.fkproduct = ? OR (il.fkproduct IS NULL AND ? IS NULL)
        GROUP BY i.id, i.itemname, it.typename
        ORDER BY i.itemname
    '''
    # Handle UNALLOCATED (NULL) vs explicit product IDs
    product_id_param = id if product['itemname'] != 'UNALLOCATED' else None
    mapped_items = db._execute(items_with_loading_query, (product_id_param, product_id_param)).fetchall()

    # Get loading statistics with monthly breakdown
    loading_query = '''
        SELECT 
            COUNT(*) as total_records,
            SUM(percent) as total_percent,
            COUNT(DISTINCT monthyear) as month_count
        FROM itemloading
        WHERE fkproduct = ? OR (fkproduct IS NULL AND ? IS NULL)
    '''
    loading_stats = db._execute(loading_query, (product_id_param, product_id_param)).fetchone()

    # Get detailed loading records for chart and table
    loading_details_query = '''
        SELECT 
            il.monthyear,
            i.itemname,
            il.percent
        FROM itemloading il
        JOIN items i ON il.fkitem = i.id
        WHERE il.fkproduct = ? OR (il.fkproduct IS NULL AND ? IS NULL)
        ORDER BY il.monthyear, i.itemname
    '''
    loading_details_rows = db._execute(loading_details_query, (product_id_param, product_id_param)).fetchall()

    # Convert Row objects to dictionaries for JSON serialization
    loading_details = [dict(row) for row in loading_details_rows]

    return render_template(
        'products_mappings.html',
        product=product,
        mapped_items=mapped_items,
        loading_stats=loading_stats,
        loading_details=loading_details
    )


@bp.get('/map/<int:product_id>')
def map_form(product_id):
    """
    Display form to map items to a product.
    Shows which items can work with this product.
    """
    db = get_db()

    # Get product
    product = db.get_item_by_id(product_id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('products.list_products'))

    # Get all non-product items
    all_items_query = '''
        SELECT i.*, it.typename
        FROM items i
        JOIN itemtypes it ON i.fkitemtype = it.id
        WHERE it.typename != 'PRODUCT'
        ORDER BY i.itemname
    '''
    all_items = db._execute(all_items_query).fetchall()

    # Get currently mapped items
    mapped_items = db.get_items_for_product(product_id)
    mapped_ids = [item['id'] for item in mapped_items]

    return render_template(
        'products_map.html',
        product=product,
        all_items=all_items,
        mapped_ids=mapped_ids
    )


@bp.post('/map/<int:product_id>')
def save_mappings(product_id):
    """
    Save item-product mappings.
    Updates which items can use this product.
    """
    db = get_db()

    try:
        # Get selected item IDs
        selected_items = request.form.getlist('mapped_items')
        selected_ids = [int(id) for id in selected_items]

        # Get current mappings
        current_mapped = db.get_items_for_product(product_id)
        current_ids = [item['id'] for item in current_mapped]

        # Add new mappings
        for item_id in selected_ids:
            if item_id not in current_ids:
                db.add_item_product_mapping(item_id, product_id)

        # Remove old mappings
        for item_id in current_ids:
            if item_id not in selected_ids:
                db.remove_item_product_mapping(item_id, product_id)

        db.con.commit()
        flash('Product mappings updated successfully.', 'success')

    except Exception as e:
        db.con.rollback()
        flash(f'Error updating mappings: {e}', 'danger')

    return redirect(url_for('products.view_mappings', id=product_id))