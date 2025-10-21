"""
Enhanced fallback visualization generator with 3D effects and animations.
Creates visually engaging D3.js visualizations with depth and motion.
"""

def generate_fallback_visualization(pivot_data: dict, user_prompt: str = "") -> str:
    """
    Generate an enhanced 3D animated D3.js visualization as fallback.
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

    num_cols = len(data[0].keys()) if data else 0

    # Check if this has a monthyear column
    has_monthyear = any('month' in col.lower() for col in data[0].keys())
    monthyear_col = None
    if has_monthyear:
        for col in categorical_cols:
            if 'month' in col.lower():
                monthyear_col = col
                break

    # Check if this is a simple list query
    is_list_query = (
        len(numeric_cols) == 0 and
        (num_cols <= 4 or
         'list' in user_prompt.lower() or
         'show' in user_prompt.lower() or
         'all' in user_prompt.lower())
    )

    if is_list_query:
        return generate_card_list()

    # Time series charts
    if monthyear_col and len(numeric_cols) >= 1:
        other_cats = [c for c in categorical_cols if c != monthyear_col]
        if other_cats and len(numeric_cols) >= 1:
            return generate_3d_grouped_bar_chart(monthyear_col, other_cats[0], numeric_cols[0])
        elif len(numeric_cols) >= 1:
            return generate_3d_line_chart(monthyear_col, numeric_cols[0])

    # Standard charts
    if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
        return generate_3d_bar_chart(categorical_cols[0], numeric_cols[0])
    elif len(numeric_cols) >= 2:
        return generate_3d_scatter_plot(numeric_cols[0], numeric_cols[1])
    elif len(numeric_cols) == 1:
        return generate_3d_histogram(numeric_cols[0])
    else:
        return generate_animated_table()


def generate_card_list() -> str:
    """Generate an animated card-based list view."""
    return """
console.log('Rendering card list...');
const data = window.chartData;

if (!data || data.length === 0) {
  d3.select('#chart').html('<div class="alert alert-warning">No data to display</div>');
} else {
  const columns = Object.keys(data[0]);
  const container = d3.select('#chart');
  container.html('');
  
  const header = container.append('div')
    .attr('class', 'card mb-3 shadow-sm')
    .style('opacity', 0);
  
  header.transition().duration(500).style('opacity', 1);
  
  header.append('div')
    .attr('class', 'card-body bg-primary text-white')
    .append('h4')
    .attr('class', 'mb-0')
    .html('<i class="bi bi-list-ul"></i> Results: ' + data.length + ' item(s)');
  
  const cardGrid = container.append('div')
    .attr('class', 'row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4');
  
  const cards = cardGrid.selectAll('.col')
    .data(data)
    .join('div')
    .attr('class', 'col')
    .style('opacity', 0);
  
  cards.transition()
    .duration(600)
    .delay(function(d, i) { return i * 50; })
    .style('opacity', 1);
  
  const cardElements = cards.append('div')
    .attr('class', 'card h-100 shadow-sm')
    .style('cursor', 'pointer')
    .style('transition', 'all 0.3s')
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
  
  cardElements.each(function(d) {
    const body = d3.select(this).append('div').attr('class', 'card-body');
    
    columns.forEach(function(col, idx) {
      if (col.toLowerCase().includes('name') || idx === 0) {
        body.append('h5')
          .attr('class', 'card-title mb-3')
          .html('<i class="bi bi-tag-fill text-primary"></i> ' + d[col]);
      } else {
        const fieldDiv = body.append('div').attr('class', 'mb-2');
        fieldDiv.append('strong').attr('class', 'text-muted').text(col + ': ');
        fieldDiv.append('span').text(d[col] != null ? d[col] : 'N/A');
      }
    });
  });
}
"""


def generate_3d_grouped_bar_chart(time_col: str, group_col: str, value_col: str) -> str:
    """Generate a 3D grouped bar chart."""
    return f"""
console.log('Rendering 3D grouped bar chart...');
const margin = {{top: 60, right: 140, bottom: 100, left: 80}};
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
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
const groups = [...new Set(data.map(d => d['{group_col}']))];

const colorScale = d3.scaleOrdinal()
  .domain(groups)
  .range(['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a']);

const x0 = d3.scaleBand()
  .domain(months)
  .range([0, width])
  .padding(0.3);

const x1 = d3.scaleBand()
  .domain(groups)
  .range([0, x0.bandwidth()])
  .padding(0.1);

const y = d3.scaleLinear()
  .domain([0, d3.max(data, d => d['{value_col}'])])
  .nice()
  .range([height, 0]);

