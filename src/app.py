from flask import Flask, render_template, g
from db.fluiddbinterface import VerificationDB
import os

# Path to your existing SQLite file (adjust as needed)
DB_PATH = 'src/db/fluid.db'

# Ensure the extra table exists on startup
EXTRA_SCHEMA_PATH = 'schema_extras.sql'


def get_db() -> VerificationDB:
    """Get database connection for current request context."""
    if 'db' not in g:
        g.db = VerificationDB(DB_PATH)
        g.db.connect()
    return g.db


def create_app() -> Flask:
    app = Flask(__name__)

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
        """Close database connection at end of request."""
        db = g.pop('db', None)
        if db is not None:
            db.close()

    # Register blueprints
    from blueprints.characteristics import bp as characteristics_bp
    from blueprints.loading import bp as loading_bp
    app.register_blueprint(characteristics_bp, url_prefix='/characteristics')
    app.register_blueprint(loading_bp, url_prefix='/loading')

    @app.get('/')
    def home():
        return render_template('home.html')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)