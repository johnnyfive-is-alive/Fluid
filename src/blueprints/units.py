from flask import Blueprint, render_template, request, redirect, url_for, flash

bp = Blueprint('units', __name__)


def get_db():
    """Get database connection for current request."""
    from app import get_db as app_get_db
    return app_get_db()


@bp.get('/')
def list_units():
    """
    Display list of all units with usage statistics.
    Shows how many products/loadings are associated with each unit.
    """
    db = get_db()

    # Get all units with usage counts
    units_query = '''
        SELECT 
            i.id, 
            i.itemname,
            COUNT(DISTINCT ipm.fkproduct) as mapped_products,
            COUNT(DISTINCT il.id) as loading_count
        FROM items i
        JOIN itemtypes it ON i.fkitemtype = it.id
        LEFT JOIN item_product_map ipm ON i.id = ipm.fkitem
        LEFT JOIN itemloading il ON i.id = il.fkitem
        WHERE it.typename = 'UNIT'
        GROUP BY i.id, i.itemname
        ORDER BY i.itemname
    '''
    units = db._execute(units_query).fetchall()

    return render_template('units_list.html', units=units)


@bp.get('/add')
def add_form():
    """Display form to add a new unit."""
    return render_template('units_add.html')


@bp.post('/add')
def add_unit():
    """
    Process form submission to add a new unit.
    Creates an item with type UNIT.
    """
    db = get_db()

    try:
        # Get form data
        unitname = request.form['unitname'].strip()

        # Validate unit name
        if not unitname:
            flash('Unit name is required.', 'warning')
            return redirect(url_for('units.add_form'))

        # Check if unit already exists
        existing = db.get_item_by_name(unitname)
        if existing:
            flash(f'Unit "{unitname}" already exists.', 'warning')
            return redirect(url_for('units.add_form'))

        # Get or create UNIT type
        unit_type_id = db.get_itemtype_id_by_typename('UNIT')
        if not unit_type_id:
            unit_type_id = db.add_itemtype('UNIT')

        # Add the unit
        unit_id = db.add_item(unitname, unit_type_id)
        db.con.commit()

        flash(f'Unit "{unitname}" added successfully with ID {unit_id}.', 'success')
        return redirect(url_for('units.list_units'))

    except Exception as e:
        db.con.rollback()
        flash(f'Error adding unit: {e}', 'danger')

    return redirect(url_for('units.add_form'))


@bp.get('/edit/<int:id>')
def edit_form(id):
    """
    Display form to edit an existing unit.
    Shows current name pre-filled.
    """
    db = get_db()

    # Get the unit
    unit = db.get_item_by_id(id)
    if not unit:
        flash('Unit not found.', 'danger')
        return redirect(url_for('units.list_units'))

    return render_template('units_edit.html', unit=unit)


@bp.post('/edit/<int:id>')
def edit_unit(id):
    """
    Process form submission to update an existing unit.
    Validates new name for uniqueness.
    """
    db = get_db()

    try:
        # Get form data
        unitname = request.form['unitname'].strip()

        # Validate unit name
        if not unitname:
            flash('Unit name is required.', 'warning')
            return redirect(url_for('units.edit_form', id=id))

        # Check if name is being changed and new name exists
        current_unit = db.get_item_by_id(id)
        if current_unit['itemname'] != unitname:
            existing = db.get_item_by_name(unitname)
            if existing:
                flash(f'Unit "{unitname}" already exists.', 'warning')
                return redirect(url_for('units.edit_form', id=id))

        # Update the unit
        db.update_item(id, unitname, current_unit['fkitemtype'])
        db.con.commit()

        flash(f'Unit "{unitname}" updated successfully.', 'success')
        return redirect(url_for('units.list_units'))

    except Exception as e:
        db.con.rollback()
        flash(f'Error updating unit: {e}', 'danger')

    return redirect(url_for('units.edit_form', id=id))


@bp.post('/delete/<int:id>')
def delete_unit(id):
    """
    Delete a unit.
    Checks if unit is in use before deletion.
    """
    db = get_db()

    try:
        # Get unit info
        unit = db.get_item_by_id(id)
        if not unit:
            flash('Unit not found.', 'danger')
            return redirect(url_for('units.list_units'))

        unitname = unit['itemname']

        # Check if unit is in use
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
                f'Cannot delete "{unitname}": '
                f'{usage["mapped_products"]} product mapping(s) and '
                f'{usage["loading_count"]} loading record(s) exist.',
                'danger'
            )
            return redirect(url_for('units.list_units'))

        # Delete the unit
        db.delete_item(id)
        db.con.commit()

        flash(f'Unit "{unitname}" deleted successfully.', 'success')

    except Exception as e:
        db.con.rollback()
        flash(f'Error deleting unit: {e}', 'danger')

    return redirect(url_for('units.list_units'))


@bp.get('/usage/<int:id>')
def view_usage(id):
    """
    View which products this unit is working on.
    Shows the unit-product relationships and detailed loading statistics.
    """
    db = get_db()

    # Get unit info
    unit = db.get_item_by_id(id)
    if not unit:
        flash('Unit not found.', 'danger')
        return redirect(url_for('units.list_units'))

    # Get products that this unit has loading records for (actual usage)
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
        'units_usage.html',
        unit=unit,
        mapped_products=mapped_products,
        loading_stats=loading_stats,
        loading_details=loading_details
    )