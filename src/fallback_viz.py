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
        print("⚠️  No data to visualize")
        return """
// No data to visualize
d3.select('#chart')
  .append('div')
  .attr('class', 'alert alert-warning')
  .html('<i class="bi bi-exclamation-triangle"></i> No data returned from query');
"""

    # Debug logging to console
    num_cols = len(data[0].keys()) if data else 0

    print(f"🔍 Fallback viz detection:")
    print(f"   - Columns: {num_cols}")
    print(f"   - Column names: {list(data[0].keys())}")
    print(f"   - Numeric columns: {len(numeric_cols)} - {numeric_cols}")
    print(f"   - Categorical columns: {len(categorical_cols)} - {categorical_cols}")
    print(f"   - User prompt: '{user_prompt}'")
    print(f"   - Row count: {len(data)}")

    # Check if this has a monthyear column (time series data)
    has_monthyear = any('month' in col.lower() for col in data[0].keys())
    monthyear_col = None
    if has_monthyear:
        for col in categorical_cols:
            if 'month' in col.lower():
                monthyear_col = col
                break

    print(f"   - Has monthyear: {has_monthyear}, Column: {monthyear_col}")

    # Check if this is a simple list query (name/id columns with no numeric data)
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

    # Time series: if we have monthyear and numeric columns, use grouped bar chart
    if monthyear_col and len(numeric_cols) >= 1:
        # Check if we also have a grouping column (like product)
        other_cats = [c for c in categorical_cols if c != monthyear_col]
        if other_cats and len(numeric_cols) >= 1:
            print(f"   ✅ Using GROUPED BAR CHART (time series with groups)")
            return generate_grouped_bar_chart(monthyear_col, other_cats[0], numeric_cols[0])
        elif len(numeric_cols) >= 1:
            print(f"   ✅ Using LINE CHART (time series)")
            return generate_line_chart(monthyear_col, numeric_cols[0])

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
        print(f"   ✅ Using TABLE (fallback)")
        return generate_table()


def generate_card_list() -> str:
    """Generate a card-based list view for simple data (like lists of names)."""
    return """
// Card List View for Simple Data
console.log('📋 Rendering card list view...');
console.log('Data:', window.chartData);

const data = window.chartData;

if (!data || data.length === 0) {
  console.error('❌ No data available for card list');
  d3.select('#chart')
    .append('div')
    .attr('class', 'alert alert-warning')
    .html('<i class="bi bi-exclamation-triangle"></i> No data to display');
} else {
  console.log('✅ Rendering', data.length, 'cards');
  const columns = Object.keys(data[0]);
  console.log('Columns:', columns);
  
  const container = d3.select('#chart');
  
  // Clear any existing content
  container.html('');
  
  // Header with count
  const header = container.append('div')
    .attr('class', 'card mb-3 shadow-sm');
  
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
      } else if (col.toLowerCase().includes('name') || idx === 0) {
        // Primary field - large and bold (use first column if no 'name' found)
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
  
  console.log('✅ Card list rendered successfully');
}
"""


def generate_table() -> str:
    """Generate a styled table when no numeric data is available."""
    return """
// Data Table with Card Layout
console.log('📊 Rendering table view...');
console.log('Data:', window.chartData);

const data = window.chartData;

if (!data || data.length === 0) {
  console.error('❌ No data available for table');
  d3.select('#chart')
    .append('div')
    .attr('class', 'alert alert-warning')
    .html('<i class="bi bi-exclamation-triangle"></i> No data to display');
} else {
  console.log('✅ Rendering table with', data.length, 'rows');
  const columns = Object.keys(data[0]);
  console.log('Columns:', columns);
  
  const container = d3.select('#chart');
  
  // Clear any existing content
  container.html('');
  
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
  
  console.log('✅ Table rendered successfully');
}
"""


