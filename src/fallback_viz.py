"""
D3.js visualization generator matching Chart.js stacked bar chart style.
Enhanced with larger, clearer font sizes for better readability.
"""
import re


def extract_resource_name(user_prompt: str) -> str:
    """Extract person/resource name from query - now more flexible."""
    name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
    matches = re.findall(name_pattern, user_prompt)

    if matches:
        common_words = {'Show', 'Give', 'Display', 'Usage', 'Loading', 'Month',
                        'Year', 'Next', 'Time', 'For', 'The', 'Allocation',
                        'Capacity', 'Utilization', 'By', 'Product', 'Station',
                        'Resource', 'All', 'List', 'Get', 'Find', 'Search'}
        names = [m for m in matches if m not in common_words]
        if names:
            return names[0]
    return None


def generate_stacked_bar_d3(time_col: str, group_col: str, value_col: str,
                             resource_name: str = None, user_prompt: str = "") -> str:
    """Generate D3.js stacked bar chart matching Chart.js style from resource/station/unit pages."""

    if not resource_name:
        resource_name = extract_resource_name(user_prompt)

    # Escape single quotes in resource name for JavaScript
    safe_name = resource_name.replace("'", "\\'") if resource_name else None

    if safe_name:
        title_js = f"'{safe_name}\\'s Loading Allocation by Product and Month (%)'"
    else:
        title_js = "'Loading Allocation by Product and Month (%)'"

    return f"""
console.log('Rendering D3.js stacked bar chart...');
const margin = {{top: 80, right: 180, bottom: 120, left: 100}};
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

const colors = [
    'rgba(54, 162, 235, 0.8)',
    'rgba(255, 99, 132, 0.8)',
    'rgba(75, 192, 192, 0.8)',
    'rgba(255, 206, 86, 0.8)',
    'rgba(153, 102, 255, 0.8)',
    'rgba(255, 159, 64, 0.8)',
    'rgba(199, 199, 199, 0.8)',
    'rgba(83, 102, 255, 0.8)',
    'rgba(255, 99, 255, 0.8)',
    'rgba(99, 255, 132, 0.8)'
];

const colorScale = d3.scaleOrdinal()
  .domain(products)
  .range(colors);

const stackData = months.map(month => {{
  const obj = {{month: month}};
  products.forEach(product => {{
    const record = data.find(d => d['{time_col}'] === month && d['{group_col}'] === product);
    obj[product] = record ? record['{value_col}'] : 0;
  }});
  return obj;
}});

const stack = d3.stack()
  .keys(products);

const series = stack(stackData);

const x = d3.scaleBand()
  .domain(months)
  .range([0, width])
  .padding(0.3);

const y = d3.scaleLinear()
  .domain([0, 100])
  .range([height, 0]);

svg.append('g')
  .attr('transform', 'translate(0,' + height + ')')
  .call(d3.axisBottom(x))
  .selectAll('text')
  .attr('transform', 'rotate(-45)')
  .style('text-anchor', 'end')
  .style('font-size', '16px')
  .style('font-weight', '500');

const yAxis = d3.axisLeft(y)
  .tickFormat(d => d + '%');

svg.append('g')
  .call(yAxis)
  .selectAll('text')
  .style('font-size', '16px')
  .style('font-weight', '500');

svg.append('text')
  .attr('x', width / 2)
  .attr('y', height + 85)
  .attr('text-anchor', 'middle')
  .style('font-size', '18px')
  .style('font-weight', 'bold')
  .text('Month');

svg.append('text')
  .attr('transform', 'rotate(-90)')
  .attr('y', -70)
  .attr('x', -height / 2)
  .attr('text-anchor', 'middle')
  .style('font-size', '18px')
  .style('font-weight', 'bold')
  .text('Allocation %');

series.forEach((productData, idx) => {{
  svg.selectAll('.bar-' + idx)
    .data(productData)
    .join('rect')
    .attr('class', 'bar-' + idx)
    .attr('x', d => x(d.data.month))
    .attr('y', height)
    .attr('width', x.bandwidth())
    .attr('height', 0)
    .attr('fill', colorScale(productData.key))
    .attr('stroke', colorScale(productData.key).replace('0.8', '1'))
    .attr('stroke-width', 2)
    .style('cursor', 'pointer')
    .on('mouseover', function(event, d) {{
      d3.select(this).attr('opacity', 0.8);
      const value = d[1] - d[0];
      const tooltip = d3.select('body').append('div')
        .attr('class', 'tooltip')
        .style('position', 'absolute')
        .style('background', 'rgba(0,0,0,0.8)')
        .style('color', 'white')
        .style('padding', '10px')
        .style('border-radius', '4px')
        .style('pointer-events', 'none')
        .style('font-size', '14px')
        .style('left', event.pageX + 10 + 'px')
        .style('top', event.pageY - 10 + 'px')
        .html(productData.key + ': ' + value.toFixed(1) + '%');
    }})
    .on('mouseout', function() {{
      d3.select(this).attr('opacity', 1);
      d3.selectAll('.tooltip').remove();
    }})
    .transition()
    .duration(800)
    .delay((d, i) => idx * 100 + i * 50)
    .attr('y', d => y(d[1]))
    .attr('height', d => y(d[0]) - y(d[1]));
}});

const legend = svg.append('g')
  .attr('transform', 'translate(' + (width + 30) + ', 0)');

products.forEach((product, i) => {{
  const legendRow = legend.append('g')
    .attr('transform', 'translate(0, ' + (i * 35) + ')');

  legendRow.append('rect')
    .attr('width', 22)
    .attr('height', 22)
    .attr('fill', colorScale(product));

  legendRow.append('text')
    .attr('x', 28)
    .attr('y', 16)
    .style('font-size', '16px')
    .style('font-weight', '500')
    .text(product);
}});

svg.append('text')
  .attr('x', width / 2)
  .attr('y', -45)
  .attr('text-anchor', 'middle')
  .style('font-size', '22px')
  .style('font-weight', 'bold')
  .text({title_js});

console.log('Stacked bar chart rendered');
"""