svg.append('g')
  .attr('transform', 'translate(0,' + height + ')')
  .call(d3.axisBottom(x0))
  .selectAll('text')
  .attr('transform', 'rotate(-45)')
  .style('text-anchor', 'end');

svg.append('g').call(d3.axisLeft(y));

const monthGroups = svg.selectAll('.month-group')
  .data(months)
  .join('g')
  .attr('class', 'month-group')
  .attr('transform', d => 'translate(' + x0(d) + ',0)');

monthGroups.each(function(month, monthIdx) {{
  const monthData = data.filter(d => d['{time_col}'] === month);
  const barGroup = d3.select(this).selectAll('.bar-group')
    .data(monthData)
    .join('g')
    .attr('class', 'bar-group');
  
  barGroup.append('rect')
    .attr('x', d => x1(d['{group_col}']) + 3)
    .attr('y', height)
    .attr('width', x1.bandwidth())
    .attr('height', 0)
    .attr('fill', d => d3.color(colorScale(d['{group_col}'])).darker(1))
    .attr('opacity', 0.6)
    .transition()
    .duration(1000)
    .delay(monthIdx * 100)
    .attr('y', d => y(d['{value_col}']) - 3)
    .attr('height', d => height - y(d['{value_col}']));
  
  barGroup.append('rect')
    .attr('x', d => x1(d['{group_col}']))
    .attr('y', height)
    .attr('width', x1.bandwidth())
    .attr('height', 0)
    .attr('fill', d => colorScale(d['{group_col}']))
    .style('cursor', 'pointer')
    .transition()
    .duration(1000)
    .delay(monthIdx * 100)
    .attr('y', d => y(d['{value_col}']))
    .attr('height', d => height - y(d['{value_col}']))
    .selection()
    .on('mouseover', function(event, d) {{
      d3.select(this).attr('opacity', 0.7);
      svg.append('text')
        .attr('class', 'tooltip')
        .attr('x', x0(d['{time_col}']) + x1(d['{group_col}']) + x1.bandwidth() / 2)
        .attr('y', y(d['{value_col}']) - 10)
        .attr('text-anchor', 'middle')
        .style('font-weight', 'bold')
        .text(d['{group_col}'] + ': ' + d['{value_col}']);
    }})
    .on('mouseout', function() {{
      d3.select(this).attr('opacity', 1);
      svg.selectAll('.tooltip').remove();
    }});
}});

const legend = svg.append('g')
  .attr('transform', 'translate(' + (width + 30) + ', 0)');

groups.forEach(function(group, i) {{
  const legendRow = legend.append('g')
    .attr('transform', 'translate(0, ' + (i * 30) + ')');
  
  legendRow.append('rect')
    .attr('width', 20)
    .attr('height', 20)
    .attr('fill', colorScale(group));
  
  legendRow.append('text')
    .attr('x', 25)
    .attr('y', 15)
    .text(group);
}});

svg.append('text')
  .attr('x', width / 2)
  .attr('y', -20)
  .attr('text-anchor', 'middle')
  .style('font-size', '18px')
  .style('font-weight', 'bold')
  .text('{value_col} by {group_col} over time');

console.log('3D grouped bar chart rendered');
"""


def generate_3d_bar_chart(cat_col: str, num_col: str) -> str:
    """Generate a 3D bar chart."""
    return f"""
console.log('Rendering 3D bar chart...');
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
  .domain([0, d3.max(data, d => d['{num_col}'])])
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

const barGroups = svg.selectAll('.bar-group')
  .data(data)
  .join('g')
  .attr('class', 'bar-group');

barGroups.append('rect')
  .attr('x', d => x(d['{cat_col}']) + 4)
  .attr('y', height)
  .attr('width', x.bandwidth())
  .attr('height', 0)
  .attr('fill', (d, i) => d3.color(colorScale(i)).darker(1))
  .attr('opacity', 0.6)
  .transition()
  .duration(1200)
  .delay((d, i) => i * 80)
  .attr('y', d => y(d['{num_col}']) - 4)
  .attr('height', d => height - y(d['{num_col}']));

barGroups.append('rect')
  .attr('x', d => x(d['{cat_col}']))
  .attr('y', height)
  .attr('width', x.bandwidth())
  .attr('height', 0)
  .attr('fill', (d, i) => colorScale(i))
  .style('cursor', 'pointer')
  .transition()
  .duration(1200)
  .delay((d, i) => i * 80)
  .attr('y', d => y(d['{num_col}']))
  .attr('height', d => height - y(d['{num_col}']))
  .selection()
  .on('mouseover', function(event, d) {{
    d3.select(this).attr('opacity', 0.7);
    svg.append('text')
      .attr('class', 'tooltip')
      .attr('x', x(d['{cat_col}']) + x.bandwidth() / 2)
      .attr('y', y(d['{num_col}']) - 10)
      .attr('text-anchor', 'middle')
      .style('font-weight', 'bold')
      .text(d['{cat_col}'] + ': ' + d['{num_col}']);
  }})
  .on('mouseout', function() {{
    d3.select(this).attr('opacity', 1);
    svg.selectAll('.tooltip').remove();
  }});