def generate_grouped_bar_chart(time_col: str, group_col: str, value_col: str) -> str:
    """Generate a grouped bar chart for time series with multiple groups."""
    code = """
// Grouped Bar Chart: """ + time_col + """ by """ + group_col + """
console.log('📊 Rendering grouped bar chart...');
const margin = {top: 40, right: 120, bottom: 80, left: 60};
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

const svg = d3.select('#chart')
  .html('')
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .append('g')
  .attr('transform', `translate(${margin.left},${margin.top})`);

const data = window.chartData;

// Get unique months and groups
const months = [...new Set(data.map(d => d['""" + time_col + """']))].sort();
const groups = [...new Set(data.map(d => d['""" + group_col + """']))];

// Color scale for groups
const color = d3.scaleOrdinal()
  .domain(groups)
  .range(d3.schemeSet2);

// X scale for months
const x0 = d3.scaleBand()
  .domain(months)
  .range([0, width])
  .padding(0.2);

// X scale for groups within each month
const x1 = d3.scaleBand()
  .domain(groups)
  .range([0, x0.bandwidth()])
  .padding(0.05);

// Y scale
const y = d3.scaleLinear()
  .domain([0, d3.max(data, d => d['""" + value_col + """'])])
  .nice()
  .range([height, 0]);

// X axis
svg.append('g')
  .attr('transform', `translate(0,${height})`)
  .call(d3.axisBottom(x0))
  .selectAll('text')
  .attr('transform', 'rotate(-45)')
  .style('text-anchor', 'end');

// Y axis
svg.append('g')
  .call(d3.axisLeft(y));

// Create groups for each month
const monthGroups = svg.selectAll('.month-group')
  .data(months)
  .join('g')
  .attr('class', 'month-group')
  .attr('transform', d => `translate(${x0(d)},0)`);

// Add bars for each group within month
monthGroups.each(function(month) {
  const monthData = data.filter(d => d['""" + time_col + """'] === month);
  
  d3.select(this).selectAll('.bar')
    .data(monthData)
    .join('rect')
    .attr('class', 'bar')
    .attr('x', d => x1(d['""" + group_col + """']))
    .attr('y', d => y(d['""" + value_col + """']))
    .attr('width', x1.bandwidth())
    .attr('height', d => height - y(d['""" + value_col + """']))
    .attr('fill', d => color(d['""" + group_col + """']))
    .on('mouseover', function(event, d) {
      d3.select(this).attr('opacity', 0.7);
      svg.append('text')
        .attr('class', 'tooltip')
        .attr('x', x0(d['""" + time_col + """']) + x1(d['""" + group_col + """']) + x1.bandwidth() / 2)
        .attr('y', y(d['""" + value_col + """']) - 10)
        .attr('text-anchor', 'middle')
        .style('font-size', '12px')
        .text(`${d['""" + group_col + """']}: ${d['""" + value_col + """']}`);
    })
    .on('mouseout', function() {
      d3.select(this).attr('opacity', 1);
      svg.selectAll('.tooltip').remove();
    });
});

// Legend
const legend = svg.append('g')
  .attr('class', 'legend')
  .attr('transform', `translate(${width + 20}, 0)`);

groups.forEach((group, i) => {
  const legendRow = legend.append('g')
    .attr('transform', `translate(0, ${i * 20})`);
  
  legendRow.append('rect')
    .attr('width', 15)
    .attr('height', 15)
    .attr('fill', color(group));
  
  legendRow.append('text')
    .attr('x', 20)
    .attr('y', 12)
    .style('font-size', '12px')
    .text(group);
});

// Title
svg.append('text')
  .attr('x', width / 2)
  .attr('y', -10)
  .attr('text-anchor', 'middle')
  .style('font-size', '16px')
  .style('font-weight', 'bold')
  .text('""" + value_col + """ by """ + group_col + """ over time');

// X label
svg.append('text')
  .attr('x', width / 2)
  .attr('y', height + margin.bottom - 10)
  .attr('text-anchor', 'middle')
  .text('""" + time_col + """');

// Y label
svg.append('text')
  .attr('transform', 'rotate(-90)')
  .attr('x', -height / 2)
  .attr('y', -40)
  .attr('text-anchor', 'middle')
  .text('""" + value_col + """');

console.log('✅ Grouped bar chart rendered');
"""
    return code


