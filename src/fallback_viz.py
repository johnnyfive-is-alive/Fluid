"""
Enhanced fallback visualization generator with improved item type detection.
Creates visually engaging D3.js visualizations with depth and motion.
Handles stations, resources, and other item types equally well.
"""


def generate_enhanced_card_list() -> str:
    """Generate an animated card-based list view with enhanced animations."""
    return """
console.log('Rendering enhanced card list...');
const data = window.chartData;

if (!data || data.length === 0) {
  d3.select('#chart').html('<div class="alert alert-warning">No data to display</div>');
} else {
  const columns = Object.keys(data[0]);
  const container = d3.select('#chart');
  container.html('');
  
  const header = container.append('div')
    .attr('class', 'card mb-3 shadow-lg')
    .style('opacity', 0)
    .style('transform', 'translateY(-20px)');
  
  header.transition()
    .duration(800)
    .ease(d3.easeCubicOut)
    .style('opacity', 1)
    .style('transform', 'translateY(0)');
  
  header.append('div')
    .attr('class', 'card-body bg-gradient-primary text-white')
    .style('background', 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)')
    .append('h4')
    .attr('class', 'mb-0')
    .html('<i class="bi bi-list-ul"></i> Results: ' + data.length + ' item(s)');
  
  const cardGrid = container.append('div')
    .attr('class', 'row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4');
  
  const cards = cardGrid.selectAll('.col')
    .data(data)
    .join('div')
    .attr('class', 'col')
    .style('opacity', 0)
    .style('transform', 'translateY(30px)');
  
  cards.transition()
    .duration(800)
    .delay(function(d, i) { return 100 + i * 80; })
    .ease(d3.easeCubicOut)
    .style('opacity', 1)
    .style('transform', 'translateY(0)');
  
  const cardElements = cards.append('div')
    .attr('class', 'card h-100 shadow-sm')
    .style('cursor', 'pointer')
    .style('transition', 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)')
    .on('mouseover', function() {
      d3.select(this)
        .style('transform', 'translateY(-8px) scale(1.02)')
        .style('box-shadow', '0 12px 24px rgba(0,0,0,0.25)');
    })
    .on('mouseout', function() {
      d3.select(this)
        .style('transform', 'translateY(0) scale(1)')
        .style('box-shadow', null);
    });
  
  cardElements.each(function(d) {
    const body = d3.select(this).append('div').attr('class', 'card-body');
    
    columns.forEach(function(col, idx) {
      if (col.toLowerCase().includes('name') || idx === 0) {
        body.append('h5')
          .attr('class', 'card-title mb-3')
          .style('color', '#667eea')
          .html('<i class="bi bi-tag-fill"></i> ' + d[col]);
      } else {
        const fieldDiv = body.append('div').attr('class', 'mb-2');
        fieldDiv.append('strong').attr('class', 'text-muted').text(col + ': ');
        fieldDiv.append('span').text(d[col] != null ? d[col] : 'N/A');
      }
    });
  });
}
"""


