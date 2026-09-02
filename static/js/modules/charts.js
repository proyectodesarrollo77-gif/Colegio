/* ==========================================================================
   PL_SGE - Graficos SVG nativos (sin dependencias externas)
   Soporta: linea, area, barras, barras horizontales, dona y sparkline.
   ========================================================================== */

const PALETTE = ["#4F46E5", "#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#A855F7", "#14B8A6", "#EC4899"];

const NS = "http://www.w3.org/2000/svg";

function svgEl(tag, attrs = {}) {
  const node = document.createElementNS(NS, tag);
  Object.entries(attrs).forEach(([key, value]) => {
    if (value !== null && value !== undefined) node.setAttribute(key, value);
  });
  return node;
}

function niceMax(value) {
  if (value <= 0) return 10;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const normalized = value / magnitude;
  const step = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  return step * magnitude;
}

function tooltipFor(container) {
  let tooltip = container.querySelector(".chart-tooltip");
  if (!tooltip) {
    tooltip = document.createElement("div");
    tooltip.className = "chart-tooltip";
    container.style.position = "relative";
    container.appendChild(tooltip);
  }
  return tooltip;
}

function attachTooltip(container, node, text) {
  const tooltip = tooltipFor(container);
  node.addEventListener("mousemove", (event) => {
    const rect = container.getBoundingClientRect();
    tooltip.textContent = text;
    tooltip.style.left = `${event.clientX - rect.left}px`;
    tooltip.style.top = `${event.clientY - rect.top}px`;
    tooltip.classList.add("is-visible");
  });
  node.addEventListener("mouseleave", () => tooltip.classList.remove("is-visible"));
}

/* --------------------------------------------------------------------------
   Grafico de lineas / area
   -------------------------------------------------------------------------- */
export function lineChart(container, { labels = [], series = [], height = 240, area = true, formatter = (v) => v } = {}) {
  container.innerHTML = "";
  const width = container.clientWidth || 640;
  const padding = { top: 16, right: 16, bottom: 28, left: 42 };
  const innerWidth = Math.max(width - padding.left - padding.right, 10);
  const innerHeight = height - padding.top - padding.bottom;

  const allValues = series.flatMap((serie) => serie.data);
  const max = niceMax(Math.max(...allValues, 1));
  const stepX = labels.length > 1 ? innerWidth / (labels.length - 1) : innerWidth;

  const svg = svgEl("svg", { class: "chart", viewBox: `0 0 ${width} ${height}`, preserveAspectRatio: "none" });

  for (let i = 0; i <= 4; i += 1) {
    const y = padding.top + (innerHeight / 4) * i;
    svg.appendChild(
      svgEl("line", {
        x1: padding.left, y1: y, x2: width - padding.right, y2: y,
        stroke: "var(--border-subtle)", "stroke-width": 1,
      })
    );
    const label = svgEl("text", {
      x: padding.left - 8, y: y + 4, "text-anchor": "end",
      fill: "var(--text-muted)", "font-size": 10,
    });
    label.textContent = formatter(Math.round(max - (max / 4) * i));
    svg.appendChild(label);
  }

  labels.forEach((label, index) => {
    const x = padding.left + stepX * index;
    const text = svgEl("text", {
      x, y: height - 8, "text-anchor": "middle", fill: "var(--text-muted)", "font-size": 10,
    });
    text.textContent = label;
    svg.appendChild(text);
  });

  series.forEach((serie, serieIndex) => {
    const color = serie.color || PALETTE[serieIndex % PALETTE.length];
    const points = serie.data.map((value, index) => [
      padding.left + stepX * index,
      padding.top + innerHeight - (value / max) * innerHeight,
    ]);

    if (area && points.length) {
      const gradientId = `grad-${Math.random().toString(36).slice(2, 8)}`;
      const defs = svgEl("defs");
      const gradient = svgEl("linearGradient", { id: gradientId, x1: 0, y1: 0, x2: 0, y2: 1 });
      gradient.appendChild(svgEl("stop", { offset: "0%", "stop-color": color, "stop-opacity": 0.24 }));
      gradient.appendChild(svgEl("stop", { offset: "100%", "stop-color": color, "stop-opacity": 0 }));
      defs.appendChild(gradient);
      svg.appendChild(defs);

      const areaPath = `M ${points[0][0]} ${padding.top + innerHeight} ` +
        points.map(([x, y]) => `L ${x} ${y}`).join(" ") +
        ` L ${points[points.length - 1][0]} ${padding.top + innerHeight} Z`;
      svg.appendChild(svgEl("path", { d: areaPath, fill: `url(#${gradientId})` }));
    }

    const linePath = points.map(([x, y], index) => `${index === 0 ? "M" : "L"} ${x} ${y}`).join(" ");
    svg.appendChild(
      svgEl("path", {
        d: linePath, fill: "none", stroke: color, "stroke-width": 2,
        "stroke-linecap": "round", "stroke-linejoin": "round",
      })
    );

    points.forEach(([x, y], index) => {
      const dot = svgEl("circle", { cx: x, cy: y, r: 3.5, fill: "var(--bg-surface)", stroke: color, "stroke-width": 2 });
      attachTooltip(container, dot, `${labels[index]}: ${formatter(serie.data[index])}`);
      svg.appendChild(dot);
    });
  });

  container.appendChild(svg);
  if (series.length > 1) container.appendChild(legend(series));
  return svg;
}

