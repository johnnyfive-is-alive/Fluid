"""
Fallback visualization generator for when AI-generated D3 code fails.
Creates simple but functional D3.js visualizations based on data structure.
"""

def generate_fallback_visualization(pivot_data: dict, user_prompt: str = "") -> str:
    """
    Generate a simple D3.js visualization as fallback.
    Detects data structure and creates appropriate chart type.

    Args:
        pivot_data: Dictionary containing columns, data, numeric/categorical info
        user_prompt: Original user query (optional)

    Returns:
        JavaScript code string for D3.js visualization
    """

    numeric_cols = pivot_data.get('numeric_columns', [])
    categorical_cols = pivot_data.get('categorical_columns', [])
    data = pivot_data.get('data', [])

    if not data:
        return """
// No data to visualize
d3.select('#chart')
  .append('div')
  .attr('class', 'alert alert-warning')
  .text('No data returned from query');
"""

    # Debug logging to console
    num_cols = len(data[0].keys()) if data else 0

    print(f"🔍 Fallback viz detection:")
    print(f"   - Columns: {num_cols}")
    print(f"   - Numeric columns: {len(numeric_cols)}")
    print(f"   - Categorical columns: {len(categorical_cols)}")
    print(f"   - User prompt: '{user_prompt}'")

    # Check if this is a simple list query (name/id columns with no numeric data)
    # Or if it's a list-like query (mentions of "list", "show", "all")
    is_list_query = (
        len(numeric_cols) == 0 and  # No numeric columns
        (num_cols <= 4 or  # 4 or fewer columns
         'list' in user_prompt.lower() or  # Query mentions "list"
         'show' in user_prompt.lower() or  # Query mentions "show"
         'all' in user_prompt.lower())  # Query mentions "all"
    )

    print(f"   - Is list query: {is_list_query}")

    if is_list_query:
        print(f"   ✅ Using CARD LAYOUT")
        return generate_card_list()

    # Decide chart type based on data structure
    if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
        print(f"   ✅ Using BAR CHART")
        return generate_bar_chart(categorical_cols[0], numeric_cols[0])
    elif len(numeric_cols) >= 2:
        print(f"   ✅ Using SCATTER PLOT")
        return generate_scatter_plot(numeric_cols[0], numeric_cols[1])
    elif len(numeric_cols) == 1:
        print(f"   ✅ Using HISTOGRAM")
        return generate_histogram(numeric_cols[0])
    else:
        print(f"   ✅ Using TABLE")
        return generate_table()


def generate_card_list() -> str:
    """Generate a card-based list view for simple data (like lists of names)."""
    return """
// Card List View for Simple Data
const data = window.chartData;

if (!data || data.length === 0) {
  d3.select('#chart')
    .append('div')
    .attr('class', 'alert alert-warning')
    .html('<i class="bi bi-exclamation-triangle"></i> No data to display');
} else {
  const columns = Object.keys(data[0]);
  const container = d3.select('#chart');
  
  // Header with count
  const header = container.append('div')
    .attr('class', 'card mb-3');
  
  header.append('div')
    .attr('class', 'card-body bg-primary text-white')
    .html(`<h4 class="mb-0"><i class="bi bi-list-ul"></i> Results: ${data.length} item(s)</h4>`);
  
  // Create a grid of cards
  const cardGrid = container.append('div')
    .attr('class', 'row row-cols-1 row-cols-md-2 row-cols-lg-3 g-3');
  
  // Generate cards for each item
  const cards = cardGrid.selectAll('.col')
    .data(data)
    .join('div')
    .attr('class', 'col');
  
  const cardElements = cards.append('div')
    .attr('class', 'card h-100 shadow-sm')
    .style('cursor', 'pointer')
    .style('transition', 'transform 0.2s, box-shadow 0.2s')
    .on('mouseover', function() {
      d3.select(this)
        .style('transform', 'translateY(-5px)')
        .style('box-shadow', '0 8px 16px rgba(0,0,0,0.2)');
    })
    .on('mouseout', function() {
      d3.select(this)
        .style('transform', 'translateY(0)')
        .style('box-shadow', null);
    });
  
  // Card body
  const cardBody = cardElements.append('div')
    .attr('class', 'card-body');
  
  // Display each field
  cardBody.each(function(d, i) {
    const body = d3.select(this);
    
    columns.forEach((col, idx) => {
      if (idx === 0 && col.toLowerCase().includes('id')) {
        // ID badge at top right
        body.append('div')
          .attr('class', 'position-absolute top-0 end-0 m-2')
          .append('span')
          .attr('class', 'badge bg-secondary')
          .text(d[col]);
      } else if (col.toLowerCase().includes('name') || idx === 1) {
        // Primary field - large and bold
        body.append('h5')
          .attr('class', 'card-title mb-3')
          .html(`<i class="bi bi-tag-fill text-primary"></i> ${d[col]}`);
      } else {
        // Other fields
        const fieldDiv = body.append('div')
          .attr('class', 'mb-2');
        
        fieldDiv.append('strong')
          .attr('class', 'text-muted')
          .text(col + ': ');
        
        fieldDiv.append('span')
          .text(d[col] != null ? d[col] : 'N/A');
      }
    });
  });
  
  // Footer with summary
  container.append('div')
    .attr('class', 'card mt-3')
    .append('div')
    .attr('class', 'card-footer text-muted')
    .html(`<small><i class="bi bi-info-circle"></i> Showing ${data.length} result(s) in card view</small>`);
}
"""