def generate_stacked_area_or_grouped_bars(time_col: str, group_col: str, value_col: str,
                                          resource_name: str = None, user_prompt: str = "") -> str:
    """
    Generate a stacked area chart for person/resource allocation across products.
    Perfect for queries like "Show Pavan usage month to month by product".
    """
    title_name = resource_name if resource_name else "Resource"

    # Create the title text in Python to avoid JavaScript string escaping issues
    if title_name != "Resource":
        title_text = f"{title_name}'s Time Allocation by Product"
    else:
        title_text = "Time Allocation by Product"

    return f"""
console.log('Rendering stacked area chart for resource allocation...');
const margin = {{top: 80, right: 180, bottom: 100, left: 90}};
const width = Math.max(900, document.getElementById('chart').clientWidth) - margin.left - margin.right;
const height = 600 - margin.top - margin.bottom;

const svg = d3.select('#chart')
  .html('')
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .append('g')
  .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

const data = window.chartData;
const months = [...new Set(data.map(d => d['{time_col}']))].sort();
const products = [...new Set(data.map(d => d['{group_col}']))].sort();

const stackData = months.map(month => {{
  const obj = {{month: month}};
  products.forEach(product => {{
    const record = data.find(d => d['{time_col}'] === month && d['{group_col}'] === product);
    obj[product] = record ? record['{value_col}'] : 0;
  }});
  return obj;
}});

const colorScale = d3.scaleOrdinal()
  .domain(products)
  .range(['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a']);

const x = d3.scalePoint()
  .domain(months)
  .range([0, width])
  .padding(0.3);

const maxY = d3.max(stackData, d => d3.sum(products, product => d[product]));

const y = d3.scaleLinear()
  .domain([0, maxY || 100])
  .nice()
  .range([height, 0]);

svg.append('g')
  .attr('transform', 'translate(0,' + height + ')')
  .call(d3.axisBottom(x))
  .selectAll('text')
  .attr('transform', 'rotate(-45)')
  .style('text-anchor', 'end');

svg.append('g').call(d3.axisLeft(y).tickFormat(d => d + '%'));

svg.append('text')
  .attr('x', width / 2)
  .attr('y', height + 75)
  .attr('text-anchor', 'middle')
  .style('font-size', '14px')
  .text('Month');

svg.append('text')
  .attr('transform', 'rotate(-90)')
  .attr('x', -height / 2)
  .attr('y', -65)
  .attr('text-anchor', 'middle')
  .style('font-size', '14px')
  .style('font-weight', 'bold')
  .text('Time Allocation (%)');

const stack = d3.stack()
  .keys(products);

const series = stack(stackData);

const area = d3.area()
  .x(d => x(d.data.month))
  .y0(d => y(d[0]))
  .y1(d => y(d[1]))
  .curve(d3.curveMonotoneX);

series.forEach(function(s, idx) {{
  svg.append('path')
    .datum(s)
    .attr('fill', colorScale(s.key))
    .attr('opacity', 0.7)
    .attr('d', area)
    .style('cursor', 'pointer');
}});

const legend = svg.append('g')
  .attr('transform', 'translate(' + (width + 30) + ', 0)');

products.forEach(function(product, i) {{
  const legendRow = legend.append('g')
    .attr('transform', 'translate(0, ' + (i * 30) + ')');

  legendRow.append('rect')
    .attr('width', 20)
    .attr('height', 20)
    .attr('fill', colorScale(product));

  legendRow.append('text')
    .attr('x', 25)
    .attr('y', 15)
    .text(product);
}});

svg.append('text')
  .attr('x', width / 2)
  .attr('y', -40)
  .attr('text-anchor', 'middle')
  .style('font-size', '20px')
  .style('font-weight', 'bold')
  .text("{title_text}");

svg.append('text')
  .attr('x', width / 2)
  .attr('y', -20)
  .attr('text-anchor', 'middle')
  .style('font-size', '14px')
  .style('fill', '#666')
  .text('Monthly distribution across products');

console.log('Stacked area chart rendered');
"""

