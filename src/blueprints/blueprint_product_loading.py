"""
Blueprint for managing product loading allocations.
Allows products to specify month-to-month resource requirements.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

bp = Blueprint('product_loading', __name__, url_prefix='/product-loading')


def get_db():
    """Get database connection for current request."""
    from app import get_db as app_get_db
    return app_get_db()


@bp.get('/<int:product_id>')
def view_product_loading(product_id):
    """
    Display loading allocation profile for a product.
    Shows month-to-month resource requirements (heads/stations/units).
    """
    db = get_db()

    # Get product details
    product = db.get_item_by_id(product_id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('products.list_products'))

    # Verify it's actually a product
    product_type = db.get_itemtype_by_id(product['fkitemtype'])
    if not product_type or product_type['typename'] != 'PRODUCT':
        flash('Item is not a product.', 'danger')
        return redirect(url_for('products.list_products'))

    # Get all loading requirements for this product
    loading_requirements = db.list_product_loadings_for_product(product_id)

    # Get available item types for the form - convert to dicts
    item_types = [dict(row) for row in db.list_itemtypes()]

    # Organize data for display - group by month
    monthly_data = {}
    for req in loading_requirements:
        month = req['monthyear']
        if month not in monthly_data:
            monthly_data[month] = []
        monthly_data[month].append({
            'id': req['id'],
            'typename': req['typename'],
            'quantity': req['quantity'],
            'notes': req['notes']
        })

    # Sort months
    sorted_months = sorted(monthly_data.keys())

    return render_template(
        'product_loading_view.html',
        product=product,
        monthly_data=monthly_data,
        sorted_months=sorted_months,
        item_types=item_types
    )


@bp.get('/<int:product_id>/edit')
def edit_form(product_id):
    """
    Display form to edit product loading allocations.
    Allows bulk month-to-month entry.
    """
    db = get_db()

    # Get product details
    product = db.get_item_by_id(product_id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('products.list_products'))

    # Get all item types - convert Row objects to dicts for JSON serialization
    item_types = [dict(row) for row in db.list_itemtypes()]

    # Get existing loading requirements
    existing_loadings = db.list_product_loadings_for_product(product_id)

    # Organize by month and item type for easier form display
    loading_matrix = {}
    for req in existing_loadings:
        month = req['monthyear']
        typename = req['typename']
        if month not in loading_matrix:
            loading_matrix[month] = {}
        loading_matrix[month][typename] = {
            'id': req['id'],
            'quantity': req['quantity'],
            'notes': req['notes']
        }

    # Get date range
    all_months = db.list_months()
    if not all_months:
        # Default to current year
        from datetime import datetime
        current_year = datetime.now().year
        all_months = [f"{current_year}-{str(m).zfill(2)}" for m in range(1, 13)]

    return render_template(
        'product_loading_edit.html',
        product=product,
        item_types=item_types,
        loading_matrix=loading_matrix,
        all_months=all_months
    )


@bp.post('/<int:product_id>/save')
def save_loading(product_id):
    """
    Save product loading allocations from form submission.
    Accepts month-to-month quantities for each item type.
    """
    db = get_db()

    try:
        # Get product
        product = db.get_item_by_id(product_id)
        if not product:
            flash('Product not found.', 'danger')
            return redirect(url_for('products.list_products'))

        # Process form data
        # Expected format: loading[YYYY-MM][typename] = quantity
        # Also: notes[YYYY-MM][typename] = notes
        saved_count = 0
        deleted_count = 0

        for key in request.form:
            if key.startswith('loading['):
                # Parse: loading[2025-01][RESOURCE] = "5.5"
                parts = key.replace('loading[', '').replace(']', '').split('[')
                if len(parts) != 2:
                    continue

                monthyear = parts[0]
                typename = parts[1]
                quantity_str = request.form[key].strip()

                # Get notes if provided
                notes_key = f'notes[{monthyear}][{typename}]'
                notes = request.form.get(notes_key, '').strip() or None

                # Get item type ID
                itemtype_id = db.get_itemtype_id_by_typename(typename)
                if not itemtype_id:
                    continue

                # If quantity is empty or 0, delete the record
                if not quantity_str or float(quantity_str) == 0:
                    # Find and delete existing record
                    existing_ids = db.find_product_loading_ids(
                        fkproduct=product_id,
                        fkitemtype=itemtype_id,
                        monthyear=monthyear
                    )
                    for existing_id in existing_ids:
                        db.delete_product_loading(existing_id)
                        deleted_count += 1
                else:
                    # Save/update the record
                    quantity = float(quantity_str)
                    db.upsert_product_loading(
                        fkproduct=product_id,
                        fkitemtype=itemtype_id,
                        monthyear=monthyear,
                        quantity=quantity,
                        notes=notes
                    )
                    saved_count += 1

        db.con.commit()

        if saved_count > 0 or deleted_count > 0:
            flash(
                f'Successfully saved {saved_count} loading requirement(s) '
                f'and removed {deleted_count} empty record(s).',
                'success'
            )
        else:
            flash('No changes were made.', 'info')

        return redirect(url_for('product_loading.view_product_loading', product_id=product_id))

    except ValueError as e:
        db.con.rollback()
        flash(f'Invalid number format: {e}', 'danger')
    except Exception as e:
        db.con.rollback()
        flash(f'Error saving loading allocations: {e}', 'danger')

    return redirect(url_for('product_loading.edit_form', product_id=product_id))


@bp.post('/<int:product_id>/delete/<int:loading_id>')
def delete_loading(product_id, loading_id):
    """Delete a specific product loading requirement."""
    db = get_db()

    try:
        # Verify the loading belongs to this product
        loading = db.get_product_loading_by_id(loading_id)
        if not loading:
            flash('Loading requirement not found.', 'danger')
            return redirect(url_for('product_loading.view_product_loading', product_id=product_id))

        if loading['fkproduct'] != product_id:
            flash('Loading requirement does not belong to this product.', 'danger')
            return redirect(url_for('product_loading.view_product_loading', product_id=product_id))

        # Delete the loading
        db.delete_product_loading(loading_id)
        db.con.commit()

        flash('Loading requirement deleted successfully.', 'success')

    except Exception as e:
        db.con.rollback()
        flash(f'Error deleting loading requirement: {e}', 'danger')

    return redirect(url_for('product_loading.view_product_loading', product_id=product_id))


@bp.get('/api/months')
def api_get_months():
    """API endpoint to get list of available months."""
    db = get_db()
    months = db.list_months()
    return jsonify({'months': months})


@bp.post('/api/generate-months')
def api_generate_months():
    """API endpoint to generate month range."""
    db = get_db()

    start_month = request.json.get('start_month')
    end_month = request.json.get('end_month')

    if not start_month or not end_month:
        return jsonify({'error': 'start_month and end_month required'}), 400

    months = db.generate_month_range(start_month, end_month)
    return jsonify({'months': months})