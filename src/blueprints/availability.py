from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import json

bp = Blueprint('availability', __name__)


def get_db():
    """Get database connection for current request."""
    from app import get_db as app_get_db
    return app_get_db()


@bp.get('/')
def analytics():
    """
    Display availability analytics page with filters for:
    - ItemType selection
    - Characteristic filters
    - Date range
    Shows unassigned/available capacity for filtered items.
    """
    db = get_db()

    # Get all item types
    itemtypes = db.list_itemtypes()

    # Get all unique characteristic keys
    char_keys_query = '''
        SELECT DISTINCT itemkey 
        FROM itemcharacteristics 
        ORDER BY itemkey
    '''
    char_keys = db._execute(char_keys_query).fetchall()

    # Set default date range (current year)
    current_year = datetime.now().year
    current_month = datetime.now().month
    start_month = f"{current_year}-{current_month:02d}"
    end_month = f"{current_year}-12"

    return render_template(
        'availability_analytics.html',
        itemtypes=itemtypes,
        char_keys=char_keys,
        start_month=start_month,
        end_month=end_month
    )


@bp.post('/query')
def query_availability():
    """
    Process availability query with filters and return JSON data for visualization.
    Calculates: Available % = 100% - (Sum of all product allocations)
    """
    db = get_db()

    try:
        # Get filter parameters
        itemtype_id = request.form.get('itemtype_id', type=int)
        char_key = request.form.get('char_key', '').strip()
        char_value = request.form.get('char_value', '').strip()
        itemname_filter = request.form.get('itemname_filter', '').strip()
        start_month = request.form.get('start_month', '')
        end_month = request.form.get('end_month', '')

        # Build SQL query with filters
        query_parts = []
        params = []

        # Generate month range
        if start_month and end_month:
            month_range = db.generate_month_range(start_month, end_month)
            if not month_range:
                return jsonify({'error': 'Invalid date range'}), 400
        else:
            return jsonify({'error': 'Date range required'}), 400

        # Build query without VALUES clause (SQLite compatible)
        # We'll get items first, then calculate for each month
        query = '''
            SELECT 
                i.id,
                i.itemname,
                it.typename,
                il.monthyear,
                COALESCE(SUM(il.percent), 0) as allocated_percent,
                (100 - COALESCE(SUM(il.percent), 0)) as available_percent
            FROM items i
            JOIN itemtypes it ON i.fkitemtype = it.id
            LEFT JOIN itemloading il ON i.id = il.fkitem
        '''

        # Apply filters
        where_clauses = []

        # ItemType filter
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

        # Month range filter (critical for SQLite)
        where_clauses.append('(il.monthyear IS NULL OR il.monthyear BETWEEN ? AND ?)')
        params.append(start_month)
        params.append(end_month)

        # Add WHERE clause if filters exist
        if where_clauses:
            query += ' WHERE ' + ' AND '.join(where_clauses)

        # Group by to aggregate allocations per item per month
        query += '''
            GROUP BY i.id, i.itemname, it.typename, il.monthyear
            ORDER BY i.itemname, il.monthyear
        '''

        # Execute query
        results = db._execute(query, tuple(params)).fetchall()

        # Post-process to ensure all months appear for each item
        # Build complete dataset with all month combinations
        items_dict = {}
        for row in results:
            if row['id'] not in items_dict:
                items_dict[row['id']] = {
                    'id': row['id'],
                    'itemname': row['itemname'],
                    'typename': row['typename'],
                    'months': {}
                }
            if row['monthyear']:
                items_dict[row['id']]['months'][row['monthyear']] = {
                    'allocated': float(row['allocated_percent']),
                    'available': float(row['available_percent'])
                }

        # Fill in missing months with 100% availability
        data = []
        for item_id, item_data in items_dict.items():
            for month in month_range:
                if month in item_data['months']:
                    data.append({
                        'id': item_data['id'],
                        'itemname': item_data['itemname'],
                        'typename': item_data['typename'],
                        'monthyear': month,
                        'allocated_percent': item_data['months'][month]['allocated'],
                        'available_percent': item_data['months'][month]['available']
                    })
                else:
                    # No loading data for this month = 100% available
                    data.append({
                        'id': item_data['id'],
                        'itemname': item_data['itemname'],
                        'typename': item_data['typename'],
                        'monthyear': month,
                        'allocated_percent': 0.0,
                        'available_percent': 100.0
                    })

        return jsonify({
            'success': True,
            'data': data,
            'row_count': len(data),
            'filters': {
                'itemtype_id': itemtype_id,
                'char_key': char_key,
                'char_value': char_value,
                'itemname_filter': itemname_filter,
                'date_range': f'{start_month} to {end_month}'
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.get('/export')
def export_csv():
    """
    Export availability data as CSV.
    Uses same filters as query endpoint.
    """
    db = get_db()

    try:
        # Get filter parameters from query string
        itemtype_id = request.args.get('itemtype_id', type=int)
        char_key = request.args.get('char_key', '').strip()
        char_value = request.args.get('char_value', '').strip()
        itemname_filter = request.args.get('itemname_filter', '').strip()
        start_month = request.args.get('start_month', '')
        end_month = request.args.get('end_month', '')

        # Build same query as query_availability but SQLite compatible
        query_parts = []
        params = []

        query = '''
            SELECT 
                i.id,
                i.itemname,
                it.typename,
                il.monthyear,
                COALESCE(SUM(il.percent), 0) as allocated_percent,
                (100 - COALESCE(SUM(il.percent), 0)) as available_percent
            FROM items i
            JOIN itemtypes it ON i.fkitemtype = it.id
            LEFT JOIN itemloading il ON i.id = il.fkitem
        '''

        # Generate month range
        if start_month and end_month:
            month_range = db.generate_month_range(start_month, end_month)
        else:
            flash('Date range required', 'warning')
            return redirect(url_for('availability.analytics'))

        where_clauses = []

        if itemtype_id:
            where_clauses.append('i.fkitemtype = ?')
            params.append(itemtype_id)

        if char_key and char_value:
            query += 'JOIN itemcharacteristics ic ON i.id = ic.fkitem '
            where_clauses.append('ic.itemkey = ?')
            where_clauses.append('ic.itemvalue LIKE ?')
            params.append(char_key)
            params.append(f'%{char_value}%')

        if itemname_filter:
            where_clauses.append('i.itemname LIKE ?')
            params.append(f'%{itemname_filter}%')

        # Month range filter
        where_clauses.append('(il.monthyear IS NULL OR il.monthyear BETWEEN ? AND ?)')
        params.append(start_month)
        params.append(end_month)

        if where_clauses:
            query += ' WHERE ' + ' AND '.join(where_clauses)

        query += '''
            GROUP BY i.id, i.itemname, it.typename, il.monthyear
            ORDER BY i.itemname, il.monthyear
        '''

        results = db._execute(query, tuple(params)).fetchall()

        # Post-process to ensure all months appear
        items_dict = {}
        for row in results:
            if row['id'] not in items_dict:
                items_dict[row['id']] = {
                    'id': row['id'],
                    'itemname': row['itemname'],
                    'typename': row['typename'],
                    'months': {}
                }
            if row['monthyear']:
                items_dict[row['id']]['months'][row['monthyear']] = {
                    'allocated': float(row['allocated_percent']),
                    'available': float(row['available_percent'])
                }

        # Generate CSV
        from io import StringIO
        import csv

        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(['Item ID', 'Item Name', 'Type', 'Month', 'Allocated %', 'Available %'])

        # Write data - fill in all months for each item
        for item_id, item_data in items_dict.items():
            for month in month_range:
                if month in item_data['months']:
                    writer.writerow([
                        item_data['id'],
                        item_data['itemname'],
                        item_data['typename'],
                        month,
                        f"{item_data['months'][month]['allocated']:.1f}",
                        f"{item_data['months'][month]['available']:.1f}"
                    ])
                else:
                    # No loading data = 100% available
                    writer.writerow([
                        item_data['id'],
                        item_data['itemname'],
                        item_data['typename'],
                        month,
                        "0.0",
                        "100.0"
                    ])

        # Create response
        from flask import Response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=availability_export.csv'}
        )

    except Exception as e:
        flash(f'Export error: {e}', 'danger')
        return redirect(url_for('availability.analytics'))