def generate_multi_line_chart(time_col: str, item_col: str, value_col: str) -> str:
    """Generate a multi-line chart showing each item as a separate line."""
    return f"""
console.log('Rendering multi-line chart...');
const margin = {{top: 80, right: 200, bottom: 100, left: 80}};
const width = Math.max(800, document.getElementById('chart').clientWidth) - margin.left - margin.right;
const height = 600 - margin.top - margin.bottom;

const svg = d3.select('#chart')
  .html('')
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .append('g')
  .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

const data = window.chartData;
const itemNames = [...new Set(data.map(d => d['{item_col}']))].sort();
const months = [...new Set(data.map(d => d['{time_col}']))].sort();

const colorScale = d3.scaleOrdinal()
  .domain(itemNames)
  .range(['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a']);

const x = d3.scalePoint()
  .domain(months)
  .range([0, width])
  .padding(0.5);

const y = d3.scaleLinear()
  .domain([0, d3.max(data, d => d['{value_col}']) || 100])
  .nice()
  .range([height, 0]);

svg.append('g')
  .attr('transform', 'translate(0,' + height + ')')
  .call(d3.axisBottom(x))
  .selectAll('text')
  .attr('transform', 'rotate(-45)')
  .style('text-anchor', 'end');

svg.append('g').call(d3.axisLeft(y));

svg.append('text')
  .attr('transform', 'rotate(-90)')
  .attr('x', -height / 2)
  .attr('y', -60)
  .attr('text-anchor', 'middle')
  .style('font-size', '14px')
  .text('{value_col} (%)');

const line = d3.line()
  .x(d => x(d['{time_col}']))
  .y(d => y(d['{value_col}']))
  .curve(d3.curveMonotoneX);

itemNames.forEach(function(itemName, idx) {{
  const itemData = data
    .filter(d => d['{item_col}'] === itemName)
    .sort((a, b) => a['{time_col}'].localeCompare(b['{time_col}']));
  
  if (itemData.length === 0) return;
  
  const path = svg.append('path')
    .datum(itemData)
    .attr('fill', 'none')
    .attr('stroke', colorScale(itemName))
    .attr('stroke-width', 3)
    .attr('d', line);
  
  const totalLength = path.node().getTotalLength();
  path
    .attr('stroke-dasharray', totalLength + ' ' + totalLength)
    .attr('stroke-dashoffset', totalLength)
    .transition()
    .duration(2000)
    .delay(idx * 200)
    .attr('stroke-dashoffset', 0);
}});

const legend = svg.append('g')
  .attr('transform', 'translate(' + (width + 30) + ', 0)');

itemNames.forEach(function(name, i) {{
  const legendRow = legend.append('g')
    .attr('transform', 'translate(0, ' + (i * 30) + ')');
  
  legendRow.append('rect')
    .attr('width', 20)
    .attr('height', 20)
    .attr('fill', colorScale(name));
  
  legendRow.append('text')
    .attr('x', 25)
    .attr('y', 15)
    .text(name);
}});

svg.append('text')
  .attr('x', width / 2)
  .attr('y', -20)
  .attr('text-anchor', 'middle')
  .style('font-size', '18px')
  .style('font-weight', 'bold')
  .text('{value_col} by {item_col} over {time_col}');

console.log('Multi-line chart rendered');
"""


def generate_enhanced_line_chart(time_col: str, value_col: str) -> str:
    """Generate single line chart with area fill."""
    return f"""
console.log('Rendering line chart...');
const margin = {{top: 60, right: 50, bottom: 80, left: 80}};
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

const svg = d3.select('#chart')
  .html('')
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .append('g')
  .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

const data = window.chartData.sort((a, b) => a['{time_col}'].localeCompare(b['{time_col}']));

const x = d3.scalePoint()
  .domain(data.map(d => d['{time_col}']))
  .range([0, width])
  .padding(0.5);

const y = d3.scaleLinear()
  .domain([0, d3.max(data, d => d['{value_col}']) || 100])
  .nice()
  .range([height, 0]);

svg.append('g')
  .attr('transform', 'translate(0,' + height + ')')
  .call(d3.axisBottom(x))
  .selectAll('text')
  .attr('transform', 'rotate(-45)')
  .style('text-anchor', 'end');

svg.append('g').call(d3.axisLeft(y));

const line = d3.line()
  .x(d => x(d['{time_col}']))
  .y(d => y(d['{value_col}']))
  .curve(d3.curveMonotoneX);

const path = svg.append('path')
  .datum(data)
  .attr('fill', 'none')
  .attr('stroke', 'steelblue')
  .attr('stroke-width', 3)
  .attr('d', line);

const totalLength = path.node().getTotalLength();
path
  .attr('stroke-dasharray', totalLength + ' ' + totalLength)
  .attr('stroke-dashoffset', totalLength)
  .transition()
  .duration(2000)
  .attr('stroke-dashoffset', 0);

svg.append('text')
  .attr('x', width / 2)
  .attr('y', -20)
  .attr('text-anchor', 'middle')
  .style('font-size', '18px')
  .style('font-weight', 'bold')
  .text('{value_col} over {time_col}');

console.log('Line chart rendered');
"""