def generate_stacked_area_or_grouped_bars(time_col: str, group_col: str, value_col: str,
                                          resource_name: str = None, user_prompt: str = "") -> str:
    """Main entry point - always use stacked bars for loading queries."""
    return generate_stacked_bar_d3(time_col, group_col, value_col, resource_name, user_prompt)


def generate_grouped_bar_chart(time_col: str, group_col: str, value_col: str, user_prompt: str = "") -> str:
    """Grouped bar chart for non-loading queries."""
    return f"""
console.log('Rendering grouped bar chart...');
const margin = {{top: 80, right: 200, bottom: 120, left: 100}};
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

const colorScale = d3.scaleOrdinal()
  .domain(products)
  .range(['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a']);

const x0 = d3.scaleBand()
  .domain(months)
  .range([0, width])
  .padding(0.2);

const x1 = d3.scaleBand()
  .domain(products)
  .range([0, x0.bandwidth()])
  .padding(0.05);

const y = d3.scaleLinear()
  .domain([0, d3.max(data, d => d['{value_col}']) || 100])
  .nice()
  .range([height, 0]);

svg.append('g')
  .attr('transform', 'translate(0,' + height + ')')
  .call(d3.axisBottom(x0))
  .selectAll('text')
  .attr('transform', 'rotate(-45)')
  .style('text-anchor', 'end')
  .style('font-size', '16px')
  .style('font-weight', '500');

svg.append('g')
  .call(d3.axisLeft(y))
  .selectAll('text')
  .style('font-size', '16px')
  .style('font-weight', '500');

products.forEach(function(product, productIdx) {{
  svg.selectAll('.bar-' + productIdx)
    .data(data.filter(d => d['{group_col}'] === product))
    .join('rect')
    .attr('x', d => x0(d['{time_col}']) + x1(product))
    .attr('y', height)
    .attr('width', x1.bandwidth())
    .attr('height', 0)
    .attr('fill', colorScale(product))
    .transition()
    .duration(1200)
    .delay((d, i) => productIdx * 100 + i * 80)
    .attr('y', d => y(d['{value_col}']))
    .attr('height', d => height - y(d['{value_col}']));
}});

svg.append('text')
  .attr('x', width / 2)
  .attr('y', -45)
  .attr('text-anchor', 'middle')
  .style('font-size', '22px')
  .style('font-weight', 'bold')
  .text('Usage by Product and Month');

console.log('Grouped bar chart rendered');
"""


