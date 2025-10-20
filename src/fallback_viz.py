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

    # Decide chart type based on data structure
    if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
        return generate_bar_chart(categorical_cols[0], numeric_cols[0])
    elif len(numeric_cols) >= 2:
        return generate_scatter_plot(numeric_cols[0], numeric_cols[1])
    elif len(numeric_cols) == 1:
        return generate_histogram(numeric_cols[0])
    else:
        return generate_table()


def generate_bar_chart(cat_col: str, num_col: str) -> str:
    """Generate a bar chart D3.js code."""
    return f"""
// Bar Chart: {cat_col} vs {num_col}
const margin = {{top: 40, right: 30, bottom: 80, left: 60}};
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

const svg = d3.select('#chart')
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .append('g')
  .attr('transform', `translate(${{margin.left}},${{margin.top}})`);

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
  .attr('transform', `translate(0,${{height}})`)
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
  .on('mouseover', function(event, d) {{
    d3.select(this).attr('fill', 'orange');
    svg.append('text')
      .attr('class', 'tooltip')
      .attr('x', x(d['{cat_col}']) + x.bandwidth() / 2)
      .attr('y', y(d['{num_col}']) - 10)
      .attr('text-anchor', 'middle')
      .text(`${{d['{cat_col}']}}: ${{d['{num_col}']}}`);
  }})
  .on('mouseout', function() {{
    d3.select(this).attr('fill', 'steelblue');
    svg.selectAll('.tooltip').remove();
  }});

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
const margin = {{top: 40, right: 30, bottom: 60, left: 60}};
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

const svg = d3.select('#chart')
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .append('g')
  .attr('transform', `translate(${{margin.left}},${{margin.top}})`);

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
  .attr('transform', `translate(0,${{height}})`)
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
  .on('mouseover', function(event, d) {{
    d3.select(this)
      .attr('r', 8)
      .attr('fill', 'orange');
    svg.append('text')
      .attr('class', 'tooltip')
      .attr('x', x(d['{x_col}']))
      .attr('y', y(d['{y_col}']) - 15)
      .attr('text-anchor', 'middle')
      .text(`({x_col}: ${{d['{x_col}']}}, {y_col}: ${{d['{y_col}']}})`);
  }})
  .on('mouseout', function() {{
    d3.select(this)
      .attr('r', 5)
      .attr('fill', 'steelblue');
    svg.selectAll('.tooltip').remove();
  }});

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
const margin = {{top: 40, right: 30, bottom: 60, left: 60}};
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

const svg = d3.select('#chart')
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .append('g')
  .attr('transform', `translate(${{margin.left}},${{margin.top}})`);

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
  .attr('transform', `translate(0,${{height}})`)
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
  .on('mouseover', function(event, d) {{
    d3.select(this).attr('fill', 'orange');
    svg.append('text')
      .attr('class', 'tooltip')
      .attr('x', x(d.x0) + (x(d.x1) - x(d.x0)) / 2)
      .attr('y', y(d.length) - 10)
      .attr('text-anchor', 'middle')
      .text(`Count: ${{d.length}}`);
  }})
  .on('mouseout', function() {{
    d3.select(this).attr('fill', 'steelblue');
    svg.selectAll('.tooltip').remove();
  }});

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


def generate_table() -> str:
    """Generate a table when no numeric data is available."""
    return """
// Data Table
const data = window.chartData;

if (!data || data.length === 0) {
  d3.select('#chart')
    .append('div')
    .attr('class', 'alert alert-warning')
    .text('No data to display');
} else {
  const columns = Object.keys(data[0]);
  
  const container = d3.select('#chart');
  
  // Add info message
  container.append('div')
    .attr('class', 'alert alert-info mb-3')
    .html('<strong>Note:</strong> Data displayed as table (no numeric columns for charting)');
  
  // Create table
  const table = container
    .append('table')
    .attr('class', 'table table-striped table-hover table-sm');
  
  // Header
  const thead = table.append('thead').append('tr');
  thead.selectAll('th')
    .data(columns)
    .join('th')
    .text(d => d)
    .style('font-weight', 'bold')
    .style('background-color', '#f8f9fa');
  
  // Body
  const tbody = table.append('tbody');
  const rows = tbody.selectAll('tr')
    .data(data)
    .join('tr');
  
  rows.selectAll('td')
    .data(d => columns.map(col => d[col]))
    .join('td')
    .text(d => d != null ? d : '');
  
  // Add row count
  container.append('div')
    .attr('class', 'text-muted mt-2')
    .html(`<small>Showing ${data.length} row(s)</small>`);
}
"""


def generate_line_chart(x_col: str, y_col: str) -> str:
    """Generate a line chart (useful for time series)."""
    return f"""
// Line Chart: {x_col} vs {y_col}
const margin = {{top: 40, right: 30, bottom: 60, left: 60}};
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

const svg = d3.select('#chart')
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .append('g')
  .attr('transform', `translate(${{margin.left}},${{margin.top}})`);

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
  .attr('transform', `translate(0,${{height}})`)
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
  .on('mouseover', function(event, d) {{
    d3.select(this)
      .attr('r', 6)
      .attr('fill', 'orange');
    svg.append('text')
      .attr('class', 'tooltip')
      .attr('x', x(d['{x_col}']) + x.bandwidth() / 2)
      .attr('y', y(d['{y_col}']) - 15)
      .attr('text-anchor', 'middle')
      .style('font-size', '12px')
      .text(`${{d['{x_col}']}}: ${{d['{y_col}']}}`);
  }})
  .on('mouseout', function() {{
    d3.select(this)
      .attr('r', 4)
      .attr('fill', 'steelblue');
    svg.selectAll('.tooltip').remove();
  }});

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