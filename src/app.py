from flask import Flask, render_template, g
from db.fluiddbinterface import VerificationDB
import os

# Get the directory where app.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to your existing SQLite file (relative to app.py)
DB_PATH = os.path.join(BASE_DIR, 'db', 'fluid.db')

# Ensure the extra table exists on startup
EXTRA_SCHEMA_PATH = os.path.join(BASE_DIR, 'schema_extras.sql')


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

    # Initialize DB & apply extra schema at startup (one-time setup)
    with app.app_context():
        db = VerificationDB(DB_PATH)
        db.connect()

        # Apply extra schema if file exists
        if os.path.exists(EXTRA_SCHEMA_PATH):
            with open(EXTRA_SCHEMA_PATH, 'r', encoding='utf-8') as f:
                db.con.executescript(f.read())
            db.con.commit()

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

    app.register_blueprint(characteristics_bp, url_prefix='/characteristics')
    app.register_blueprint(loading_bp, url_prefix='/loading')
    app.register_blueprint(items_bp, url_prefix='/items')
    app.register_blueprint(itemtypes_bp, url_prefix='/itemtypes')

    @app.get('/')
    def home():
        """Home page with welcome message and navigation guidance."""
        return render_template('home.html')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)