/* --------------------------------------------------------------------------
   Barras verticales
   -------------------------------------------------------------------------- */
export function barChart(container, { labels = [], series = [], height = 240, formatter = (v) => v } = {}) {
  container.innerHTML = "";
  const width = container.clientWidth || 640;
  const padding = { top: 16, right: 16, bottom: 30, left: 42 };
  const innerWidth = Math.max(width - padding.left - padding.right, 10);
  const innerHeight = height - padding.top - padding.bottom;

  const max = niceMax(Math.max(...series.flatMap((serie) => serie.data), 1));
  const groupWidth = innerWidth / Math.max(labels.length, 1);
  const barWidth = Math.min((groupWidth * 0.68) / series.length, 44);

  const svg = svgEl("svg", { class: "chart", viewBox: `0 0 ${width} ${height}` });

  for (let i = 0; i <= 4; i += 1) {
    const y = padding.top + (innerHeight / 4) * i;
    svg.appendChild(
      svgEl("line", { x1: padding.left, y1: y, x2: width - padding.right, y2: y, stroke: "var(--border-subtle)" })
    );
    const label = svgEl("text", { x: padding.left - 8, y: y + 4, "text-anchor": "end", fill: "var(--text-muted)", "font-size": 10 });
    label.textContent = formatter(Math.round(max - (max / 4) * i));
    svg.appendChild(label);
  }

  labels.forEach((label, index) => {
    const groupX = padding.left + groupWidth * index;
    series.forEach((serie, serieIndex) => {
      const value = serie.data[index] || 0;
      const barHeight = (value / max) * innerHeight;
      const x = groupX + groupWidth / 2 - (barWidth * series.length) / 2 + barWidth * serieIndex;
      const y = padding.top + innerHeight - barHeight;
      const rect = svgEl("rect", {
        x, y: padding.top + innerHeight, width: barWidth - 3, height: 0,
        rx: 4, fill: serie.color || PALETTE[serieIndex % PALETTE.length],
      });
      svg.appendChild(rect);
      attachTooltip(container, rect, `${label} - ${serie.name || ""}: ${formatter(value)}`);
      requestAnimationFrame(() => {
        rect.style.transition = "y .6s cubic-bezier(.16,1,.3,1), height .6s cubic-bezier(.16,1,.3,1)";
        rect.setAttribute("y", y);
        rect.setAttribute("height", Math.max(barHeight, 0));
      });
    });
    const text = svgEl("text", {
      x: groupX + groupWidth / 2, y: height - 8, "text-anchor": "middle",
      fill: "var(--text-muted)", "font-size": 10,
    });
    text.textContent = label;
    svg.appendChild(text);
  });

  container.appendChild(svg);
  if (series.length > 1) container.appendChild(legend(series));
  return svg;
}

/* --------------------------------------------------------------------------
   Barras horizontales
   -------------------------------------------------------------------------- */
export function horizontalBars(container, { items = [], formatter = (v) => v } = {}) {
  container.innerHTML = "";
  const max = Math.max(...items.map((item) => item.value), 1);
  items.forEach((item, index) => {
    const row = document.createElement("div");
    row.className = "meter-row";
    row.innerHTML = `
      <div class="meter-row__label truncate" title="${item.label}">${item.label}</div>
      <div class="progress" style="flex:1">
        <div class="progress__bar" style="width:0;background:${item.color || PALETTE[index % PALETTE.length]}"></div>
      </div>
      <div class="meter-row__value">${formatter(item.value)}</div>`;
    container.appendChild(row);
    requestAnimationFrame(() => {
      row.querySelector(".progress__bar").style.width = `${(item.value / max) * 100}%`;
    });
  });
}