def generate_multi_line_chart(time_col: str, item_col: str, value_col: str) -> str:
    """Multi-line chart for comparing multiple items."""
    return f"""
console.log('Rendering multi-line chart...');
const margin = {{top: 80, right: 220, bottom: 120, left: 100}};
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
  .style('text-anchor', 'end')
  .style('font-size', '16px')
  .style('font-weight', '500');

svg.append('g')
  .call(d3.axisLeft(y))
  .selectAll('text')
  .style('font-size', '16px')
  .style('font-weight', '500');

const line = d3.line()
  .x(d => x(d['{time_col}']))
  .y(d => y(d['{value_col}']))
  .curve(d3.curveMonotoneX);

itemNames.forEach((itemName, idx) => {{
  const itemData = data.filter(d => d['{item_col}'] === itemName).sort((a, b) => a['{time_col}'].localeCompare(b['{time_col}']));
  
  svg.append('path')
    .datum(itemData)
    .attr('fill', 'none')
    .attr('stroke', colorScale(itemName))
    .attr('stroke-width', 3)
    .attr('d', line);
}});

const legend = svg.append('g')
  .attr('transform', 'translate(' + (width + 30) + ', 0)');

itemNames.forEach(function(itemName, i) {{
  const legendRow = legend.append('g')
    .attr('transform', 'translate(0, ' + (i * 35) + ')');
  legendRow.append('line')
    .attr('x1', 0).attr('x2', 25).attr('y1', 12).attr('y2', 12)
    .attr('stroke', colorScale(itemName)).attr('stroke-width', 3);
  legendRow.append('text')
    .attr('x', 30).attr('y', 17)
    .style('font-size', '16px')
    .style('font-weight', '500')
    .text(itemName);
}});

svg.append('text')
  .attr('x', width / 2).attr('y', -45).attr('text-anchor', 'middle')
  .style('font-size', '22px').style('font-weight', 'bold')
  .text('Loading Over Time');
"""


def generate_enhanced_line_chart(time_col: str, value_col: str) -> str:
    """Simple line chart."""
    return f"""
const margin = {{top: 70, right: 50, bottom: 100, left: 100}};
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

const svg = d3.select('#chart').html('').append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .append('g').attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

const data = window.chartData.sort((a, b) => a['{time_col}'].localeCompare(b['{time_col}']));
const x = d3.scalePoint().domain(data.map(d => d['{time_col}'])).range([0, width]).padding(0.5);
const y = d3.scaleLinear().domain([0, d3.max(data, d => d['{value_col}']) || 100]).nice().range([height, 0]);

svg.append('g')
  .attr('transform', 'translate(0,' + height + ')')
  .call(d3.axisBottom(x))
  .selectAll('text')
  .style('font-size', '16px')
  .style('font-weight', '500');

svg.append('g')
  .call(d3.axisLeft(y))
  .selectAll('text')
  .style('font-size', '16px')
  .style('font-weight', '500');

const line = d3.line().x(d => x(d['{time_col}'])).y(d => y(d['{value_col}'])).curve(d3.curveMonotoneX);
svg.append('path').datum(data).attr('fill', 'none').attr('stroke', 'steelblue').attr('stroke-width', 3).attr('d', line);
"""


def generate_enhanced_bar_chart(cat_col: str, num_col: str) -> str:
    """Bar chart."""
    return f"""
const margin = {{top: 70, right: 40, bottom: 120, left: 100}};
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

const svg = d3.select('#chart').html('').append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .append('g').attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

const data = window.chartData;
const x = d3.scaleBand().domain(data.map(d => d['{cat_col}'])).range([0, width]).padding(0.3);
const y = d3.scaleLinear().domain([0, d3.max(data, d => d['{num_col}']) || 100]).nice().range([height, 0]);

svg.append('g')
  .attr('transform', 'translate(0,' + height + ')')
  .call(d3.axisBottom(x))
  .selectAll('text')
  .attr('transform', 'rotate(-45)')
  .style('text-anchor', 'end')
  .style('font-size', '16px')
  .style('font-weight', '500');

svg.append('g')
  .call(d3.axisLeft(y))
  .selectAll('text')
  .style('font-size', '16px')
  .style('font-weight', '500');

svg.selectAll('.bar').data(data).join('rect')
  .attr('x', d => x(d['{cat_col}'])).attr('y', d => y(d['{num_col}']))
  .attr('width', x.bandwidth()).attr('height', d => height - y(d['{num_col}']))
  .attr('fill', 'steelblue');
"""