svg.append('text')
  .attr('x', width / 2)
  .attr('y', -20)
  .attr('text-anchor', 'middle')
  .style('font-size', '18px')
  .style('font-weight', 'bold')
  .text('{cat_col} vs {num_col}');

console.log('3D bar chart rendered');
"""


def generate_3d_line_chart(time_col: str, value_col: str) -> str:
    """Generate a 3D line chart."""
    return f"""
console.log('Rendering 3D line chart...');
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

const data = window.chartData.sort((a, b) => 
  a['{time_col}'].localeCompare(b['{time_col}'])
);

const x = d3.scalePoint()
  .domain(data.map(d => d['{time_col}']))
  .range([0, width])
  .padding(0.5);

const y = d3.scaleLinear()
  .domain([0, d3.max(data, d => d['{value_col}'])])
  .nice()
  .range([height, 0]);

svg.append('g')
  .attr('transform', 'translate(0,' + height + ')')
  .call(d3.axisBottom(x))
  .selectAll('text')
  .attr('transform', 'rotate(-45)')
  .style('text-anchor', 'end');

svg.append('g').call(d3.axisLeft(y));

const area = d3.area()
  .x(d => x(d['{time_col}']))
  .y0(height)
  .y1(d => y(d['{value_col}']))
  .curve(d3.curveMonotoneX);

svg.append('path')
  .datum(data)
  .attr('fill', 'steelblue')
  .attr('opacity', 0.3)
  .attr('d', area);

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

svg.selectAll('.point')
  .data(data)
  .join('circle')
  .attr('class', 'point')
  .attr('cx', d => x(d['{time_col}']))
  .attr('cy', d => y(d['{value_col}']))
  .attr('r', 0)
  .attr('fill', 'steelblue')
  .style('cursor', 'pointer')
  .transition()
  .duration(600)
  .delay((d, i) => 2000 + i * 100)
  .attr('r', 5)
  .selection()
  .on('mouseover', function(event, d) {{
    d3.select(this).attr('r', 8);
    svg.append('text')
      .attr('class', 'tooltip')
      .attr('x', x(d['{time_col}']))
      .attr('y', y(d['{value_col}']) - 15)
      .attr('text-anchor', 'middle')
      .style('font-weight', 'bold')
      .text(d['{time_col}'] + ': ' + d['{value_col}']);
  }})
  .on('mouseout', function() {{
    d3.select(this).attr('r', 5);
    svg.selectAll('.tooltip').remove();
  }});

svg.append('text')
  .attr('x', width / 2)
  .attr('y', -20)
  .attr('text-anchor', 'middle')
  .style('font-size', '18px')
  .style('font-weight', 'bold')
  .text('{value_col} over {time_col}');

console.log('3D line chart rendered');
"""


def generate_3d_scatter_plot(x_col: str, y_col: str) -> str:
    """Generate a 3D scatter plot."""
    return f"""
console.log('Rendering 3D scatter plot...');
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

const colorScale = d3.scaleSequential(d3.interpolateRainbow)
  .domain([0, data.length - 1]);

svg.append('g')
  .attr('transform', 'translate(0,' + height + ')')
  .call(d3.axisBottom(x));

svg.append('g').call(d3.axisLeft(y));

svg.selectAll('.point')
  .data(data)
  .join('circle')
  .attr('class', 'point')
  .attr('cx', d => x(d['{x_col}']))
  .attr('cy', d => y(d['{y_col}']))
  .attr('r', 0)
  .attr('fill', (d, i) => colorScale(i))
  .attr('opacity', 0.7)
  .style('cursor', 'pointer')
  .transition()
  .duration(1000)
  .delay((d, i) => i * 50)
  .attr('r', 8)
  .selection()
  .on('mouseover', function(event, d) {{
    d3.select(this).attr('r', 12).attr('opacity', 1);
    svg.append('text')
      .attr('class', 'tooltip')
      .attr('x', x(d['{x_col}']))
      .attr('y', y(d['{y_col}']) - 15)
      .attr('text-anchor', 'middle')
      .style('font-weight', 'bold')
      .text('(' + d['{x_col}'] + ', ' + d['{y_col}'] + ')');
  }})
  .on('mouseout', function() {{
    d3.select(this).attr('r', 8).attr('opacity', 0.7);
    svg.selectAll('.tooltip').remove();
  }});

