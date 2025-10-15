from flask import Blueprint, render_template, request, redirect, url_for, flash

bp = Blueprint('items', __name__)


def get_db():
    """Get database connection for current request."""
    from app import get_db as app_get_db
    return app_get_db()


@bp.get('/')
def list_items():
    """
    Display list of all items with their type information.
    Includes edit and delete buttons for each item.
    """
    db = get_db()

    # Get all items with their type information
    items_query = '''
        SELECT i.id, i.itemname, i.fkitemtype, it.typename
        FROM items i
        JOIN itemtypes it ON i.fkitemtype = it.id
        ORDER BY i.id
    '''
    items = db._execute(items_query).fetchall()

    return render_template('items_list.html', items=items)


@bp.get('/add')
def add_form():
    """
    Display form to add a new item.
    User selects item type from dropdown.
    """
    db = get_db()
    itemtypes = db.list_itemtypes()

    return render_template('items_add.html', itemtypes=itemtypes)


@bp.post('/add')
def add_item():
    """
    Process form submission to add a new item.
    Validates input and commits to database.
    """
    db = get_db()

    try:
        # Get form data
        itemname = request.form['itemname'].strip()
        fkitemtype = int(request.form['fkitemtype'])

        # Validate item name
        if not itemname:
            flash('Item name is required.', 'warning')
            return redirect(url_for('items.add_form'))

        # Check if item name already exists
        existing = db.get_item_by_name(itemname)
        if existing:
            flash(f'Item "{itemname}" already exists.', 'warning')
            return redirect(url_for('items.add_form'))

        # Add the item
        item_id = db.add_item(itemname, fkitemtype)
        db.con.commit()

        flash(f'Item "{itemname}" added successfully with ID {item_id}.', 'success')
        return redirect(url_for('items.list_items'))

    except ValueError as e:
        flash(f'Invalid input: {e}', 'danger')
    except Exception as e:
        db.con.rollback()
        flash(f'Error adding item: {e}', 'danger')

    return redirect(url_for('items.add_form'))


@bp.get('/edit/<int:id>')
def edit_form(id):
    """
    Display form to edit an existing item.
    Shows current values pre-filled in form.
    """
    db = get_db()

    # Get the item to edit
    item = db.get_item_by_id(id)
    if not item:
        flash('Item not found.', 'danger')
        return redirect(url_for('items.list_items'))

    # Get all item types for dropdown
    itemtypes = db.list_itemtypes()

    return render_template('items_edit.html', item=item, itemtypes=itemtypes)


@bp.post('/edit/<int:id>')
def edit_item(id):
    """
    Process form submission to update an existing item.
    Validates input and commits changes.
    """
    db = get_db()

    try:
        # Get form data
        itemname = request.form['itemname'].strip()
        fkitemtype = int(request.form['fkitemtype'])

        # Validate item name
        if not itemname:
            flash('Item name is required.', 'warning')
            return redirect(url_for('items.edit_form', id=id))

        # Check if new name conflicts with existing item (excluding current item)
        existing = db.get_item_by_name(itemname)
        if existing and existing['id'] != id:
            flash(f'Another item with name "{itemname}" already exists.', 'warning')
            return redirect(url_for('items.edit_form', id=id))

        # Update the item
        db.update_item(id, itemname=itemname, fkitemtype=fkitemtype)
        db.con.commit()

        flash(f'Item "{itemname}" updated successfully.', 'success')
        return redirect(url_for('items.list_items'))

    except ValueError as e:
        flash(f'Invalid input: {e}', 'danger')
    except Exception as e:
        db.con.rollback()
        flash(f'Error updating item: {e}', 'danger')

    return redirect(url_for('items.edit_form', id=id))


@bp.post('/delete/<int:id>')
def delete_item(id):
    """
    Delete an item from the database.
    Cascades to delete all related characteristics and loadings.
    """
    db = get_db()

    try:
        # Get item name before deletion for confirmation message
        item = db.get_item_by_id(id)
        if not item:
            flash('Item not found.', 'danger')
            return redirect(url_for('items.list_items'))

        itemname = item['itemname']

        # Delete the item (cascade will handle related records)
        db.delete_item(id)
        db.con.commit()

        flash(f'Item "{itemname}" and all related data deleted successfully.', 'success')

    except Exception as e:
        db.con.rollback()
        flash(f'Error deleting item: {e}', 'danger')

    return redirect(url_for('items.list_items'))