def generate_enhanced_scatter_plot(x_col: str, y_col: str) -> str:
    """Scatter plot."""
    return f"""
const margin = {{top: 70, right: 50, bottom: 100, left: 100}};
const svg = d3.select('#chart').html('').append('svg').attr('width', 800).attr('height', 600)
  .append('g').attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');
const data = window.chartData;
const x = d3.scaleLinear().domain(d3.extent(data, d => d['{x_col}'])).nice().range([0, 600]);
const y = d3.scaleLinear().domain(d3.extent(data, d => d['{y_col}'])).nice().range([400, 0]);

svg.append('g')
  .attr('transform', 'translate(0,400)')
  .call(d3.axisBottom(x))
  .selectAll('text')
  .style('font-size', '16px')
  .style('font-weight', '500');

svg.append('g')
  .call(d3.axisLeft(y))
  .selectAll('text')
  .style('font-size', '16px')
  .style('font-weight', '500');

svg.selectAll('circle').data(data).join('circle')
  .attr('cx', d => x(d['{x_col}'])).attr('cy', d => y(d['{y_col}']))
  .attr('r', 6).attr('fill', 'steelblue').attr('opacity', 0.7);
"""


def generate_enhanced_histogram(num_col: str) -> str:
    """Histogram."""
    return """
d3.select('#chart').html('<div class="alert alert-info">Histogram view</div>');
"""


def generate_enhanced_table() -> str:
    """Table."""
    return """
const data = window.chartData;
if (!data || data.length === 0) {
  d3.select('#chart').html('<div class="alert alert-warning">No data</div>');
} else {
  const columns = Object.keys(data[0]);
  const container = d3.select('#chart').html('');
  const card = container.append('div').attr('class', 'card');
  card.append('div').attr('class', 'card-header bg-primary text-white')
    .html('<h5>Results (' + data.length + ' rows)</h5>');
  const table = card.append('div').attr('class', 'card-body p-0')
    .append('table').attr('class', 'table table-sm');
  const thead = table.append('thead').attr('class', 'table-dark');
  thead.append('tr').selectAll('th').data(['#'].concat(columns)).join('th').text(d => d);
  const tbody = table.append('tbody');
  tbody.selectAll('tr').data(data).join('tr').selectAll('td')
    .data((d, i) => [i + 1].concat(columns.map(col => d[col]))).join('td').text(d => d);
}
"""


def generate_enhanced_card_list() -> str:
    """Card list."""
    return """
const data = window.chartData;
if (!data || data.length === 0) {
  d3.select('#chart').html('<div class="alert alert-warning">No data found</div>');
} else {
  const container = d3.select('#chart').html('');
  const row = container.append('div').attr('class', 'row g-3');
  row.selectAll('.col').data(data).join('div').attr('class', 'col-md-6 col-lg-4')
    .append('div').attr('class', 'card h-100 border-primary')
    .html(d => {
      let content = '<div class="card-body">';
      for (const [key, value] of Object.entries(d)) {
        if (key !== 'id') content += `<p class="mb-2"><strong>${key}:</strong> ${value}</p>`;
      }
      return content + '</div>';
    });
}
"""


def generate_fallback_visualization(pivot_data: dict, user_prompt: str = "") -> str:
    """Main entry point for visualization generation."""
    numeric_cols = pivot_data.get('numeric_columns', [])
    categorical_cols = pivot_data.get('categorical_columns', [])
    data = pivot_data.get('data', [])

    if not data:
        return "d3.select('#chart').append('div').attr('class', 'alert alert-warning').html('No data');"

    monthyear_col = next((col for col in categorical_cols if 'month' in col.lower()), None)
    item_col = next((col for col in categorical_cols if 'itemname' in col.lower()), None)
    group_col = next((col for col in categorical_cols if col.lower() in ['product', 'productname']), None)

    resource_name = extract_resource_name(user_prompt)

    is_list_query = len(numeric_cols) == 0 and ('list' in user_prompt.lower() or 'show all' in user_prompt.lower())
    if is_list_query:
        return generate_enhanced_card_list()

    if monthyear_col and group_col and len(numeric_cols) >= 1:
        return generate_stacked_area_or_grouped_bars(monthyear_col, group_col, numeric_cols[0], resource_name, user_prompt)

    if monthyear_col and item_col and len(numeric_cols) >= 1:
        return generate_multi_line_chart(monthyear_col, item_col, numeric_cols[0])

    if monthyear_col and len(numeric_cols) >= 1:
        return generate_enhanced_line_chart(monthyear_col, numeric_cols[0])

    if item_col and len(numeric_cols) >= 1:
        return generate_enhanced_bar_chart(item_col, numeric_cols[0])

    if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
        return generate_enhanced_bar_chart(categorical_cols[0], numeric_cols[0])

    if len(numeric_cols) >= 2:
        return generate_enhanced_scatter_plot(numeric_cols[0], numeric_cols[1])

    if len(numeric_cols) == 1:
        return generate_enhanced_histogram(numeric_cols[0])

    return generate_enhanced_table()