def generate_table() -> str:
    """Generate a styled table when no numeric data is available."""
    return """
// Data Table with Card Layout
const data = window.chartData;

if (!data || data.length === 0) {
  d3.select('#chart')
    .append('div')
    .attr('class', 'alert alert-warning')
    .html('<i class="bi bi-exclamation-triangle"></i> No data to display');
} else {
  const columns = Object.keys(data[0]);
  
  const container = d3.select('#chart');
  
  // Add info header
  container.append('div')
    .attr('class', 'alert alert-info mb-3')
    .html('<strong><i class="bi bi-info-circle"></i> Note:</strong> Data displayed as table (no numeric columns for charting)');
  
  // Create card wrapper
  const card = container
    .append('div')
    .attr('class', 'card shadow-sm');
  
  const cardHeader = card.append('div')
    .attr('class', 'card-header bg-primary text-white d-flex justify-content-between align-items-center');
  
  cardHeader.append('h5')
    .attr('class', 'mb-0')
    .html('<i class="bi bi-table"></i> Query Results');
  
  cardHeader.append('span')
    .attr('class', 'badge bg-light text-dark')
    .text(`${data.length} row(s)`);
  
  const cardBody = card.append('div')
    .attr('class', 'card-body p-0');
  
  // Create scrollable table container
  const tableContainer = cardBody.append('div')
    .attr('class', 'table-responsive')
    .style('max-height', '600px')
    .style('overflow-y', 'auto');
  
  // Create table
  const table = tableContainer
    .append('table')
    .attr('class', 'table table-striped table-hover table-sm mb-0');
  
  // Header (sticky)
  const thead = table.append('thead')
    .attr('class', 'table-dark')
    .style('position', 'sticky')
    .style('top', '0')
    .style('z-index', '10');
  
  const headerRow = thead.append('tr');
  
  // Add row number column
  headerRow.append('th')
    .attr('class', 'text-center')
    .style('width', '60px')
    .text('#');
  
  // Add data columns
  headerRow.selectAll('th.data-col')
    .data(columns)
    .join('th')
    .attr('class', 'data-col')
    .html(d => `<i class="bi bi-tag"></i> ${d}`)
    .style('font-weight', 'bold');
  
  // Body
  const tbody = table.append('tbody');
  const rows = tbody.selectAll('tr')
    .data(data)
    .join('tr')
    .style('cursor', 'pointer')
    .on('mouseover', function() {
      d3.select(this).style('background-color', '#fff3cd');
    })
    .on('mouseout', function() {
      d3.select(this).style('background-color', null);
    });
  
  // Row numbers
  rows.append('td')
    .attr('class', 'text-center text-muted')
    .style('font-weight', 'bold')
    .text((d, i) => i + 1);
  
  // Data cells
  rows.selectAll('td.data-cell')
    .data(d => columns.map(col => ({col: col, value: d[col]})))
    .join('td')
    .attr('class', 'data-cell')
    .html(d => {
      if (d.value === null || d.value === undefined) {
        return '<span class="text-muted fst-italic">null</span>';
      }
      // Highlight if it looks like an ID
      if (d.col.toLowerCase().includes('id') && typeof d.value === 'number') {
        return `<span class="badge bg-secondary">${d.value}</span>`;
      }
      // Highlight if it's a name column
      if (d.col.toLowerCase().includes('name')) {
        return `<strong>${d.value}</strong>`;
      }
      return d.value;
    });
  
  // Footer with stats
  const cardFooter = card.append('div')
    .attr('class', 'card-footer text-muted');
  
  cardFooter.append('small')
    .html(`<i class="bi bi-database"></i> Showing <strong>${data.length}</strong> row(s) × <strong>${columns.length}</strong> column(s)`);
}
"""


