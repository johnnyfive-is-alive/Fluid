from flask import Blueprint, g, render_template, request, redirect, url_for, flash

bp = Blueprint('characteristics', __name__)


def get_db():
    """Get database connection for current request."""
    from app import get_db as app_get_db
    return app_get_db()


@bp.get('/')
def form():
    """Show the characteristics form."""
    db = get_db()
    items = db.list_items()
    return render_template('characteristics_form.html', items=items)


@bp.post('/add')
def add():
    """Add a new characteristic to an item."""
    db = get_db()

    try:
        fkitem = int(request.form['fkitem'])
        itemkey = request.form['itemkey'].strip()
        itemvalue = request.form['itemvalue'].strip()
        itemkeyvaluetype = request.form.get('itemkeyvaluetype', '').strip() or None

        if not itemkey:
            flash('Item key is required.', 'warning')
            return redirect(url_for('characteristics.form'))

        # Add the characteristic
        db.add_characteristic(fkitem, itemkey, itemvalue, itemkeyvaluetype)
        db.con.commit()

        flash('Characteristic added successfully.', 'success')

    except ValueError as e:
        flash(f'Invalid input: {e}', 'danger')
    except Exception as e:
        db.con.rollback()
        flash(f'Error adding characteristic: {e}', 'danger')

    return redirect(url_for('characteristics.form'))