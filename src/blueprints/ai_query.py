from flask import Blueprint, render_template, request, jsonify
import json

bp = Blueprint('ai_query', __name__)


def get_db():
    """Get database connection for current request."""
    from app import get_db as app_get_db
    return app_get_db()


@bp.get('/')
def query_interface():
    """Display the AI query interface."""
    return render_template('ai_query.html')


@bp.post('/process')
def process_query():
    """
    Process natural language query through three phases:
    1. Data Query Generation (AI generates SQL)
    2. Data Retrieval & Pivot Processing
    3. Visualization Generation (AI generates D3.js code)
    """
    from src.ai_wrapper import LlamaQueryProcessor

    db = get_db()
    user_prompt = request.json.get('prompt', '')

    if not user_prompt:
        return jsonify({'error': 'No prompt provided'}), 400

    try:
        # Initialize the AI processor
        processor = LlamaQueryProcessor(
            model_path = 'C:\models\llama-3.2-3b\Llama-3.2-3B-Instruct-Q4_K_M.gguf',
            db_connection=db
        )

        # Execute the three-phase pipeline
        result = processor.process_pipeline(user_prompt)

        return jsonify({
            'success': True,
            'phase1_sql_generation': {
                'prompt': result['phase1']['prompt'],
                'sql_query': result['phase1']['sql_query'],
                'ai_response': result['phase1']['raw_response']
            },
            'phase2_data_retrieval': {
                'raw_data': result['phase2']['raw_data'],
                'pivot_data': result['phase2']['pivot_data'],
                'row_count': result['phase2']['row_count']
            },
            'phase3_visualization': {
                'prompt': result['phase3']['prompt'],
                'd3_code': result['phase3']['d3_code'],
                'ai_response': result['phase3']['raw_response']
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500


@bp.get('/schema')
def get_schema():
    """Return database schema information for debugging."""
    db = get_db()

    # Get all tables
    tables_query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    tables = db._execute(tables_query).fetchall()

    schema_info = {}

    for table in tables:
        table_name = table['name']
        # Get columns for each table
        columns_query = f"PRAGMA table_info({table_name});"
        columns = db._execute(columns_query).fetchall()

        schema_info[table_name] = [
            {
                'name': col['name'],
                'type': col['type'],
                'notnull': bool(col['notnull']),
                'pk': bool(col['pk'])
            }
            for col in columns
        ]

    return jsonify(schema_info)