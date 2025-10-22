from flask import Flask, render_template, g
from db.fluiddbinterface import VerificationDB
import os

# Get the directory where app.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to your existing SQLite file (relative to app.py)
DB_PATH = os.path.join(BASE_DIR, 'db', 'fluid.db')

def get_db() -> VerificationDB:
    """
    Get database connection for current request context.
    Uses Flask's g object to store one connection per request.
    """
    if 'db' not in g:
        g.db = VerificationDB(DB_PATH)
        g.db.connect()
    return g.db


def create_app() -> Flask:
    """
    Create and configure the Flask application.
    Sets up database, blueprints, and routes.
    """
    app = Flask(__name__)

    # Secret key for session management (needed for flash messages)
    app.secret_key = 'dev-secret-key-change-in-production'

    # Store database path in config
    app.config['DB_PATH'] = DB_PATH

    # Initialize DB at startup (ensure schema compatibility)
    with app.app_context():
        db = VerificationDB(DB_PATH)
        db.connect()

        # Ensure PRODUCT type and UNALLOCATED product exist
        try:
            product_type_id = db.get_itemtype_id_by_typename('PRODUCT')
            if not product_type_id:
                product_type_id = db.add_itemtype('PRODUCT')
                db.con.commit()
                print("Created PRODUCT item type")

            unallocated = db.get_item_by_name('UNALLOCATED')
            if not unallocated:
                unallocated_id = db.add_item('UNALLOCATED', product_type_id)
                db.con.commit()
                print(f"Created UNALLOCATED product with ID {unallocated_id}")
        except Exception as e:
            print(f"Startup initialization warning: {e}")
        finally:
            db.close()

    # Make get_db function accessible
    app.config['GET_DB'] = get_db

    @app.teardown_appcontext
    def close_db(error):
        """
        Close database connection at end of request.
        Called automatically by Flask after each request.
        """
        db = g.pop('db', None)
        if db is not None:
            db.close()

    # Register blueprints for different functional areas
    from blueprints.characteristics import bp as characteristics_bp
    from blueprints.loading import bp as loading_bp
    from blueprints.items import bp as items_bp
    from blueprints.itemtypes import bp as itemtypes_bp
    from blueprints.products import bp as products_bp
    from blueprints.resources import bp as resources_bp
    from blueprints.stations import bp as stations_bp
    from blueprints.units import bp as units_bp
    from blueprints.ai_query import bp as ai_query_bp

    app.register_blueprint(characteristics_bp, url_prefix='/characteristics')
    app.register_blueprint(loading_bp, url_prefix='/loading')
    app.register_blueprint(items_bp, url_prefix='/items')
    app.register_blueprint(itemtypes_bp, url_prefix='/itemtypes')
    app.register_blueprint(products_bp, url_prefix='/products')
    app.register_blueprint(resources_bp, url_prefix='/resources')
    app.register_blueprint(stations_bp, url_prefix='/stations')
    app.register_blueprint(units_bp, url_prefix='/units')
    app.register_blueprint(ai_query_bp, url_prefix='/ai-query')

    @app.get('/')
    def home():
        """Home page with welcome message and navigation guidance."""
        return render_template('home.html')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
