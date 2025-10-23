"""
AI Wrapper using llama-cpp-python with pre-built wheels.
Includes robust error handling and fallback mechanisms.

ENHANCEMENTS:
- Better SQL generation with item type awareness
- Improved handling of monthyear time series data
- Enhanced data pivoting for multi-line charts
- Uses enhanced fallback visualizations for all item types
- FIXED: Avoid COALESCE in GROUP BY (SQLite compatibility)
- FIXED: Catches i.itemtype (should be i.fkitemtype)
- FIXED: Converts subqueries to JOINs for better performance

Installation: pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
"""

from llama_cpp import Llama
import pandas as pd
import json
import re
from typing import Dict, List, Any, Optional
import os

# Import table metadata for AI context
from table_metadata import TABLE_METADATA, get_table_metadata


class LlamaQueryProcessor:
    """
    Processes natural language queries through AI-powered pipeline.

    Three-phase approach:
    1. SQL Generation: Convert natural language to SQL
    2. Data Retrieval: Execute SQL and pivot data
    3. Visualization: Generate D3.js code with enhanced animations
    """

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
                n_ctx=4096,          # Context window size (increased for longer prompts)
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
        """
        Extract database schema with formatting metadata for AI context.

        ENHANCEMENT: Now includes detailed column metadata from table_metadata.py
        to help AI understand:
        - Capitalization rules (STATION names are uppercase, RESOURCE names are mixed)
        - Column formats (monthyear is YYYY-MM)
        - Business rules (loading should sum to ≤100%)
        """
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

            # Add metadata if available (CRITICAL for item type awareness)
            metadata = get_table_metadata(table_name)
            metadata_info = ""

            if metadata:
                if 'capitalization' in metadata:
                    metadata_info += f"\n  Capitalization: {metadata['capitalization']}"

                if 'columns' in metadata:
                    col_notes = []
                    for col_name, col_meta in metadata['columns'].items():
                        # Check for capitalization_rules (helps AI understand item types)
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
        """
        Call Llama model with error handling.

        Uses Llama 3.2 instruction format with system context for better results.
        """
        # Construct full prompt in Llama 3.2 format
        if system_context:
            full_prompt = f"<|system|>\n{system_context}\n<|user|>\n{prompt}\n<|assistant|>\n"
        else:
            full_prompt = prompt

        try:
            response = self.llm(
                full_prompt,
                max_tokens=max_tokens,
                temperature=0.2,      # Low temperature for more deterministic SQL
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
        """
        Extract SQL query from AI response.

        Handles various formats:
        - Code blocks with ```sql
        - Bare SQL starting with SELECT
        - SQL with explanatory text
        """
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

    # Add this method to ai_wrapper.py - replaces _validate_and_fix_sql method

    def _validate_and_fix_sql(self, sql_query: str) -> str:
        """Validate and auto-fix common SQL errors."""
        import re

        # FIX 1: Replace i.itemtype with i.fkitemtype
        if re.search(r'\bi\.itemtype\b', sql_query, re.IGNORECASE):
            print("⚠️  Found i.itemtype - fixing to i.fkitemtype...")
            sql_query = re.sub(r'\bi\.itemtype\b', 'i.fkitemtype', sql_query, flags=re.IGNORECASE)

        # FIX 2: Improve name matching for all staff
        # Look for WHERE clauses with partial name matching that are too restrictive
        # Example: WHERE i.itemname LIKE '%Pavan%' OR i.itemname LIKE '%Eranki%'
        # Problem: Only works for "Pavan Eranki", not "John Smith" or single names

        # Find patterns like: WHERE i.itemname LIKE '%Name%' OR i.itemname LIKE '%Name2%'
        multi_like_pattern = r"WHERE\s+i\.itemname\s+LIKE\s+'%([^%']+)%'\s+OR\s+i\.itemname\s+LIKE\s+'%([^%']+)%'"
        match = re.search(multi_like_pattern, sql_query, re.IGNORECASE)

        if match:
            name1, name2 = match.group(1), match.group(2)
            # Combine into single LIKE for partial match of full name
            combined_pattern = f"{name1}%{name2}"
            print(f"⚠️  Improving name search from '{name1}' OR '{name2}' to flexible match...")

            # Replace with a single flexible LIKE that matches any part
            replacement = f"WHERE (i.itemname LIKE '%{name1}%' OR i.itemname LIKE '%{name2}%' OR i.itemname LIKE '%{name1} {name2}%' OR i.itemname LIKE '%{name2} {name1}%')"
            sql_query = re.sub(multi_like_pattern, replacement, sql_query, flags=re.IGNORECASE)

        # FIX 3: Single name searches - make them work for first or last names
        # Example: WHERE i.itemname LIKE '%John%' should also find "John Smith"
        single_like_pattern = r"WHERE\s+i\.itemname\s+LIKE\s+'%([^%']+)%'"
        if re.search(single_like_pattern, sql_query, re.IGNORECASE) and not match:
            # This is already good - single LIKE works for partial matches
            pass

        # FIX 4: Remove COALESCE from GROUP BY
        coalesce_in_group = re.search(
            r'GROUP BY.*?COALESCE\([^)]+\)',
            sql_query,
            re.IGNORECASE | re.DOTALL
        )
        if coalesce_in_group:
            print("⚠️  Found COALESCE in GROUP BY - fixing...")
            sql_query = re.sub(
                r'(GROUP BY.*?)COALESCE\([^,]+,\s*["\']UNALLOCATED["\']\)',
                r'\1p.itemname',
                sql_query,
                flags=re.IGNORECASE
            )

        # FIX 5: Convert subquery itemtype filters to JOINs
        subquery_pattern = r'WHERE\s+i\.fkitemtype\s*=\s*\(\s*SELECT\s+id\s+FROM\s+itemtypes\s+WHERE\s+\w+\.typename\s*=\s*["\'](\w+)["\']\s*\)'
        match = re.search(subquery_pattern, sql_query, re.IGNORECASE)

        if match:
            typename = match.group(1)
            print(f"⚠️  Converting itemtype subquery to JOIN for '{typename}'...")

            # Remove subquery WHERE clause
            sql_query = re.sub(subquery_pattern, '', sql_query, flags=re.IGNORECASE)

            # Add JOIN itemtypes if not exists
            if not re.search(r'JOIN\s+itemtypes', sql_query, re.IGNORECASE):
                items_join = re.search(r'(JOIN\s+items\s+i\s+ON\s+[^\n]+)', sql_query, re.IGNORECASE)
                if items_join:
                    insert_pos = items_join.end()
                    join_clause = f"\n  JOIN itemtypes it ON i.fkitemtype = it.id"
                    sql_query = sql_query[:insert_pos] + join_clause + sql_query[insert_pos:]

            # Add WHERE typename filter
            if 'WHERE' in sql_query.upper():
                sql_query = re.sub(r'WHERE\s+', f'WHERE it.typename = \'{typename}\' AND ', sql_query, count=1,
                                   flags=re.IGNORECASE)
            else:
                sql_query = sql_query.rstrip() + f"\nWHERE it.typename = '{typename}'"

        return sql_query

    def phase1_generate_sql(self, user_prompt: str) -> Dict[str, Any]:
        """
        Phase 1: Generate SQL query from natural language with formatting awareness.

        ENHANCEMENT: System context now includes:
        - Item type awareness (STATION vs RESOURCE vs UNIT)
        - Capitalization rules for each item type
        - monthyear format understanding
        - Product-based loading structure
        - SQL validation and auto-correction
        - FIXED: Avoid COALESCE in GROUP BY clauses
        - FIXED: Use correct column name i.fkitemtype (not i.itemtype)
        """

        system_context = f"""SQLite query generator. Use ONLY SQLite syntax.

SCHEMA:
{self.schema}

CRITICAL COLUMN NAMES:
- items.fkitemtype (NOT items.itemtype) - foreign key to itemtypes.id
- items.fkitemtype is an INTEGER (foreign key)
- To get typename: JOIN itemtypes it ON i.fkitemtype = it.id

CRITICAL SQLITE SYNTAX RULES (NO PostgreSQL):
1. NO EXTRACT, NO INTERVAL - monthyear is already 'YYYY-MM' format
2. Date math: date('now','-1 year') or simple strings like '2025-01'
3. Current date: date('now') returns 'YYYY-MM-DD', use substr to get 'YYYY-MM'
4. items.fkitemtype and il.fkproduct are INTs (foreign keys)
5. items has NO fkproduct column - use il.fkproduct from itemloading
6. Percent is in itemloading: il.percent (NOT i.percent)

CRITICAL: NEVER use COALESCE in GROUP BY clause!
✅ CORRECT: GROUP BY p.itemname  (group by the actual column)
❌ WRONG: GROUP BY COALESCE(p.itemname, 'UNALLOCATED')  (causes token error)

For display, use CASE WHEN in SELECT:
  CASE WHEN p.itemname IS NULL THEN 'UNALLOCATED' ELSE p.itemname END AS product

IMPORTANT: ALWAYS JOIN itemtypes WHEN FILTERING BY TYPE
- If WHERE clause uses it.typename, you MUST JOIN itemtypes it ON i.fkitemtype = it.id
- Never reference it.typename without JOIN itemtypes it ON i.fkitemtype = it.id
- CORRECT column name is i.fkitemtype (NOT i.itemtype)

FILTERING BY ITEM TYPE (CRITICAL):
✅ CORRECT:
```sql
SELECT i.itemname, it.typename, SUM(il.percent) as total
FROM itemloading il
JOIN items i ON il.fkitem = i.id
JOIN itemtypes it ON i.fkitemtype = it.id
WHERE it.typename = 'RESOURCE'
GROUP BY i.itemname, it.typename
```

❌ WRONG (uses subquery and wrong column):
```sql
WHERE i.itemtype = (SELECT id FROM itemtypes WHERE typename = 'RESOURCE')
```

❌ WRONG (missing JOIN):
```sql
WHERE it.typename = 'RESOURCE'  -- it is not defined!
```

PERSON/RESOURCE QUERIES (CRITICAL):
When user asks about a SPECIFIC PERSON's usage/loading/time allocation:
- The person is in the items table (e.g., "Pavan Eranki", "Gabor Farkas")
- You want to see HOW THAT PERSON'S time is allocated across products
- WRONG: Looking at all items and grouping by product
- CORRECT: Filter for that specific person, then show their allocation by product

EXAMPLE - "Show Pavan Eranki month to month use" or "Pavan Eranki usage by product":
```sql
SELECT 
  i.itemname,
  il.monthyear,
  CASE WHEN p.itemname IS NULL THEN 'UNALLOCATED' ELSE p.itemname END AS product,
  il.percent as total_percent
FROM itemloading il
JOIN items i ON il.fkitem = i.id
LEFT JOIN items p ON il.fkproduct = p.id
WHERE i.itemname LIKE '%Pavan%' OR i.itemname LIKE '%Eranki%'
  AND il.monthyear BETWEEN '2025-01' AND '2025-12'
ORDER BY il.monthyear, product
```

PRODUCT/PROGRAM QUERIES (CRITICAL):
When user asks about usage/loading/allocation FOR A PRODUCT OR PROGRAM:
- Keywords: "for the X program", "X product usage", "stations working on X", "beehive program"
- The product is in the items table with typename='PRODUCT' (e.g., "BEEHIVE 300G", "BEEHIVE R304")
- You want to see WHICH ITEMS/STATIONS are working on that product
- WRONG: Filter i.itemname (that's looking for a station named BEEHIVE)
- CORRECT: Filter p.itemname (that's the product being worked on)

EXAMPLE - "Give me station usage for the beehive program" or "stations working on beehive":
```sql
SELECT 
  i.itemname,
  il.monthyear,
  CASE WHEN p.itemname IS NULL THEN 'UNALLOCATED' ELSE p.itemname END AS product,
  SUM(il.percent) as total_percent
FROM itemloading il
JOIN items i ON il.fkitem = i.id
JOIN itemtypes it ON i.fkitemtype = it.id
LEFT JOIN items p ON il.fkproduct = p.id
WHERE p.itemname LIKE '%BEEHIVE%'
  AND it.typename = 'STATION'
  AND il.monthyear BETWEEN '2025-01' AND '2025-12'
GROUP BY i.itemname, il.monthyear, p.itemname
ORDER BY il.monthyear, i.itemname
```

Or if they want aggregated view by product:
```sql
SELECT 
  CASE WHEN p.itemname IS NULL THEN 'UNALLOCATED' ELSE p.itemname END AS product,
  il.monthyear,
  COUNT(DISTINCT il.fkitem) AS station_count,
  SUM(il.percent) AS total_percent
FROM itemloading il
LEFT JOIN items p ON il.fkproduct = p.id
WHERE il.monthyear BETWEEN '2025-01' AND '2025-12'
GROUP BY p.itemname, il.monthyear
ORDER BY il.monthyear, p.itemname
```

DETECTION RULES:
- Person query: "Pavan usage", "Gabor loading" → Filter i.itemname (the person)
- Product query: "beehive program", "for X product", "stations on X" → Filter p.itemname (the product)
- If query says "program" or "product" → It's asking about a product
- Product names are UPPERCASE: BEEHIVE, GENERIC, R64-72, VHAGAR, etc.
- Person names are mixed case: Pavan Eranki, Gabor Farkas, etc.

LOADING QUERIES WITH PRODUCTS:
```sql
SELECT 
  i.itemname,
  il.monthyear,
  CASE WHEN p.itemname IS NULL THEN 'UNALLOCATED' ELSE p.itemname END AS product,
  SUM(il.percent) as total_percent
FROM itemloading il
JOIN items i ON il.fkitem = i.id
LEFT JOIN items p ON il.fkproduct = p.id
WHERE il.monthyear BETWEEN '2025-01' AND '2025-12'
GROUP BY i.itemname, il.monthyear, p.itemname
ORDER BY i.itemname, il.monthyear, product
```

IMPORTANT NOTES:
- For products: JOIN items p ON il.fkproduct = p.id (product is in items table with typename='PRODUCT')
- UNALLOCATED: il.fkproduct IS NULL or p.itemname = 'UNALLOCATED'
- Always JOIN itemtypes if you need typename in SELECT or WHERE
- Use CASE WHEN for NULL handling in SELECT, NOT COALESCE in GROUP BY
- CORRECT column: i.fkitemtype (NOT i.itemtype)

Return ONLY SQL in ```sql blocks."""

        prompt = f"Query: {user_prompt}"

        print(f"🤖 Generating SQL for query: {user_prompt}")
        ai_response = self._call_llama(prompt, system_context, max_tokens=512)
        sql_query = self._extract_sql(ai_response)

        # Validate and auto-fix common SQL errors
        sql_query = self._validate_and_fix_sql(sql_query)

        # Fallback to safe query if extraction fails
        if not sql_query.upper().startswith('SELECT'):
            sql_query = "SELECT * FROM items LIMIT 10;"
            print("⚠️  Using fallback query")

        print(f"✅ SQL generated: {sql_query[:80]}...")

        return {
            'prompt': prompt,
            'sql_query': sql_query,
            'raw_response': ai_response
        }

    def phase2_retrieve_data(self, sql_query: str) -> Dict[str, Any]:
        """
        Phase 2: Execute SQL and prepare pivot data.

        ENHANCEMENT: Better grouping detection for multi-line charts
        - Identifies itemname columns for per-item lines
        - Identifies monthyear columns for time series
        - Prepares data structure for enhanced visualizations
        """
        try:
            print(f"📊 Executing SQL...")
            cursor = self.db._execute(sql_query)
            rows = cursor.fetchall()

            # Convert to dictionaries
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

            # Create DataFrame for analysis
            df = pd.DataFrame(raw_data)

            # Identify column types
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            categorical_cols = df.select_dtypes(exclude=['number']).columns.tolist()

            print(f"📈 Data structure: {len(numeric_cols)} numeric, {len(categorical_cols)} categorical columns")
            print(f"📋 Columns: {', '.join(df.columns)}")

            # Convert DataFrame to JSON-safe format (CRITICAL for D3.js)
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
                        # For any other type, convert to native Python type
                        try:
                            row_dict[col] = val.item() if hasattr(val, 'item') else str(val)
                        except:
                            row_dict[col] = str(val)
                json_safe_data.append(row_dict)

            # Build pivot data structure
            pivot_data = {
                'columns': list(df.columns),
                'numeric_columns': numeric_cols,
                'categorical_columns': categorical_cols,
                'data': json_safe_data,
                'summary': {}
            }

            # Calculate summary statistics for numeric columns
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

            # Try to create grouped data for charts (helps with product/item grouping)
            if categorical_cols and numeric_cols:
                group_col = categorical_cols[0]
                try:
                    grouped = df.groupby(group_col)[numeric_cols].agg(['sum', 'mean', 'count']).reset_index()
                    # Flatten and convert to JSON-safe format
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
                    print(f"📊 Created grouped aggregation by {group_col}")
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
        """
        Phase 3: Generate D3.js visualization code.

        ENHANCEMENT: Now uses enhanced fallback visualizations with:
        - Multi-line charts for item-by-month queries
        - Better detection of time series data
        - Enhanced animations and interactivity
        - Proper handling of all item types (stations, resources, units)

        NOTE: We use fallback for reliability. AI-generated D3 can be inconsistent.
        """

        # Import the enhanced fallback visualization generator
        from fallback_viz import generate_fallback_visualization

        print(f"📊 Generating enhanced visualization...")

        # Use enhanced fallback for reliability and better item type support
        fallback_code = generate_fallback_visualization(pivot_data, user_prompt)

        print(f"✅ Visualization code generated ({len(fallback_code)} chars)")

        return {
            'prompt': 'Using enhanced visualization templates with item type awareness',
            'd3_code': fallback_code,
            'raw_response': 'Using enhanced fallback visualization for reliability and better item type support',
            'used_fallback': True
        }

    def process_pipeline(self, user_prompt: str) -> Dict[str, Any]:
        """
        Execute complete three-phase pipeline.

        WORKFLOW:
        1. Generate SQL from natural language (with item type awareness)
        2. Execute SQL and pivot data (with proper column detection)
        3. Generate enhanced D3.js visualization (with animations)

        Returns complete results from all three phases for debugging and display.
        """
        print(f"\n{'='*60}")
        print(f"🚀 Processing query: {user_prompt}")
        print(f"{'='*60}\n")

        # Phase 1: Generate SQL with item type awareness
        phase1_result = self.phase1_generate_sql(user_prompt)

        # Phase 2: Retrieve and pivot data with proper column detection
        phase2_result = self.phase2_retrieve_data(phase1_result['sql_query'])

        # Phase 3: Generate enhanced visualization
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
        print(f"   - SQL generated: {len(phase1_result['sql_query'])} chars")
        print(f"   - Data rows: {phase2_result['row_count']}")
        print(f"   - Viz code: {len(phase3_result['d3_code'])} chars")
        print(f"{'='*60}\n")

        return {
            'phase1': phase1_result,
            'phase2': phase2_result,
            'phase3': phase3_result
        }