from flask import Flask, render_template
from db.fluiddbinterface import VerificationDB

# Path to your existing SQLite file (adjust as needed)
DB_PATH = 'my.db'

# Ensure the extra table exists on startup
EXTRA_SCHEMA_PATH = 'schema_extras.sql'

def create_app() -> Flask:
app = Flask(__name__)


# Initialize DB & apply extra schema (idempotent)
db = VerificationDB(DB_PATH)
db.connect()
with open(EXTRA_SCHEMA_PATH, 'r', encoding='utf-8') as f:
db.con.executescript(f.read())
db.con.commit()


# Make `db` accessible via app context (simple approach)
app.config['DB'] = db


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