/* --------------------------------------------------------------------------
   Dona
   -------------------------------------------------------------------------- */
export function donutChart(container, { items = [], size = 200, thickness = 26, centerLabel = "", centerValue = "" } = {}) {
  container.innerHTML = "";
  const total = items.reduce((acc, item) => acc + item.value, 0) || 1;
  const radius = (size - thickness) / 2;
  const circumference = 2 * Math.PI * radius;

  const svg = svgEl("svg", { class: "chart", viewBox: `0 0 ${size} ${size}`, width: size, height: size });
  const group = svgEl("g", { transform: `rotate(-90 ${size / 2} ${size / 2})` });

  svg.appendChild(
    svgEl("circle", {
      cx: size / 2, cy: size / 2, r: radius, fill: "none",
      stroke: "var(--bg-surface-3)", "stroke-width": thickness,
    })
  );

  let offset = 0;
  items.forEach((item, index) => {
    const fraction = item.value / total;
    const arc = svgEl("circle", {
      cx: size / 2, cy: size / 2, r: radius, fill: "none",
      stroke: item.color || PALETTE[index % PALETTE.length],
      "stroke-width": thickness,
      "stroke-dasharray": `${circumference * fraction} ${circumference}`,
      "stroke-dashoffset": -offset,
      "stroke-linecap": "butt",
    });
    attachTooltip(container, arc, `${item.label}: ${item.value} (${(fraction * 100).toFixed(1)}%)`);
    group.appendChild(arc);
    offset += circumference * fraction;
  });

  svg.appendChild(group);

  if (centerValue !== "") {
    const value = svgEl("text", {
      x: size / 2, y: size / 2 - 2, "text-anchor": "middle",
      fill: "var(--text-primary)", "font-size": 26, "font-weight": 600,
    });
    value.textContent = centerValue;
    svg.appendChild(value);
    const label = svgEl("text", {
      x: size / 2, y: size / 2 + 18, "text-anchor": "middle",
      fill: "var(--text-muted)", "font-size": 11,
    });
    label.textContent = centerLabel;
    svg.appendChild(label);
  }

  const wrapper = document.createElement("div");
  wrapper.style.display = "flex";
  wrapper.style.alignItems = "center";
  wrapper.style.gap = "24px";
  wrapper.style.flexWrap = "wrap";
  wrapper.appendChild(svg);

  const list = document.createElement("div");
  list.style.flex = "1";
  list.style.minWidth = "160px";
  items.forEach((item, index) => {
    const row = document.createElement("div");
    row.className = "row-between";
    row.style.padding = "5px 0";
    row.innerHTML = `<div class="chart-legend__item">
        <span class="chart-legend__swatch" style="background:${item.color || PALETTE[index % PALETTE.length]}"></span>
        <span>${item.label}</span></div>
      <strong class="text-sm">${item.value}</strong>`;
    list.appendChild(row);
  });
  wrapper.appendChild(list);
  container.appendChild(wrapper);
  return svg;
}

/* --------------------------------------------------------------------------
   Sparkline
   -------------------------------------------------------------------------- */
export function sparkline(container, { data = [], color = PALETTE[0], height = 38 } = {}) {
  container.innerHTML = "";
  const width = container.clientWidth || 120;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;
  const stepX = data.length > 1 ? width / (data.length - 1) : width;
  const points = data.map((value, index) => [index * stepX, height - ((value - min) / range) * (height - 4) - 2]);

  const svg = svgEl("svg", { class: "chart", viewBox: `0 0 ${width} ${height}` });
  svg.appendChild(
    svgEl("path", {
      d: points.map(([x, y], index) => `${index === 0 ? "M" : "L"} ${x} ${y}`).join(" "),
      fill: "none", stroke: color, "stroke-width": 2, "stroke-linecap": "round",
    })
  );
  container.appendChild(svg);
  return svg;
}

function legend(series) {
  const node = document.createElement("div");
  node.className = "chart-legend";
  series.forEach((serie, index) => {
    const item = document.createElement("div");
    item.className = "chart-legend__item";
    item.innerHTML = `<span class="chart-legend__swatch" style="background:${
      serie.color || PALETTE[index % PALETTE.length]
    }"></span><span>${serie.name || `Serie ${index + 1}`}</span>`;
    node.appendChild(item);
  });
  return node;
}

export const palette = PALETTE;