def generate_bar_chart(cat_col: str, num_col: str) -> str:
    """Generate a bar chart D3.js code."""
    return f"""
// Bar Chart: {cat_col} vs {num_col}
const margin = {{{{top: 40, right: 30, bottom: 80, left: 60}}}};
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

const svg = d3.select('#chart')
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .append('g')
  .attr('transform', `translate(${{{{margin.left}}}},${{{{margin.top}}}})`);

const data = window.chartData;

// X scale
const x = d3.scaleBand()
  .domain(data.map(d => d['{cat_col}']))
  .range([0, width])
  .padding(0.2);

// Y scale
const y = d3.scaleLinear()
  .domain([0, d3.max(data, d => d['{num_col}'])])
  .nice()
  .range([height, 0]);

// X axis
svg.append('g')
  .attr('transform', `translate(0,${{{{height}}}})`)
  .call(d3.axisBottom(x))
  .selectAll('text')
  .attr('transform', 'rotate(-45)')
  .style('text-anchor', 'end');

// Y axis
svg.append('g')
  .call(d3.axisLeft(y));

// Bars
svg.selectAll('.bar')
  .data(data)
  .join('rect')
  .attr('class', 'bar')
  .attr('x', d => x(d['{cat_col}']))
  .attr('y', d => y(d['{num_col}']))
  .attr('width', x.bandwidth())
  .attr('height', d => height - y(d['{num_col}']))
  .attr('fill', 'steelblue')
  .on('mouseover', function(event, d) {{{{
    d3.select(this).attr('fill', 'orange');
    svg.append('text')
      .attr('class', 'tooltip')
      .attr('x', x(d['{cat_col}']) + x.bandwidth() / 2)
      .attr('y', y(d['{num_col}']) - 10)
      .attr('text-anchor', 'middle')
      .text(`${{{{d['{cat_col}']}}}}: ${{{{d['{num_col}']}}}}`);
  }}}})
  .on('mouseout', function() {{{{
    d3.select(this).attr('fill', 'steelblue');
    svg.selectAll('.tooltip').remove();
  }}}});

// Title
svg.append('text')
  .attr('x', width / 2)
  .attr('y', -10)
  .attr('text-anchor', 'middle')
  .style('font-size', '16px')
  .style('font-weight', 'bold')
  .text('{cat_col} vs {num_col}');

// X label
svg.append('text')
  .attr('x', width / 2)
  .attr('y', height + margin.bottom - 10)
  .attr('text-anchor', 'middle')
  .text('{cat_col}');

// Y label
svg.append('text')
  .attr('transform', 'rotate(-90)')
  .attr('x', -height / 2)
  .attr('y', -40)
  .attr('text-anchor', 'middle')
  .text('{num_col}');
"""


