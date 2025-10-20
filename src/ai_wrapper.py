"""
AI Wrapper using llama-cpp-python with pre-built wheels.
Includes robust error handling and fallback mechanisms.

Installation: pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
"""

from llama_cpp import Llama
import pandas as pd
import json
import re
from typing import Dict, List, Any, Optional
import os

# Import table metadata
from table_metadata import TABLE_METADATA, get_table_metadata


class LlamaQueryProcessor:
    """Processes natural language queries through AI-powered pipeline."""

    def __init__(self, model_path: str = None, db_connection = None):
        # Try to import config, but provide defaults if it fails
        try:
            import config_ai as config
            self.model_path = model_path or config.MODEL_PATH
            self.config = config
        except ImportError:
            self.model_path = model_path
            self.config = None

        self.db = db_connection
        self.schema = self._get_schema()

        # Verify model file exists
        if not os.path.exists(self.model_path):
            raise Exception(
                f"Model file not found: {self.model_path}\n"
                f"Please verify the path in config_ai.py or download a model:\n"
                f"  huggingface-cli download bartowski/Llama-3.2-3B-Instruct-GGUF \\\n"
                f"      Llama-3.2-3B-Instruct-Q4_K_M.gguf --local-dir C:\\models\\llama-3.2-3b"
            )

        # Get file size
        file_size_mb = os.path.getsize(self.model_path) / (1024 * 1024)
        print(f"📁 Model file: {self.model_path}")
        print(f"📊 File size: {file_size_mb:.1f} MB")

        # Initialize Llama model with conservative settings
        try:
            print("🔄 Loading model (this may take 30-60 seconds)...")

            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=2048,          # Reduced context for stability
                n_threads=4,         # Conservative thread count
                n_gpu_layers=0,      # CPU only for compatibility
                n_batch=512,         # Batch size
                use_mlock=False,     # Don't lock memory (more compatible)
                use_mmap=True,       # Memory-map the file
                verbose=False,       # Reduce output
                seed=-1,             # Random seed
            )

            print("✅ Model loaded successfully!")

        except Exception as e:
            raise Exception(
                f"Failed to load model. This could be due to:\n"
                f"1. Insufficient RAM (need ~4-6GB free)\n"
                f"2. Corrupted model file\n"
                f"3. Incompatible model format\n"
                f"\nError details: {str(e)}\n"
                f"\nTry:\n"
                f"- Close other applications to free RAM\n"
                f"- Re-download the model\n"
                f"- Use a smaller model (1B instead of 3B)"
            )

    def _get_schema(self) -> str:
        """Extract database schema with formatting metadata for AI context."""
        schema_parts = []
        tables_query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        tables = self.db._execute(tables_query).fetchall()

        for table in tables:
            table_name = table['name']

            # Get column information
            columns_query = f"PRAGMA table_info({table_name});"
            columns = self.db._execute(columns_query).fetchall()

            col_info = ', '.join([
                f"{col['name']} {col['type']}" +
                (" PRIMARY KEY" if col['pk'] else "") +
                (" NOT NULL" if col['notnull'] else "")
                for col in columns
            ])

            # Get foreign keys
            fk_query = f"PRAGMA foreign_key_list({table_name});"
            fks = self.db._execute(fk_query).fetchall()
            fk_info = ""
            if fks:
                fk_info = "\n  Foreign Keys: " + ", ".join([
                    f"{fk['from']} -> {fk['table']}({fk['to']})"
                    for fk in fks
                ])

            # Add metadata if available
            metadata = get_table_metadata(table_name)
            metadata_info = ""

            if metadata:
                if 'capitalization' in metadata:
                    metadata_info += f"\n  Capitalization: {metadata['capitalization']}"

                if 'columns' in metadata:
                    col_notes = []
                    for col_name, col_meta in metadata['columns'].items():
                        # Check for capitalization_rules
                        if 'capitalization_rules' in col_meta:
                            rules = col_meta['capitalization_rules']
                            rules_str = "; ".join([f"{k}={v}" for k, v in rules.items()])
                            col_notes.append(f"{col_name} (rules: {rules_str})")
                        elif 'format' in col_meta:
                            col_notes.append(f"{col_name}: {col_meta.get('description', '')} [{col_meta['format']}]")

                    if col_notes:
                        metadata_info += "\n  Column Details: " + " | ".join(col_notes)

                if 'business_rules' in metadata:
                    rules = metadata['business_rules']
                    metadata_info += "\n  Business Rules: " + "; ".join(rules)

                if 'notes' in metadata:
                    metadata_info += f"\n  Notes: {metadata['notes']}"

            schema_parts.append(
                f"Table: {table_name}\n"
                f"  Columns: {col_info}{fk_info}{metadata_info}"
            )

        return "\n\n".join(schema_parts)

    def _call_llama(self, prompt: str, system_context: str = "", max_tokens: int = 512) -> str:
        """Call Llama model with error handling."""
        # Construct full prompt
        if system_context:
            full_prompt = f"<|system|>\n{system_context}\n<|user|>\n{prompt}\n<|assistant|>\n"
        else:
            full_prompt = prompt

        try:
            response = self.llm(
                full_prompt,
                max_tokens=max_tokens,
                temperature=0.2,
                top_p=0.9,
                top_k=40,
                repeat_penalty=1.1,
                stop=["<|user|>", "<|system|>", "\n\n\n"],
                echo=False
            )

            return response['choices'][0]['text'].strip()

        except Exception as e:
            raise Exception(f"Error generating response: {str(e)}")

    def _extract_sql(self, ai_response: str) -> str:
        """Extract SQL query from AI response."""
        # Look for SQL between ```sql and ``` or ```
        sql_pattern = r'```sql\s*(.*?)\s*```|```\s*(.*?)\s*```'
        matches = re.findall(sql_pattern, ai_response, re.DOTALL | re.IGNORECASE)

        if matches:
            for match in matches:
                sql = match[0] or match[1]
                if sql.strip():
                    return sql.strip()

        # Fallback: look for SELECT statements
        select_pattern = r'(SELECT\s+.*?(?:;|$))'
        select_matches = re.findall(select_pattern, ai_response, re.DOTALL | re.IGNORECASE)
        if select_matches:
            return select_matches[0].strip()

        # Clean up and return
        cleaned = ai_response.strip()
        for prefix in ["Here's the SQL query:", "SQL query:", "Query:", "Here is the query:"]:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()

        return cleaned

    def _extract_d3_code(self, ai_response: str) -> str:
        """Extract D3.js code from AI response."""
        code_pattern = r'```(?:javascript|js|html)\s*(.*?)\s*```|```\s*(.*?)\s*```'
        matches = re.findall(code_pattern, ai_response, re.DOTALL | re.IGNORECASE)

        if matches:
            for match in matches:
                code = match[0] or match[1]
                if code.strip() and ('d3' in code.lower() or 'svg' in code.lower()):
                    return code.strip()

        if '<svg' in ai_response or 'd3.' in ai_response:
            return ai_response.strip()

        return ai_response.strip()

    def phase1_generate_sql(self, user_prompt: str) -> Dict[str, Any]:
        """Phase 1: Generate SQL query from natural language with formatting awareness."""

        system_context = f"""SQLite query generator. Use ONLY SQLite syntax.

SCHEMA:
{self.schema}

SQLITE SYNTAX (NO PostgreSQL):
1. NO EXTRACT, NO INTERVAL. monthyear is already 'YYYY-MM' format - use it directly
2. Date math: date('now','-1 year') or use simple string: '2025-01'
3. Current date: date('now') returns 'YYYY-MM-DD', use substr to get 'YYYY-MM'
4. items.fkitemtype and il.fkproduct are INTs (foreign keys to items/itemtypes)
5. items has NO fkproduct column - use il.fkproduct or item_product_map
6. Percent is in itemloading: il.percent (NOT i.percent)

EXAMPLE - Product usage over next year:
SELECT 
  COALESCE(p.itemname, 'UNALLOCATED') AS product,
  il.monthyear,
  COUNT(DISTINCT il.fkitem) AS station_count,
  SUM(il.percent) AS total_percent
FROM itemloading il
LEFT JOIN items p ON il.fkproduct = p.id
WHERE il.monthyear BETWEEN '2025-01' AND '2025-12'
GROUP BY p.itemname, il.monthyear
ORDER BY il.monthyear, p.itemname

Return ONLY SQL in ```sql blocks."""

        prompt = f"Query: {user_prompt}"

        print(f"🤖 Generating SQL...")
        ai_response = self._call_llama(prompt, system_context, max_tokens=512)
        sql_query = self._extract_sql(ai_response)

        if not sql_query.upper().startswith('SELECT'):
            sql_query = "SELECT * FROM items LIMIT 10;"
            print("⚠️  Using fallback query")

        print(f"✅ SQL: {sql_query[:50]}...")

        return {
            'prompt': prompt,
            'sql_query': sql_query,
            'raw_response': ai_response
        }

    def phase2_retrieve_data(self, sql_query: str) -> Dict[str, Any]:
        """Phase 2: Execute SQL and prepare pivot data."""
        try:
            print(f"📊 Executing SQL...")
            cursor = self.db._execute(sql_query)
            rows = cursor.fetchall()

            raw_data = [dict(row) for row in rows]

            if not raw_data:
                print("⚠️  No data returned")
                return {
                    'raw_data': [],
                    'pivot_data': {
                        'columns': [],
                        'numeric_columns': [],
                        'categorical_columns': [],
                        'data': [],
                        'summary': {}
                    },
                    'row_count': 0
                }

            df = pd.DataFrame(raw_data)

            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            categorical_cols = df.select_dtypes(exclude=['number']).columns.tolist()

            # Convert DataFrame to JSON-safe format
            json_safe_data = []
            for _, row in df.iterrows():
                row_dict = {}
                for col in df.columns:
                    val = row[col]
                    # Convert pandas/numpy types to Python native types
                    if pd.isna(val):
                        row_dict[col] = None
                    elif isinstance(val, (pd.Timestamp, pd.DatetimeTZDtype)):
                        row_dict[col] = str(val)
                    elif isinstance(val, (int, float, str, bool)):
                        row_dict[col] = val
                    else:
                        # For any other type, try to convert to native Python type
                        try:
                            row_dict[col] = val.item() if hasattr(val, 'item') else str(val)
                        except:
                            row_dict[col] = str(val)
                json_safe_data.append(row_dict)

            pivot_data = {
                'columns': list(df.columns),
                'numeric_columns': numeric_cols,
                'categorical_columns': categorical_cols,
                'data': json_safe_data,
                'summary': {}
            }

            if numeric_cols:
                summary = {}
                for col in numeric_cols:
                    summary[col] = {
                        'min': float(df[col].min()) if not pd.isna(df[col].min()) else None,
                        'max': float(df[col].max()) if not pd.isna(df[col].max()) else None,
                        'mean': float(df[col].mean()) if not pd.isna(df[col].mean()) else None,
                        'sum': float(df[col].sum()) if not pd.isna(df[col].sum()) else None,
                        'count': int(df[col].count())
                    }
                pivot_data['summary'] = summary

            if categorical_cols and numeric_cols:
                group_col = categorical_cols[0]
                try:
                    grouped = df.groupby(group_col)[numeric_cols].agg(['sum', 'mean', 'count']).reset_index()
                    # Flatten multi-index columns and convert to JSON-safe format
                    grouped_simple = []
                    for idx in range(len(grouped)):
                        row_dict = {group_col: str(grouped.iloc[idx][group_col])}
                        for num_col in numeric_cols:
                            try:
                                row_dict[f'{num_col}_sum'] = float(grouped[num_col]['sum'].iloc[idx])
                                row_dict[f'{num_col}_mean'] = float(grouped[num_col]['mean'].iloc[idx])
                                row_dict[f'{num_col}_count'] = int(grouped[num_col]['count'].iloc[idx])
                            except:
                                pass  # Skip if conversion fails
                        grouped_simple.append(row_dict)
                    pivot_data['grouped'] = grouped_simple
                except:
                    # If grouping fails, just skip it
                    pass

            print(f"✅ Retrieved {len(json_safe_data)} rows")

            return {
                'raw_data': json_safe_data,
                'pivot_data': pivot_data,
                'row_count': len(json_safe_data)
            }

        except Exception as e:
            raise Exception(f"SQL execution error: {str(e)}\nQuery: {sql_query}")

    def phase3_generate_visualization(self, pivot_data: Dict, user_prompt: str) -> Dict[str, Any]:
        """Phase 3: Generate D3.js visualization code (using fallback for reliability)."""

        from fallback_viz import generate_fallback_visualization

        print(f"📊 Generating visualization...")

        # Use fallback for reliability (AI D3 generation can be flaky)
        fallback_code = generate_fallback_visualization(pivot_data, user_prompt)

        print(f"✅ Visualization code generated")

        return {
            'prompt': 'Using pre-built visualization templates',
            'd3_code': fallback_code,
            'raw_response': 'Using fallback visualization for reliability',
            'used_fallback': True
        }

    def process_pipeline(self, user_prompt: str) -> Dict[str, Any]:
        """Execute complete three-phase pipeline."""
        print(f"\n{'='*60}")
        print(f"🚀 Processing query: {user_prompt}")
        print(f"{'='*60}\n")

        # Phase 1: Generate SQL
        phase1_result = self.phase1_generate_sql(user_prompt)

        # Phase 2: Retrieve and pivot data
        phase2_result = self.phase2_retrieve_data(phase1_result['sql_query'])

        # Phase 3: Generate visualization
        if phase2_result['row_count'] > 0:
            phase3_result = self.phase3_generate_visualization(
                phase2_result['pivot_data'],
                user_prompt
            )
        else:
            phase3_result = {
                'prompt': 'No data to visualize',
                'd3_code': '// No data returned from query',
                'raw_response': 'No data returned from the SQL query.',
                'used_fallback': True
            }

        print(f"\n{'='*60}")
        print(f"✅ Pipeline complete!")
        print(f"{'='*60}\n")

        return {
            'phase1': phase1_result,
            'phase2': phase2_result,
            'phase3': phase3_result
        }