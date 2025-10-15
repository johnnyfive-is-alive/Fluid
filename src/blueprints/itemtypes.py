from flask import Blueprint, render_template, request, redirect, url_for, flash

bp = Blueprint('itemtypes', __name__)


def get_db():
    """Get database connection for current request."""
    from app import get_db as app_get_db
    return app_get_db()


@bp.get('/')
def list_types():
    """
    Display list of all item types.
    Shows count of items for each type.
    Includes edit and delete buttons.
    """
    db = get_db()

    # Get all item types with item counts
    types_query = '''
        SELECT it.id, it.typename, COUNT(i.id) as item_count
        FROM itemtypes it
        LEFT JOIN items i ON it.id = i.fkitemtype
        GROUP BY it.id, it.typename
        ORDER BY it.id
    '''
    itemtypes = db._execute(types_query).fetchall()

    return render_template('itemtypes_list.html', itemtypes=itemtypes)


@bp.get('/add')
def add_form():
    """Display form to add a new item type."""
    return render_template('itemtypes_add.html')


@bp.post('/add')
def add_type():
    """
    Process form submission to add a new item type.
    Ensures typename is unique.
    """
    db = get_db()

    try:
        # Get form data
        typename = request.form['typename'].strip().upper()

        # Validate typename
        if not typename:
            flash('Type name is required.', 'warning')
            return redirect(url_for('itemtypes.add_form'))

        # Check if typename already exists
        existing_id = db.get_itemtype_id_by_typename(typename)
        if existing_id:
            flash(f'Item type "{typename}" already exists.', 'warning')
            return redirect(url_for('itemtypes.add_form'))

        # Add the item type
        type_id = db.add_itemtype(typename)
        db.con.commit()

        flash(f'Item type "{typename}" added successfully with ID {type_id}.', 'success')
        return redirect(url_for('itemtypes.list_types'))

    except Exception as e:
        db.con.rollback()
        flash(f'Error adding item type: {e}', 'danger')

    return redirect(url_for('itemtypes.add_form'))


@bp.get('/edit/<int:id>')
def edit_form(id):
    """
    Display form to edit an existing item type.
    Shows current value pre-filled.
    """
    db = get_db()

    # Get the item type to edit
    itemtype = db.get_itemtype_by_id(id)
    if not itemtype:
        flash('Item type not found.', 'danger')
        return redirect(url_for('itemtypes.list_types'))

    return render_template('itemtypes_edit.html', itemtype=itemtype)


@bp.post('/edit/<int:id>')
def edit_type(id):
    """
    Process form submission to update an existing item type.
    Validates uniqueness of new typename.
    """
    db = get_db()

    try:
        # Get form data
        typename = request.form['typename'].strip().upper()

        # Validate typename
        if not typename:
            flash('Type name is required.', 'warning')
            return redirect(url_for('itemtypes.edit_form', id=id))

        # Check if new name conflicts with existing type (excluding current type)
        existing_id = db.get_itemtype_id_by_typename(typename)
        if existing_id and existing_id != id:
            flash(f'Another item type with name "{typename}" already exists.', 'warning')
            return redirect(url_for('itemtypes.edit_form', id=id))

        # Update the item type
        db.update_itemtype(id, typename=typename)
        db.con.commit()

        flash(f'Item type updated to "{typename}" successfully.', 'success')
        return redirect(url_for('itemtypes.list_types'))

    except Exception as e:
        db.con.rollback()
        flash(f'Error updating item type: {e}', 'danger')

    return redirect(url_for('itemtypes.edit_form', id=id))


@bp.post('/delete/<int:id>')
def delete_type(id):
    """
    Delete an item type from the database.
    Cannot delete if items are still using this type (foreign key constraint).
    """
    db = get_db()

    try:
        # Get typename before deletion for confirmation message
        itemtype = db.get_itemtype_by_id(id)
        if not itemtype:
            flash('Item type not found.', 'danger')
            return redirect(url_for('itemtypes.list_types'))

        typename = itemtype['typename']

        # Check if any items use this type
        items_query = 'SELECT COUNT(*) as cnt FROM items WHERE fkitemtype = ?'
        result = db._execute(items_query, (id,)).fetchone()

        if result['cnt'] > 0:
            flash(f'Cannot delete "{typename}": {result["cnt"]} item(s) still use this type.', 'danger')
            return redirect(url_for('itemtypes.list_types'))

        # Delete the item type
        db.delete_itemtype(id)
        db.con.commit()

        flash(f'Item type "{typename}" deleted successfully.', 'success')

    except Exception as e:
        db.con.rollback()
        flash(f'Error deleting item type: {e}', 'danger')

    return redirect(url_for('itemtypes.list_types'))