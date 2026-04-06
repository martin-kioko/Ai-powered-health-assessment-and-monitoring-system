/* charts.js — Chart.js rendering for ClinicalAI white/navy theme */

const RC = {
  Low:    '#059669',
  Medium: '#d97706',
  High:   '#dc2626',
  accent: '#2563eb',
};

const GRID  = 'rgba(226,232,240,0.9)';
const FONT  = "'JetBrains Mono', monospace";
const MUTED = '#94a3b8';

function _tooltip() {
  return {
    backgroundColor: '#ffffff',
    borderColor: '#e2e8f0',
    borderWidth: 1,
    titleColor: '#0f172a',
    bodyColor: '#475569',
    cornerRadius: 6,
    padding: 10,
  };
}

/* ── Risk trend line ── */
function riskTrendChart(elementId, dates, risks) {
  const el = document.getElementById(elementId);
  if (!el || !dates || !dates.length) return;
  new Chart(el, {
    type: 'line',
    data: {
      labels: dates,
      datasets: [{
        data: risks,
        borderColor: RC.accent,
        backgroundColor: 'rgba(37,99,235,0.06)',
        fill: true,
        tension: 0.35,
        pointRadius: 5,
        pointBackgroundColor: risks.map(r => r === 3 ? RC.High : r === 2 ? RC.Medium : RC.Low),
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          ..._tooltip(),
          callbacks: { label: ctx => ['', 'Low', 'Medium', 'High'][ctx.parsed.y] || '' },
        },
      },
      scales: {
        x: {
          grid: { color: GRID },
          ticks: { color: MUTED, font: { family: FONT, size: 10 } },
        },
        y: {
          min: 0, max: 4,
          ticks: {
            stepSize: 1,
            color: MUTED,
            font: { family: FONT, size: 10 },
            callback: v => ({ 1: 'Low', 2: 'Med', 3: 'High' }[v] || ''),
          },
          grid: { color: GRID },
        },
      },
    },
  });
}

/* ── Donut / risk distribution ── */
function pieChart(elementId, counts) {
  const el = document.getElementById(elementId);
  if (!el) return;

  const order  = ['Low', 'Medium', 'High'];
  const labels = order.filter(k => (counts[k] || 0) > 0);
  const values = labels.map(l => counts[l] || 0);
  const total  = values.reduce((a, b) => a + b, 0);

  if (!total) {
    const wrap = el.closest('.chart-box') || el.parentElement;
    wrap.innerHTML =
      '<div class="chart-title">Risk distribution</div>' +
      '<div style="height:220px;display:flex;align-items:center;justify-content:center;' +
      'font-size:12px;color:#94a3b8;font-family:JetBrains Mono,monospace">No data yet</div>';
    return;
  }

  new Chart(el, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: labels.map(l => RC[l]),
        borderColor: '#ffffff',
        borderWidth: 3,
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: {
          display: true,
          position: 'bottom',
          labels: {
            color: '#475569',
            font: { family: FONT, size: 11 },
            padding: 18,
            boxWidth: 10,
            boxHeight: 10,
            usePointStyle: true,
            pointStyle: 'circle',
          },
        },
        tooltip: {
          ..._tooltip(),
          callbacks: {
            label: ctx => {
              const pct = ((ctx.raw / total) * 100).toFixed(0);
              return ` ${ctx.label}: ${ctx.raw} assessment${ctx.raw !== 1 ? 's' : ''} (${pct}%)`;
            },
          },
        },
      },
    },
  });
}

/* ── Probability bar ── */
function probBar(elementId, probs) {
  const el = document.getElementById(elementId);
  if (!el || !probs || !probs.length) return;
  const labels = ['High', 'Low', 'Medium'];
  new Chart(el, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data: probs.map(p => +(p * 100).toFixed(1)),
        backgroundColor: labels.map(l => RC[l] + '22'),
        borderColor: labels.map(l => RC[l]),
        borderWidth: 1.5,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { ..._tooltip(), callbacks: { label: ctx => ` ${ctx.raw}%` } },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: MUTED, font: { family: FONT, size: 11 } },
        },
        y: {
          min: 0, max: 100,
          grid: { color: GRID },
          ticks: { color: MUTED, font: { family: FONT, size: 10 }, callback: v => v + '%' },
        },
      },
    },
  });
}

/* ── SHAP bar ── */
function shapBar(elementId, features) {
  const el = document.getElementById(elementId);
  if (!el || !features || !features.length) return;
  const names  = features.map(f => f[0]).reverse();
  const values = features.map(f => +f[1].toFixed(4)).reverse();
  new Chart(el, {
    type: 'bar',
    data: {
      labels: names,
      datasets: [{
        data: values,
        backgroundColor: RC.accent + '20',
        borderColor: RC.accent,
        borderWidth: 1.5,
        borderRadius: 4,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { ..._tooltip() } },
      scales: {
        x: { grid: { color: GRID }, ticks: { color: MUTED, font: { family: FONT, size: 10 } } },
        y: { grid: { display: false }, ticks: { color: MUTED, font: { family: FONT, size: 10 } } },
      },
    },
  });
}

/* ── Radar chart ── */
function radarChart(elementId, vitals) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const norm = {
    'Resp Rate': Math.min(vitals.rr / 30, 1),
    'SpO₂':      vitals.spo2 / 100,
    'Sys BP':    Math.min(vitals.sbp / 200, 1),
    'Heart Rate':Math.min(vitals.hr / 150, 1),
    'Temp':      Math.min(Math.max((vitals.temp - 35) / 7, 0), 1),
  };
  new Chart(el, {
    type: 'radar',
    data: {
      labels: Object.keys(norm),
      datasets: [{
        data: Object.values(norm),
        backgroundColor: 'rgba(37,99,235,0.08)',
        borderColor: RC.accent,
        borderWidth: 1.5,
        pointBackgroundColor: RC.accent,
        pointBorderColor: '#ffffff',
        pointBorderWidth: 1.5,
        pointRadius: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: {
        r: {
          min: 0, max: 1,
          ticks: { display: false },
          grid: { color: GRID },
          pointLabels: { color: MUTED, font: { family: FONT, size: 10 } },
          angleLines: { color: GRID },
        },
      },
    },
  });
}

/* ── Review card toggle ── */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.review-card-header').forEach(h => {
    h.addEventListener('click', () => {
      h.closest('.review-card').classList.toggle('open');
    });
  });
});