def generate_bar_chart(cat_col: str, num_col: str) -> str:
    """Generate a bar chart D3.js code."""
    # Use string concatenation to avoid f-string brace issues
    code = """
// Bar Chart: """ + cat_col + """ vs """ + num_col + """
console.log('📊 Rendering bar chart...');
const margin = {top: 40, right: 30, bottom: 80, left: 60};
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

const svg = d3.select('#chart')
  .html('')
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .append('g')
  .attr('transform', `translate(${margin.left},${margin.top})`);

const data = window.chartData;

// X scale
const x = d3.scaleBand()
  .domain(data.map(d => d['""" + cat_col + """']))
  .range([0, width])
  .padding(0.2);

// Y scale
const y = d3.scaleLinear()
  .domain([0, d3.max(data, d => d['""" + num_col + """'])])
  .nice()
  .range([height, 0]);

// X axis
svg.append('g')
  .attr('transform', `translate(0,${height})`)
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
  .attr('x', d => x(d['""" + cat_col + """']))
  .attr('y', d => y(d['""" + num_col + """']))
  .attr('width', x.bandwidth())
  .attr('height', d => height - y(d['""" + num_col + """']))
  .attr('fill', 'steelblue')
  .on('mouseover', function(event, d) {
    d3.select(this).attr('fill', 'orange');
    svg.append('text')
      .attr('class', 'tooltip')
      .attr('x', x(d['""" + cat_col + """']) + x.bandwidth() / 2)
      .attr('y', y(d['""" + num_col + """']) - 10)
      .attr('text-anchor', 'middle')
      .text(`${d['""" + cat_col + """']}: ${d['""" + num_col + """']}`);
  })
  .on('mouseout', function() {
    d3.select(this).attr('fill', 'steelblue');
    svg.selectAll('.tooltip').remove();
  });

// Title
svg.append('text')
  .attr('x', width / 2)
  .attr('y', -10)
  .attr('text-anchor', 'middle')
  .style('font-size', '16px')
  .style('font-weight', 'bold')
  .text('""" + cat_col + """ vs """ + num_col + """');

// X label
svg.append('text')
  .attr('x', width / 2)
  .attr('y', height + margin.bottom - 10)
  .attr('text-anchor', 'middle')
  .text('""" + cat_col + """');

// Y label
svg.append('text')
  .attr('transform', 'rotate(-90)')
  .attr('x', -height / 2)
  .attr('y', -40)
  .attr('text-anchor', 'middle')
  .text('""" + num_col + """');

console.log('✅ Bar chart rendered');
"""
    return code


def generate_scatter_plot(x_col: str, y_col: str) -> str:
    """Generate a scatter plot D3.js code."""
    return f"""
// Scatter Plot: {x_col} vs {y_col}
console.log('📊 Rendering scatter plot...');
const margin = {{{{top: 40, right: 30, bottom: 60, left: 60}}}};
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

const svg = d3.select('#chart')
  .html('')  // Clear existing
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
  .attr('opacity', 0.7);

// Title
svg.append('text')
  .attr('x', width / 2)
  .attr('y', -10)
  .attr('text-anchor', 'middle')
  .style('font-size', '16px')
  .style('font-weight', 'bold')
  .text('{x_col} vs {y_col}');

console.log('✅ Scatter plot rendered');
"""


def generate_histogram(num_col: str) -> str:
    """Generate a histogram D3.js code."""
    return f"""
// Histogram: {num_col}
console.log('📊 Rendering histogram...');
const margin = {{{{top: 40, right: 30, bottom: 60, left: 60}}}};
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

const svg = d3.select('#chart')
  .html('')  // Clear existing
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
  .attr('fill', 'steelblue');

// Title
svg.append('text')
  .attr('x', width / 2)
  .attr('y', -10)
  .attr('text-anchor', 'middle')
  .style('font-size', '16px')
  .style('font-weight', 'bold')
  .text('Distribution of {num_col}');

console.log('✅ Histogram rendered');
"""