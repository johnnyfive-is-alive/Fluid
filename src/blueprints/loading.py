from flask import Blueprint, g, render_template, request, redirect, url_for, flash

bp = Blueprint('loading', __name__)


def get_db():
    """Get database connection for current request."""
    from app import get_db as app_get_db
    return app_get_db()


@bp.get('/')
def grid_selector():
    """Show item selection form for loading grid."""
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
    """Show the loading grid for selected items."""
    db = get_db()
    items = db.list_items()

    # Get selected item IDs from the form
    selected_ids = request.form.getlist('items')
    selected_ids = [int(id) for id in selected_ids]

    if not selected_ids:
        flash('Please select at least one item.', 'warning')
        return redirect(url_for('loading.grid_selector'))

    # Get all months and current loadings
    all_months = db.list_months()

    # If no months exist yet, create a default set
    if not all_months:
        # Generate current year months as default
        from datetime import datetime
        current_year = datetime.now().year
        all_months = [f"{current_year}-{m:02d}" for m in range(1, 13)]

    # Get existing loading data for selected items
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
    """Save all loading grid changes."""
    db = get_db()

    # Parse all form fields that start with "percent-"
    updates = 0
    for key, value in request.form.items():
        if not key.startswith('percent-'):
            continue

        # Parse "percent-{item_id}-{monthyear}"
        try:
            parts = key.split('-', 2)
            if len(parts) != 3:
                continue

            _, item_id_str, monthyear = parts
            item_id = int(item_id_str)

            # Skip empty values
            if not value or value.strip() == '':
                continue

            percent = float(value)

            # Validate percent range
            if not (0 <= percent <= 100):
                flash(f'Percent must be between 0 and 100 for item {item_id}, month {monthyear}', 'warning')
                continue

            # Upsert the loading value
            db.upsert_loading(item_id, monthyear, percent)
            updates += 1

        except (ValueError, IndexError) as e:
            flash(f'Error parsing value for {key}: {e}', 'warning')
            continue

    # Commit all changes
    db.con.commit()

    if updates > 0:
        flash(f'Successfully saved {updates} loading values.', 'success')
    else:
        flash('No changes were made.', 'info')

    return redirect(url_for('loading.grid_selector'))