from flask import Blueprint, render_template, request, redirect, url_for, flash

bp = Blueprint('characteristics', __name__)


def get_db():
    """Get database connection for current request."""
    from app import get_db as app_get_db
    return app_get_db()


@bp.get('/')
def list_characteristics():
    """
    Display list of all characteristics grouped by item.
    Shows item name, key, value, and type.
    Includes edit and delete buttons for each characteristic.
    """
    db = get_db()

    # Get all characteristics with item information
    chars_query = '''
        SELECT ic.id, ic.fkitem, ic.itemkey, ic.itemvalue, ic.itemkeyvaluetype,
               i.itemname
        FROM itemcharacteristics ic
        JOIN items i ON ic.fkitem = i.id
        ORDER BY i.itemname, ic.itemkey
    '''
    characteristics = db._execute(chars_query).fetchall()

    return render_template('characteristics_list.html', characteristics=characteristics)


@bp.get('/add')
def add_form():
    """
    Display form to add a new characteristic to an item.
    User selects item and enters key/value pairs.
    """
    db = get_db()
    items = db.list_items()

    return render_template('characteristics_add.html', items=items)


@bp.post('/add')
def add_characteristic():
    """
    Process form submission to add a new characteristic.
    Validates input and handles unique constraint on (fkitem, itemkey).
    """
    db = get_db()

    try:
        # Get form data
        fkitem = int(request.form['fkitem'])
        itemkey = request.form['itemkey'].strip()
        itemvalue = request.form['itemvalue'].strip()
        itemkeyvaluetype = request.form.get('itemkeyvaluetype', '').strip() or None

        # Validate required fields
        if not itemkey:
            flash('Item key is required.', 'warning')
            return redirect(url_for('characteristics.add_form'))

        # Check if this key already exists for this item (unique constraint)
        existing_ids = db.find_itemcharacteristics_ids(fkitem=fkitem, itemkey=itemkey)
        if existing_ids:
            flash(f'Characteristic with key "{itemkey}" already exists for this item.', 'warning')
            return redirect(url_for('characteristics.add_form'))

        # Add the characteristic
        char_id = db.add_characteristic(fkitem, itemkey, itemvalue, itemkeyvaluetype)
        db.con.commit()

        flash(f'Characteristic "{itemkey}" added successfully.', 'success')
        return redirect(url_for('characteristics.list_characteristics'))

    except ValueError as e:
        flash(f'Invalid input: {e}', 'danger')
    except Exception as e:
        db.con.rollback()
        flash(f'Error adding characteristic: {e}', 'danger')

    return redirect(url_for('characteristics.add_form'))


@bp.get('/edit/<int:id>')
def edit_form(id):
    """
    Display form to edit an existing characteristic.
    Shows current values pre-filled.
    Note: fkitem and itemkey cannot be changed due to unique constraint.
    """
    db = get_db()

    # Get the characteristic to edit with item info
    char_query = '''
        SELECT ic.*, i.itemname
        FROM itemcharacteristics ic
        JOIN items i ON ic.fkitem = i.id
        WHERE ic.id = ?
    '''
    characteristic = db._execute(char_query, (id,)).fetchone()

    if not characteristic:
        flash('Characteristic not found.', 'danger')
        return redirect(url_for('characteristics.list_characteristics'))

    return render_template('characteristics_edit.html', characteristic=characteristic)


@bp.post('/edit/<int:id>')
def edit_characteristic(id):
    """
    Process form submission to update an existing characteristic.
    Only allows editing itemvalue and itemkeyvaluetype (not fkitem or itemkey).
    """
    db = get_db()

    try:
        # Get form data (only value and type can be edited)
        itemvalue = request.form['itemvalue'].strip()
        itemkeyvaluetype = request.form.get('itemkeyvaluetype', '').strip() or None

        # Update the characteristic (only value and type)
        db.update_itemcharacteristic(
            id,
            itemvalue=itemvalue,
            itemkeyvaluetype=itemkeyvaluetype
        )
        db.con.commit()

        flash('Characteristic updated successfully.', 'success')
        return redirect(url_for('characteristics.list_characteristics'))

    except Exception as e:
        db.con.rollback()
        flash(f'Error updating characteristic: {e}', 'danger')

    return redirect(url_for('characteristics.edit_form', id=id))


@bp.post('/delete/<int:id>')
def delete_characteristic(id):
    """
    Delete a characteristic from the database.
    Removes the key-value pair from the item.
    """
    db = get_db()

    try:
        # Get characteristic info before deletion for confirmation message
        characteristic = db.get_itemcharacteristic_by_id(id)
        if not characteristic:
            flash('Characteristic not found.', 'danger')
            return redirect(url_for('characteristics.list_characteristics'))

        itemkey = characteristic['itemkey']

        # Delete the characteristic
        db.delete_itemcharacteristic(id)
        db.con.commit()

        flash(f'Characteristic "{itemkey}" deleted successfully.', 'success')

    except Exception as e:
        db.con.rollback()
        flash(f'Error deleting characteristic: {e}', 'danger')

    return redirect(url_for('characteristics.list_characteristics'))