def generate_enhanced_bar_chart(cat_col: str, num_col: str) -> str:
    """Generate bar chart."""
    return f"""
console.log('Rendering bar chart...');
const margin = {{top: 60, right: 40, bottom: 100, left: 80}};
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

const svg = d3.select('#chart')
  .html('')
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .append('g')
  .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

const data = window.chartData;

const x = d3.scaleBand()
  .domain(data.map(d => d['{cat_col}']))
  .range([0, width])
  .padding(0.3);

const y = d3.scaleLinear()
  .domain([0, d3.max(data, d => d['{num_col}']) || 100])
  .nice()
  .range([height, 0]);

const colorScale = d3.scaleSequential(d3.interpolateViridis)
  .domain([0, data.length - 1]);

svg.append('g')
  .attr('transform', 'translate(0,' + height + ')')
  .call(d3.axisBottom(x))
  .selectAll('text')
  .attr('transform', 'rotate(-45)')
  .style('text-anchor', 'end');

svg.append('g').call(d3.axisLeft(y));

svg.selectAll('.bar')
  .data(data)
  .join('rect')
  .attr('x', d => x(d['{cat_col}']))
  .attr('y', height)
  .attr('width', x.bandwidth())
  .attr('height', 0)
  .attr('fill', (d, i) => colorScale(i))
  .transition()
  .duration(1200)
  .delay((d, i) => i * 80)
  .attr('y', d => y(d['{num_col}']))
  .attr('height', d => height - y(d['{num_col}']));

svg.append('text')
  .attr('x', width / 2)
  .attr('y', -20)
  .attr('text-anchor', 'middle')
  .style('font-size', '18px')
  .style('font-weight', 'bold')
  .text('{cat_col} vs {num_col}');

console.log('Bar chart rendered');
"""


def generate_enhanced_scatter_plot(x_col: str, y_col: str) -> str:
    """Generate scatter plot."""
    return f"""
console.log('Rendering scatter plot...');
const margin = {{top: 60, right: 50, bottom: 80, left: 80}};
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

const svg = d3.select('#chart')
  .html('')
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .append('g')
  .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

const data = window.chartData;

const x = d3.scaleLinear()
  .domain(d3.extent(data, d => d['{x_col}']))
  .nice()
  .range([0, width]);

const y = d3.scaleLinear()
  .domain(d3.extent(data, d => d['{y_col}']))
  .nice()
  .range([height, 0]);

svg.append('g')
  .attr('transform', 'translate(0,' + height + ')')
  .call(d3.axisBottom(x));

svg.append('g').call(d3.axisLeft(y));

svg.selectAll('.point')
  .data(data)
  .join('circle')
  .attr('cx', d => x(d['{x_col}']))
  .attr('cy', d => y(d['{y_col}']))
  .attr('r', 0)
  .attr('fill', 'steelblue')
  .attr('opacity', 0.7)
  .transition()
  .duration(1000)
  .delay((d, i) => i * 50)
  .attr('r', 8);

svg.append('text')
  .attr('x', width / 2)
  .attr('y', -20)
  .attr('text-anchor', 'middle')
  .style('font-size', '18px')
  .style('font-weight', 'bold')
  .text('{x_col} vs {y_col}');

console.log('Scatter plot rendered');
"""


def generate_enhanced_histogram(num_col: str) -> str:
    """Generate histogram."""
    return f"""
console.log('Rendering histogram...');
const margin = {{top: 60, right: 50, bottom: 80, left: 80}};
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

const svg = d3.select('#chart')
  .html('')
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .append('g')
  .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

const data = window.chartData.map(d => d['{num_col}']);

const x = d3.scaleLinear()
  .domain(d3.extent(data))
  .nice()
  .range([0, width]);

const histogram = d3.histogram()
  .domain(x.domain())
  .thresholds(x.ticks(20));

const bins = histogram(data);

const y = d3.scaleLinear()
  .domain([0, d3.max(bins, d => d.length)])
  .nice()
  .range([height, 0]);

svg.append('g')
  .attr('transform', 'translate(0,' + height + ')')
  .call(d3.axisBottom(x));

svg.append('g').call(d3.axisLeft(y));

svg.selectAll('.bar')
  .data(bins)
  .join('rect')
  .attr('x', d => x(d.x0))
  .attr('y', height)
  .attr('width', d => x(d.x1) - x(d.x0) - 1)
  .attr('height', 0)
  .attr('fill', 'steelblue')
  .transition()
  .duration(1200)
  .delay((d, i) => i * 60)
  .attr('y', d => y(d.length))
  .attr('height', d => height - y(d.length));

svg.append('text')
  .attr('x', width / 2)
  .attr('y', -20)
  .attr('text-anchor', 'middle')
  .style('font-size', '18px')
  .style('font-weight', 'bold')
  .text('Distribution of {num_col}');

console.log('Histogram rendered');
"""


