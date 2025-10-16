from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime

bp = Blueprint('loading', __name__)


def get_db():
    """Get database connection for current request."""
    from app import get_db as app_get_db
    return app_get_db()


@bp.get('/')
def grid_selector():
    """
    Display item selection form for loading grid with product support.
    Shows all items and allows selection for the grid view.
    """
    db = get_db()

    # Get all non-product items for selection
    items_query = '''
        SELECT i.* FROM items i
        JOIN itemtypes it ON i.fkitemtype = it.id
        WHERE it.typename != 'PRODUCT'
        ORDER BY i.itemname
    '''
    items = db._execute(items_query).fetchall()

    # Get all products (including UNALLOCATED)
    products = db.list_products()

    # Set default date range (current year)
    current_year = datetime.now().year
    current_month = datetime.now().month
    start_month = f"{current_year}-{current_month:02d}"
    end_month = f"{current_year}-12"

    return render_template(
        'loading_grid_products.html',
        items=items,
        products=products,
        selected_ids=[],
        editing=False,
        loadings={},
        all_months=[],
        start_month=start_month,
        end_month=end_month
    )


@bp.post('/edit')
def grid_edit():
    """
    Display the product-based loading grid for selected items.
    Creates a table where:
    - Rows are items × months
    - Columns are products (including UNALLOCATED/INACTIVE)
    - Each cell is the loading percentage for that item-month-product combination
    """
    db = get_db()

    # Get all non-product items
    items_query = '''
        SELECT i.*, it.typename as typename FROM items i
        JOIN itemtypes it ON i.fkitemtype = it.id
        WHERE it.typename != 'PRODUCT'
        ORDER BY i.itemname
    '''
    items = db._execute(items_query).fetchall()

    # Get selected item IDs
    selected_ids = request.form.getlist('items')
    selected_ids = [int(id) for id in selected_ids]

    if not selected_ids:
        flash('Please select at least one item.', 'warning')
        return redirect(url_for('loading.grid_selector'))

    # Get date range from form (format: YYYY-MM)
    start_month = request.form.get('start_month', '')
    end_month = request.form.get('end_month', '')

    # Validate and generate month list
    if start_month and end_month:
        all_months = db.generate_month_range(start_month, end_month)
        if not all_months:
            flash('Invalid date range.', 'danger')
            return redirect(url_for('loading.grid_selector'))
    else:
        # Default: current year
        current_year = datetime.now().year
        all_months = [f"{current_year}-{m:02d}" for m in range(1, 13)]
        start_month = all_months[0]
        end_month = all_months[-1]

    # Get all products
    products = db.list_products()

    # Ensure UNALLOCATED exists
    unallocated_id = db.get_or_create_unallocated_product()
    if not any(p['id'] == unallocated_id for p in products):
        products = list(db.list_products())

    # Get existing loading data for selected items
    loadings = db.get_loadings_for_items(selected_ids)

    return render_template(
        'loading_grid_products.html',
        items=items,
        all_months=all_months,
        products=products,
        selected_ids=selected_ids,
        editing=True,
        loadings=loadings,
        unallocated_id=unallocated_id,
        start_month=start_month,
        end_month=end_month
    )


@bp.post('/save')
def grid_save():
    """
    Save all product-based loading grid changes.
    Processes all input fields from the grid form.
    Field name format: "percent-{item_id}-{monthyear}-{product_id}"
    """
    db = get_db()

    updates = 0
    errors = []

    # Parse all form fields that start with "percent-"
    for key, value in request.form.items():
        if not key.startswith('percent-'):
            continue

        try:
            # Remove the "percent-" prefix first
            key_without_prefix = key[8:]  # Remove "percent-"

            # Find the last hyphen to separate product_id
            last_hyphen_idx = key_without_prefix.rfind('-')
            if last_hyphen_idx == -1:
                continue

            product_id_str = key_without_prefix[last_hyphen_idx + 1:]
            remainder = key_without_prefix[:last_hyphen_idx]

            # Find the first hyphen to separate item_id from monthyear
            first_hyphen_idx = remainder.find('-')
            if first_hyphen_idx == -1:
                continue

            item_id_str = remainder[:first_hyphen_idx]
            monthyear = remainder[first_hyphen_idx + 1:]

            # Parse IDs
            item_id = int(item_id_str)
            product_id = int(product_id_str) if product_id_str != 'None' else None

            # Skip empty values
            if not value or value.strip() == '':
                continue

            percent = float(value)

            # Validate percent range
            if not (0 <= percent <= 100):
                errors.append(f'Invalid percent {percent}% for item {item_id}, month {monthyear}')
                continue

            # Upsert the loading value
            db.upsert_loading(item_id, monthyear, percent, product_id)
            updates += 1

        except (ValueError, IndexError) as e:
            errors.append(f'Error parsing {key}: {e}')
            continue

    # Commit all changes
    try:
        db.con.commit()

        if updates > 0:
            flash(f'Successfully saved {updates} loading values.', 'success')
        else:
            flash('No changes were made.', 'info')

        if errors:
            for error in errors[:5]:  # Show max 5 errors
                flash(error, 'warning')

    except Exception as e:
        db.con.rollback()
        flash(f'Error saving changes: {e}', 'danger')

    return redirect(url_for('loading.grid_selector'))


@bp.get('/validate/<int:item_id>/<monthyear>')
def validate_month_total(item_id, monthyear):
    """
    Validate that loading percentages for an item-month sum to ≤100%.
    Returns JSON with validation status.
    """
    db = get_db()

    cur = db._execute(
        'SELECT SUM(percent) as total FROM itemloading WHERE fkitem = ? AND monthyear = ?;',
        (item_id, monthyear)
    )
    result = cur.fetchone()
    total = result['total'] if result and result['total'] else 0

    return {
        'item_id': item_id,
        'monthyear': monthyear,
        'total': total,
        'valid': total <= 100,
        'message': f'Total: {total}%' if total <= 100 else f'Warning: Total is {total}% (exceeds 100%)'
    }