def generate_scatter_plot(x_col: str, y_col: str) -> str:
    """Generate a scatter plot D3.js code."""
    return f"""
// Scatter Plot: {x_col} vs {y_col}
const margin = {{{{top: 40, right: 30, bottom: 60, left: 60}}}};
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

const svg = d3.select('#chart')
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .append('g')
  .attr('transform', `translate(${{{{margin.left}}}},${{{{margin.top}}}})`);

const data = window.chartData;

// X scale
const x = d3.scaleLinear()
  .domain(d3.extent(data, d => d['{x_col}']))
  .nice()
  .range([0, width]);

// Y scale
const y = d3.scaleLinear()
  .domain(d3.extent(data, d => d['{y_col}']))
  .nice()
  .range([height, 0]);

// X axis
svg.append('g')
  .attr('transform', `translate(0,${{{{height}}}})`)
  .call(d3.axisBottom(x));

// Y axis
svg.append('g')
  .call(d3.axisLeft(y));

// Points
svg.selectAll('.dot')
  .data(data)
  .join('circle')
  .attr('class', 'dot')
  .attr('cx', d => x(d['{x_col}']))
  .attr('cy', d => y(d['{y_col}']))
  .attr('r', 5)
  .attr('fill', 'steelblue')
  .attr('opacity', 0.7)
  .on('mouseover', function(event, d) {{{{
    d3.select(this)
      .attr('r', 8)
      .attr('fill', 'orange');
    svg.append('text')
      .attr('class', 'tooltip')
      .attr('x', x(d['{x_col}']))
      .attr('y', y(d['{y_col}']) - 15)
      .attr('text-anchor', 'middle')
      .text(`({x_col}: ${{{{d['{x_col}']}}}}, {y_col}: ${{{{d['{y_col}']}}}})` );
  }}}})
  .on('mouseout', function() {{{{
    d3.select(this)
      .attr('r', 5)
      .attr('fill', 'steelblue');
    svg.selectAll('.tooltip').remove();
  }}}});

// Title
svg.append('text')
  .attr('x', width / 2)
  .attr('y', -10)
  .attr('text-anchor', 'middle')
  .style('font-size', '16px')
  .style('font-weight', 'bold')
  .text('{x_col} vs {y_col}');

// X label
svg.append('text')
  .attr('x', width / 2)
  .attr('y', height + 40)
  .attr('text-anchor', 'middle')
  .text('{x_col}');

// Y label
svg.append('text')
  .attr('transform', 'rotate(-90)')
  .attr('x', -height / 2)
  .attr('y', -40)
  .attr('text-anchor', 'middle')
  .text('{y_col}');
"""


def generate_histogram(num_col: str) -> str:
    """Generate a histogram D3.js code."""
    return f"""
// Histogram: {num_col}
const margin = {{{{top: 40, right: 30, bottom: 60, left: 60}}}};
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

const svg = d3.select('#chart')
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .append('g')
  .attr('transform', `translate(${{{{margin.left}}}},${{{{margin.top}}}})`);

const data = window.chartData.map(d => d['{num_col}']);

// X scale
const x = d3.scaleLinear()
  .domain(d3.extent(data))
  .nice()
  .range([0, width]);

// Histogram generator
const histogram = d3.histogram()
  .domain(x.domain())
  .thresholds(x.ticks(20));

const bins = histogram(data);

// Y scale
const y = d3.scaleLinear()
  .domain([0, d3.max(bins, d => d.length)])
  .nice()
  .range([height, 0]);

// X axis
svg.append('g')
  .attr('transform', `translate(0,${{{{height}}}})`)
  .call(d3.axisBottom(x));

// Y axis
svg.append('g')
  .call(d3.axisLeft(y));

// Bars
svg.selectAll('.bar')
  .data(bins)
  .join('rect')
  .attr('class', 'bar')
  .attr('x', d => x(d.x0))
  .attr('y', d => y(d.length))
  .attr('width', d => x(d.x1) - x(d.x0) - 1)
  .attr('height', d => height - y(d.length))
  .attr('fill', 'steelblue')
  .on('mouseover', function(event, d) {{{{
    d3.select(this).attr('fill', 'orange');
    svg.append('text')
      .attr('class', 'tooltip')
      .attr('x', x(d.x0) + (x(d.x1) - x(d.x0)) / 2)
      .attr('y', y(d.length) - 10)
      .attr('text-anchor', 'middle')
      .text(`Count: ${{{{d.length}}}}`);
  }}}})
  .on('mouseout', function() {{{{
    d3.select(this).attr('fill', 'steelblue');
    svg.selectAll('.tooltip').remove();
  }}}});

// Title
svg.append('text')
  .attr('x', width / 2)
  .attr('y', -10)
  .attr('text-anchor', 'middle')
  .style('font-size', '16px')
  .style('font-weight', 'bold')
  .text('Distribution of {num_col}');

// X label
svg.append('text')
  .attr('x', width / 2)
  .attr('y', height + 40)
  .attr('text-anchor', 'middle')
  .text('{num_col}');

// Y label
svg.append('text')
  .attr('transform', 'rotate(-90)')
  .attr('x', -height / 2)
  .attr('y', -40)
  .attr('text-anchor', 'middle')
  .text('Frequency');
"""