def generate_enhanced_table() -> str:
    """Generate table."""
    return """
console.log('Rendering table...');
const data = window.chartData;

if (!data || data.length === 0) {
  d3.select('#chart').html('<div class="alert alert-warning">No data</div>');
} else {
  const columns = Object.keys(data[0]);
  const container = d3.select('#chart');
  container.html('');
  
  const card = container.append('div').attr('class', 'card');
  card.append('div')
    .attr('class', 'card-header bg-primary text-white')
    .html('<h5>Results (' + data.length + ' rows)</h5>');
  
  const table = card.append('div')
    .attr('class', 'card-body p-0')
    .append('table')
    .attr('class', 'table table-sm');
  
  const thead = table.append('thead').attr('class', 'table-dark');
  thead.append('tr')
    .selectAll('th')
    .data(['#'].concat(columns))
    .join('th')
    .text(d => d);
  
  const tbody = table.append('tbody');
  tbody.selectAll('tr')
    .data(data)
    .join('tr')
    .selectAll('td')
    .data((d, i) => [i + 1].concat(columns.map(col => d[col])))
    .join('td')
    .text(d => d);
}
"""


def generate_fallback_visualization(pivot_data: dict, user_prompt: str = "") -> str:
    """
    Generate an enhanced animated D3.js visualization as fallback.
    Detects data structure and creates appropriate chart type.
    """
    numeric_cols = pivot_data.get('numeric_columns', [])
    categorical_cols = pivot_data.get('categorical_columns', [])
    data = pivot_data.get('data', [])

    if not data:
        return """
d3.select('#chart')
  .append('div')
  .attr('class', 'alert alert-warning')
  .html('<i class="bi bi-exclamation-triangle"></i> No data returned from query');
"""

    # Enhanced detection logic
    monthyear_col = None
    for col in categorical_cols:
        if 'month' in col.lower() or col.lower() in ['monthyear', 'month_year', 'yearmonth']:
            monthyear_col = col
            break

    item_col = None
    for col in categorical_cols:
        if 'itemname' in col.lower() or col.lower() in ['item', 'name', 'station', 'resource']:
            item_col = col
            break

    group_col = None
    for col in categorical_cols:
        if col.lower() in ['product', 'productname', 'group', 'category'] and col != monthyear_col:
            group_col = col
            break

    # Extract person name from query
    resource_name = None
    if 'usage' in user_prompt.lower() or 'loading' in user_prompt.lower():
        words = user_prompt.split()
        for i, word in enumerate(words):
            if word.lower() in ['usage', 'loading', 'capacity', 'utilization', 'time']:
                if i > 0:
                    resource_name = words[i-1].strip(',')
                    break

    # Check if list query
    is_list_query = (
        len(numeric_cols) == 0 and
        ('list' in user_prompt.lower() or 'show all' in user_prompt.lower())
    )

    if is_list_query:
        return generate_enhanced_card_list()

    # PRIORITY 1: Time series with product breakdown
    if monthyear_col and group_col and len(numeric_cols) >= 1:
        return generate_stacked_area_or_grouped_bars(
            monthyear_col, group_col, numeric_cols[0],
            resource_name=resource_name, user_prompt=user_prompt
        )

    # PRIORITY 2: Time series with item breakdown
    if monthyear_col and item_col and len(numeric_cols) >= 1:
        return generate_multi_line_chart(monthyear_col, item_col, numeric_cols[0])

    # PRIORITY 3: Simple time series
    if monthyear_col and len(numeric_cols) >= 1:
        return generate_enhanced_line_chart(monthyear_col, numeric_cols[0])

    # PRIORITY 4: Item comparison
    if item_col and len(numeric_cols) >= 1:
        return generate_enhanced_bar_chart(item_col, numeric_cols[0])

    # PRIORITY 5: Standard categorical vs numeric
    if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
        return generate_enhanced_bar_chart(categorical_cols[0], numeric_cols[0])

    # PRIORITY 6: Scatter plot
    if len(numeric_cols) >= 2:
        return generate_enhanced_scatter_plot(numeric_cols[0], numeric_cols[1])

    # PRIORITY 7: Histogram
    if len(numeric_cols) == 1:
        return generate_enhanced_histogram(numeric_cols[0])

    # FALLBACK: Table
    return generate_enhanced_table()