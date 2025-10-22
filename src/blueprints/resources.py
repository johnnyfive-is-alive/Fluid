from flask import Blueprint, render_template, request, redirect, url_for, flash

bp = Blueprint('resources', __name__)


def get_db():
    """Get database connection for current request."""
    from app import get_db as app_get_db
    return app_get_db()


@bp.get('/')
def list_resources():
    """
    Display list of all resources with usage statistics.
    Shows how many products/loadings are associated with each resource.
    """
    db = get_db()

    # Get all resources with usage counts
    resources_query = '''
        SELECT 
            i.id, 
            i.itemname,
            COUNT(DISTINCT ipm.fkproduct) as mapped_products,
            COUNT(DISTINCT il.id) as loading_count
        FROM items i
        JOIN itemtypes it ON i.fkitemtype = it.id
        LEFT JOIN item_product_map ipm ON i.id = ipm.fkitem
        LEFT JOIN itemloading il ON i.id = il.fkitem
        WHERE it.typename = 'RESOURCE'
        GROUP BY i.id, i.itemname
        ORDER BY i.itemname
    '''
    resources = db._execute(resources_query).fetchall()

    return render_template('resources_list.html', resources=resources)


@bp.get('/add')
def add_form():
    """Display form to add a new resource."""
    return render_template('resources_add.html')


@bp.post('/add')
def add_resource():
    """
    Process form submission to add a new resource.
    Creates an item with type RESOURCE.
    """
    db = get_db()

    try:
        # Get form data
        resourcename = request.form['resourcename'].strip()

        # Validate resource name
        if not resourcename:
            flash('Resource name is required.', 'warning')
            return redirect(url_for('resources.add_form'))

        # Check if resource already exists
        existing = db.get_item_by_name(resourcename)
        if existing:
            flash(f'Resource "{resourcename}" already exists.', 'warning')
            return redirect(url_for('resources.add_form'))

        # Get or create RESOURCE type
        resource_type_id = db.get_itemtype_id_by_typename('RESOURCE')
        if not resource_type_id:
            resource_type_id = db.add_itemtype('RESOURCE')

        # Add the resource
        resource_id = db.add_item(resourcename, resource_type_id)
        db.con.commit()

        flash(f'Resource "{resourcename}" added successfully with ID {resource_id}.', 'success')
        return redirect(url_for('resources.list_resources'))

    except Exception as e:
        db.con.rollback()
        flash(f'Error adding resource: {e}', 'danger')

    return redirect(url_for('resources.add_form'))


@bp.get('/edit/<int:id>')
def edit_form(id):
    """
    Display form to edit an existing resource.
    Shows current name pre-filled.
    """
    db = get_db()

    # Get the resource
    resource = db.get_item_by_id(id)
    if not resource:
        flash('Resource not found.', 'danger')
        return redirect(url_for('resources.list_resources'))

    return render_template('resources_edit.html', resource=resource)


@bp.post('/edit/<int:id>')
def edit_resource(id):
    """
    Process form submission to update an existing resource.
    Validates new name for uniqueness.
    """
    db = get_db()

    try:
        # Get form data
        resourcename = request.form['resourcename'].strip()

        # Validate resource name
        if not resourcename:
            flash('Resource name is required.', 'warning')
            return redirect(url_for('resources.edit_form', id=id))

        # Check if name is being changed and new name exists
        current_resource = db.get_item_by_id(id)
        if current_resource['itemname'] != resourcename:
            existing = db.get_item_by_name(resourcename)
            if existing:
                flash(f'Resource "{resourcename}" already exists.', 'warning')
                return redirect(url_for('resources.edit_form', id=id))

        # Update the resource
        db.update_item(id, resourcename, current_resource['fkitemtype'])
        db.con.commit()

        flash(f'Resource "{resourcename}" updated successfully.', 'success')
        return redirect(url_for('resources.list_resources'))

    except Exception as e:
        db.con.rollback()
        flash(f'Error updating resource: {e}', 'danger')

    return redirect(url_for('resources.edit_form', id=id))


@bp.post('/delete/<int:id>')
def delete_resource(id):
    """
    Delete a resource.
    Checks if resource is in use before deletion.
    """
    db = get_db()

    try:
        # Get resource info
        resource = db.get_item_by_id(id)
        if not resource:
            flash('Resource not found.', 'danger')
            return redirect(url_for('resources.list_resources'))

        resourcename = resource['itemname']

        # Check if resource is in use
        usage_query = '''
            SELECT 
                COUNT(DISTINCT ipm.fkproduct) as mapped_products,
                COUNT(DISTINCT il.id) as loading_count
            FROM items i
            LEFT JOIN item_product_map ipm ON i.id = ipm.fkitem
            LEFT JOIN itemloading il ON i.id = il.fkitem
            WHERE i.id = ?
        '''
        usage = db._execute(usage_query, (id,)).fetchone()

        if usage['mapped_products'] > 0 or usage['loading_count'] > 0:
            flash(
                f'Cannot delete "{resourcename}": '
                f'{usage["mapped_products"]} product mapping(s) and '
                f'{usage["loading_count"]} loading record(s) exist.',
                'danger'
            )
            return redirect(url_for('resources.list_resources'))

        # Delete the resource
        db.delete_item(id)
        db.con.commit()

        flash(f'Resource "{resourcename}" deleted successfully.', 'success')

    except Exception as e:
        db.con.rollback()
        flash(f'Error deleting resource: {e}', 'danger')

    return redirect(url_for('resources.list_resources'))


@bp.get('/usage/<int:id>')
def view_usage(id):
    """
    View which products this resource is working on.
    Shows the resource-product relationships and detailed loading statistics.
    """
    db = get_db()

    # Get resource info
    resource = db.get_item_by_id(id)
    if not resource:
        flash('Resource not found.', 'danger')
        return redirect(url_for('resources.list_resources'))

    # Get products that this resource has loading records for (actual usage)
    products_with_loading_query = '''
        SELECT DISTINCT 
            p.id, 
            p.itemname,
            COUNT(DISTINCT il.id) as loading_count
        FROM items p
        JOIN itemloading il ON p.id = il.fkproduct
        WHERE il.fkitem = ?
        GROUP BY p.id, p.itemname
        ORDER BY p.itemname
    '''
    mapped_products = db._execute(products_with_loading_query, (id,)).fetchall()

    # Get loading statistics with monthly breakdown
    loading_query = '''
        SELECT 
            COUNT(*) as total_records,
            SUM(percent) as total_percent,
            COUNT(DISTINCT monthyear) as month_count
        FROM itemloading
        WHERE fkitem = ?
    '''
    loading_stats = db._execute(loading_query, (id,)).fetchone()

    # Get detailed loading records for chart and table
    loading_details_query = '''
        SELECT 
            il.monthyear,
            CASE WHEN p.itemname IS NULL THEN 'UNALLOCATED' ELSE p.itemname END AS productname,
            il.percent
        FROM itemloading il
        LEFT JOIN items p ON il.fkproduct = p.id
        WHERE il.fkitem = ?
        ORDER BY il.monthyear, p.itemname
    '''
    loading_details_rows = db._execute(loading_details_query, (id,)).fetchall()

    # Convert Row objects to dictionaries for JSON serialization
    loading_details = [dict(row) for row in loading_details_rows]

    return render_template(
        'resources_usage.html',
        resource=resource,
        mapped_products=mapped_products,
        loading_stats=loading_stats,
        loading_details=loading_details
    )