def generate_line_chart(x_col: str, y_col: str) -> str:
    """Generate a line chart (useful for time series)."""
    return f"""
// Line Chart: {x_col} vs {y_col}
const margin = {{{{top: 40, right: 30, bottom: 60, left: 60}}}};
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

const svg = d3.select('#chart')
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .append('g')
  .attr('transform', `translate(${{{{margin.left}}}},${{{{margin.top}}}})`);

const data = window.chartData;

// X scale (assuming categorical/ordinal for now)
const x = d3.scaleBand()
  .domain(data.map(d => d['{x_col}']))
  .range([0, width])
  .padding(0.1);

// Y scale
const y = d3.scaleLinear()
  .domain([0, d3.max(data, d => d['{y_col}'])])
  .nice()
  .range([height, 0]);

// Line generator
const line = d3.line()
  .x(d => x(d['{x_col}']) + x.bandwidth() / 2)
  .y(d => y(d['{y_col}']))
  .curve(d3.curveMonotoneX);

// X axis
svg.append('g')
  .attr('transform', `translate(0,${{{{height}}}})`)
  .call(d3.axisBottom(x))
  .selectAll('text')
  .attr('transform', 'rotate(-45)')
  .style('text-anchor', 'end');

// Y axis
svg.append('g')
  .call(d3.axisLeft(y));

// Draw line
svg.append('path')
  .datum(data)
  .attr('fill', 'none')
  .attr('stroke', 'steelblue')
  .attr('stroke-width', 2)
  .attr('d', line);

// Add points
svg.selectAll('.dot')
  .data(data)
  .join('circle')
  .attr('class', 'dot')
  .attr('cx', d => x(d['{x_col}']) + x.bandwidth() / 2)
  .attr('cy', d => y(d['{y_col}']))
  .attr('r', 4)
  .attr('fill', 'steelblue')
  .on('mouseover', function(event, d) {{{{
    d3.select(this)
      .attr('r', 6)
      .attr('fill', 'orange');
    svg.append('text')
      .attr('class', 'tooltip')
      .attr('x', x(d['{x_col}']) + x.bandwidth() / 2)
      .attr('y', y(d['{y_col}']) - 15)
      .attr('text-anchor', 'middle')
      .style('font-size', '12px')
      .text(`${{{{d['{x_col}']}}}}: ${{{{d['{y_col}']}}}}`);
  }}}})
  .on('mouseout', function() {{{{
    d3.select(this)
      .attr('r', 4)
      .attr('fill', 'steelblue');
    svg.selectAll('.tooltip').remove();
  }}}});

// Title
svg.append('text')
  .attr('x', width / 2)
  .attr('y', -10)
  .attr('text-anchor', 'middle')
  .style('font-size', '16px')
  .style('font-weight', 'bold')
  .text('{x_col} vs {y_col}');

// X label
svg.append('text')
  .attr('x', width / 2)
  .attr('y', height + margin.bottom - 10)
  .attr('text-anchor', 'middle')
  .text('{x_col}');

// Y label
svg.append('text')
  .attr('transform', 'rotate(-90)')
  .attr('x', -height / 2)
  .attr('y', -40)
  .attr('text-anchor', 'middle')
  .text('{y_col}');
"""