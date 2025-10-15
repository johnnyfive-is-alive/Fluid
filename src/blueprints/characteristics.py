from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash


bp = Blueprint('characteristics', __name__)


@bp.get('/')
def form():
db = current_app.config['DB']
items = db.list_items()
return render_template('characteristics_form.html', items=items)


@bp.post('/add')
def add():
db = current_app.config['DB']
fkitem = int(request.form['fkitem'])
itemkey = request.form['itemkey'].strip()
itemvalue = request.form['itemvalue'].strip()
itemkeyvaluetype = request.form.get('itemkeyvaluetype', '').strip() or None


if not itemkey:
flash('Item key is required.', 'danger')
return redirect(url_for('characteristics.form'))


db.add_characteristic(fkitem, itemkey, itemvalue, itemkeyvaluetype)
flash('Characteristic added.', 'success')
return redirect(url_for('characteristics.form'))