svg.append('text')
  .attr('x', width / 2)
  .attr('y', -20)
  .attr('text-anchor', 'middle')
  .style('font-size', '18px')
  .style('font-weight', 'bold')
  .text('{x_col} vs {y_col}');

console.log('3D scatter plot rendered');
"""


def generate_3d_histogram(num_col: str) -> str:
    """Generate a 3D histogram."""
    return f"""
console.log('Rendering 3D histogram...');
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

const colorScale = d3.scaleSequential(d3.interpolateWarm)
  .domain([0, bins.length - 1]);

svg.append('g')
  .attr('transform', 'translate(0,' + height + ')')
  .call(d3.axisBottom(x));

svg.append('g').call(d3.axisLeft(y));

svg.selectAll('.bar')
  .data(bins)
  .join('rect')
  .attr('class', 'bar')
  .attr('x', d => x(d.x0))
  .attr('y', height)
  .attr('width', d => x(d.x1) - x(d.x0) - 1)
  .attr('height', 0)
  .attr('fill', (d, i) => colorScale(i))
  .style('cursor', 'pointer')
  .transition()
  .duration(1200)
  .delay((d, i) => i * 60)
  .attr('y', d => y(d.length))
  .attr('height', d => height - y(d.length))
  .selection()
  .on('mouseover', function(event, d) {{
    d3.select(this).attr('opacity', 0.7);
    svg.append('text')
      .attr('class', 'tooltip')
      .attr('x', x(d.x0) + (x(d.x1) - x(d.x0)) / 2)
      .attr('y', y(d.length) - 10)
      .attr('text-anchor', 'middle')
      .style('font-weight', 'bold')
      .text('Count: ' + d.length);
  }})
  .on('mouseout', function() {{
    d3.select(this).attr('opacity', 1);
    svg.selectAll('.tooltip').remove();
  }});

svg.append('text')
  .attr('x', width / 2)
  .attr('y', -20)
  .attr('text-anchor', 'middle')
  .style('font-size', '18px')
  .style('font-weight', 'bold')
  .text('Distribution of {num_col}');

console.log('3D histogram rendered');
"""


def generate_animated_table() -> str:
    """Generate an animated table."""
    return """
console.log('Rendering animated table...');
const data = window.chartData;

if (!data || data.length === 0) {
  d3.select('#chart').html('<div class="alert alert-warning">No data to display</div>');
} else {
  const columns = Object.keys(data[0]);
  const container = d3.select('#chart');
  container.html('');
  
  const card = container.append('div').attr('class', 'card shadow-sm');
  
  card.append('div')
    .attr('class', 'card-header bg-primary text-white')
    .html('<h5 class="mb-0"><i class="bi bi-table"></i> Query Results (' + data.length + ' rows)</h5>');
  
  const tableContainer = card.append('div')
    .attr('class', 'card-body p-0')
    .append('div')
    .attr('class', 'table-responsive')
    .style('max-height', '600px');
  
  const table = tableContainer.append('table')
    .attr('class', 'table table-hover table-sm mb-0');
  
  const thead = table.append('thead')
    .attr('class', 'table-dark')
    .style('position', 'sticky')
    .style('top', '0');
  
  const headerRow = thead.append('tr');
  headerRow.append('th').attr('class', 'text-center').text('#');
  
  headerRow.selectAll('th.data-col')
    .data(columns)
    .join('th')
    .attr('class', 'data-col')
    .text(d => d);
  
  const tbody = table.append('tbody');
  
  const rows = tbody.selectAll('tr')
    .data(data)
    .join('tr')
    .style('cursor', 'pointer')
    .on('mouseover', function() {
      d3.select(this).style('background-color', '#f0f0f0');
    })
    .on('mouseout', function() {
      d3.select(this).style('background-color', null);
    });
  
  rows.append('td')
    .attr('class', 'text-center')
    .html((d, i) => '<span class="badge bg-primary">' + (i + 1) + '</span>');
  
  rows.selectAll('td.data-cell')
    .data(d => columns.map(col => ({col: col, value: d[col]})))
    .join('td')
    .attr('class', 'data-cell')
    .html(d => {
      if (d.value === null || d.value === undefined) {
        return '<span class="text-muted">null</span>';
      }
      if (d.col.toLowerCase().includes('name')) {
        return '<strong>' + d.value + '</strong>';
      }
      return d.value;
    });
  
  card.append('div')
    .attr('class', 'card-footer text-muted')
    .html('<small>Showing ' + data.length + ' rows × ' + columns.length + ' columns</small>');
}
"""