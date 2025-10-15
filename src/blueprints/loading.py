from flask import Blueprint, render_template, request, redirect, url_for, flash

bp = Blueprint('loading', __name__)


def get_db():
    """Get database connection for current request."""
    from app import get_db as app_get_db
    return app_get_db()


@bp.get('/')
def grid_selector():
    """
    Display item selection form for loading grid.
    Shows all items and all months in the system.
    No grid is shown initially - user must select items first.
    """
    db = get_db()
    items = db.list_items()

    # Get all distinct months that exist in the database
    all_months = db.list_months()

    return render_template(
        'loading_grid.html',
        items=items,
        all_months=all_months,
        selected_ids=[],
        editing=False,
        loadings={}
    )


@bp.post('/edit')
def grid_edit():
    """
    Display the loading grid for selected items.
    Creates a table where rows are items and columns are months.
    Each cell is an input field for that item's loading percentage for that month.
    """
    db = get_db()
    items = db.list_items()

    # Get selected item IDs from the form (user can select multiple)
    selected_ids = request.form.getlist('items')
    selected_ids = [int(id) for id in selected_ids]

    # Validate that at least one item was selected
    if not selected_ids:
        flash('Please select at least one item.', 'warning')
        return redirect(url_for('loading.grid_selector'))

    # Get all months that have loading data in the system
    all_months = db.list_months()

    # If no months exist yet, create a default set (current year)
    if not all_months:
        from datetime import datetime
        current_year = datetime.now().year
        all_months = [f"{current_year}-{m:02d}" for m in range(1, 13)]

    # Get existing loading data for selected items
    # Returns dict with (item_id, monthyear) -> percent
    loadings = db.get_loadings_for_items(selected_ids)

    return render_template(
        'loading_grid.html',
        items=items,
        all_months=all_months,
        selected_ids=selected_ids,
        editing=True,
        loadings=loadings
    )


@bp.post('/save')
def grid_save():
    """
    Save all loading grid changes.
    Processes all input fields from the grid form.
    Uses upsert to insert new values or update existing ones.
    """
    db = get_db()

    # Parse all form fields that start with "percent-"
    # Field name format: "percent-{item_id}-{monthyear}"
    updates = 0
    for key, value in request.form.items():
        if not key.startswith('percent-'):
            continue

        try:
            # Split the field name to extract item_id and monthyear
            parts = key.split('-', 2)
            if len(parts) != 3:
                continue

            _, item_id_str, monthyear = parts
            item_id = int(item_id_str)

            # Skip empty values (user didn't enter anything)
            if not value or value.strip() == '':
                continue

            percent = float(value)

            # Validate percent is in valid range (0-100)
            if not (0 <= percent <= 100):
                flash(f'Percent must be between 0 and 100 for item {item_id}, month {monthyear}', 'warning')
                continue

            # Upsert the loading value (insert if new, update if exists)
            db.upsert_loading(item_id, monthyear, percent)
            updates += 1

        except (ValueError, IndexError) as e:
            # Handle parsing errors gracefully
            flash(f'Error parsing value for {key}: {e}', 'warning')
            continue

    # Commit all changes to database
    db.con.commit()

    # Provide feedback to user
    if updates > 0:
        flash(f'Successfully saved {updates} loading values.', 'success')
    else:
        flash('No changes were made.', 'info')

    return redirect(url_for('loading.grid_selector'))