from flask import Blueprint, render_template, request, redirect, url_for, flash

bp = Blueprint('stations', __name__)


def get_db():
    """Get database connection for current request."""
    from app import get_db as app_get_db
    return app_get_db()


@bp.get('/')
def list_stations():
    """
    Display list of all stations with usage statistics.
    Shows how many products/loadings are associated with each station.
    """
    db = get_db()

    # Get all stations with usage counts
    stations_query = '''
        SELECT 
            i.id, 
            i.itemname,
            COUNT(DISTINCT ipm.fkproduct) as mapped_products,
            COUNT(DISTINCT il.id) as loading_count
        FROM items i
        JOIN itemtypes it ON i.fkitemtype = it.id
        LEFT JOIN item_product_map ipm ON i.id = ipm.fkitem
        LEFT JOIN itemloading il ON i.id = il.fkitem
        WHERE it.typename = 'STATION'
        GROUP BY i.id, i.itemname
        ORDER BY i.itemname
    '''
    stations = db._execute(stations_query).fetchall()

    return render_template('stations_list.html', stations=stations)


@bp.get('/add')
def add_form():
    """Display form to add a new station."""
    return render_template('stations_add.html')


@bp.post('/add')
def add_station():
    """
    Process form submission to add a new station.
    Creates an item with type STATION.
    """
    db = get_db()

    try:
        # Get form data - stations should be uppercase
        stationname = request.form['stationname'].strip().upper()

        # Validate station name
        if not stationname:
            flash('Station name is required.', 'warning')
            return redirect(url_for('stations.add_form'))

        # Check if station already exists
        existing = db.get_item_by_name(stationname)
        if existing:
            flash(f'Station "{stationname}" already exists.', 'warning')
            return redirect(url_for('stations.add_form'))

        # Get or create STATION type
        station_type_id = db.get_itemtype_id_by_typename('STATION')
        if not station_type_id:
            station_type_id = db.add_itemtype('STATION')

        # Add the station
        station_id = db.add_item(stationname, station_type_id)
        db.con.commit()

        flash(f'Station "{stationname}" added successfully with ID {station_id}.', 'success')
        return redirect(url_for('stations.list_stations'))

    except Exception as e:
        db.con.rollback()
        flash(f'Error adding station: {e}', 'danger')

    return redirect(url_for('stations.add_form'))


@bp.get('/edit/<int:id>')
def edit_form(id):
    """
    Display form to edit an existing station.
    Shows current name pre-filled.
    """
    db = get_db()

    # Get the station
    station = db.get_item_by_id(id)
    if not station:
        flash('Station not found.', 'danger')
        return redirect(url_for('stations.list_stations'))

    return render_template('stations_edit.html', station=station)


@bp.post('/edit/<int:id>')
def edit_station(id):
    """
    Process form submission to update an existing station.
    Validates new name for uniqueness.
    """
    db = get_db()

    try:
        # Get form data - stations should be uppercase
        stationname = request.form['stationname'].strip().upper()

        # Validate station name
        if not stationname:
            flash('Station name is required.', 'warning')
            return redirect(url_for('stations.edit_form', id=id))

        # Check if name is being changed and new name exists
        current_station = db.get_item_by_id(id)
        if current_station['itemname'] != stationname:
            existing = db.get_item_by_name(stationname)
            if existing:
                flash(f'Station "{stationname}" already exists.', 'warning')
                return redirect(url_for('stations.edit_form', id=id))

        # Update the station
        db.update_item(id, stationname, current_station['fkitemtype'])
        db.con.commit()

        flash(f'Station "{stationname}" updated successfully.', 'success')
        return redirect(url_for('stations.list_stations'))

    except Exception as e:
        db.con.rollback()
        flash(f'Error updating station: {e}', 'danger')

    return redirect(url_for('stations.edit_form', id=id))


@bp.post('/delete/<int:id>')
def delete_station(id):
    """
    Delete a station.
    Checks if station is in use before deletion.
    """
    db = get_db()

    try:
        # Get station info
        station = db.get_item_by_id(id)
        if not station:
            flash('Station not found.', 'danger')
            return redirect(url_for('stations.list_stations'))

        stationname = station['itemname']

        # Check if station is in use
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
                f'Cannot delete "{stationname}": '
                f'{usage["mapped_products"]} product mapping(s) and '
                f'{usage["loading_count"]} loading record(s) exist.',
                'danger'
            )
            return redirect(url_for('stations.list_stations'))

        # Delete the station
        db.delete_item(id)
        db.con.commit()

        flash(f'Station "{stationname}" deleted successfully.', 'success')

    except Exception as e:
        db.con.rollback()
        flash(f'Error deleting station: {e}', 'danger')

    return redirect(url_for('stations.list_stations'))


@bp.get('/usage/<int:id>')
def view_usage(id):
    """
    View which products this station is working on.
    Shows the station-product relationships and detailed loading statistics.
    """
    db = get_db()

    # Get station info
    station = db.get_item_by_id(id)
    if not station:
        flash('Station not found.', 'danger')
        return redirect(url_for('stations.list_stations'))

    # Get products that this station has loading records for (actual usage)
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
        'stations_usage.html',
        station=station,
        mapped_products=mapped_products,
        loading_stats=loading_stats,
        loading_details=loading_details
    )
