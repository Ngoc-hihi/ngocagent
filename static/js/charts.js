/**
 * charts.js - Hiển thị 4 Cấp độ Phân tích & Quản lý Biểu đồ Pastel Chart.js
 */

let chartDonutInstance = null;
let chartComparisonInstance = null;
let chartTrendInstance = null;
let chartRegionInstance = null;

// Bảng màu Pastel chuẩn AnoraAI
const ANORA_PALETTE = {
  sage: '#5C6B52',
  sageLight: '#8B9B84',
  sageSubtle: '#E8EFE5',
  rose: '#D49B9E',
  roseLight: '#E8C5C8',
  sand: '#D9CBB8',
  gold: '#C2A676',
  olive: '#7D8B74'
};

function formatCurrencyVN(val) {
  if (typeof val !== 'number') val = parseFloat(val) || 0;
  return Math.round(val).toLocaleString('vi-VN') + ' đ';
}

function switchAnalysisTab(tabIndex) {
  document.querySelectorAll('.analysis-tab-btn').forEach((btn, idx) => {
    btn.classList.toggle('active', idx + 1 === tabIndex);
  });
  document.querySelectorAll('.analysis-tab-pane').forEach((pane, idx) => {
    pane.classList.toggle('active', idx + 1 === tabIndex);
  });
}

function populateAnalyticsAndDashboard(analysisData) {
  if (!analysisData) return;

  const desc = analysisData.descriptive || {};
  const diag = analysisData.diagnostic || {};
  const pred = analysisData.predictive || {};
  const pres = analysisData.prescriptive || {};
  const meta = analysisData.business_meta || {};
  const charts = analysisData.charts || {};

  // 1. Cập nhật Tiêu đề & Bối cảnh
  const subEl = document.getElementById('dashboardSubtitle');
  if (subEl) {
    subEl.innerText = `Doanh nghiệp: ${meta.name} | Mô hình: ${meta.model} | Bài toán: ${meta.core_problem}`;
  }

  // 2. Cập nhật Hàng 6 KPI Cards Pastel (100% chuẩn xác theo dữ liệu nạp)
  document.getElementById('kpiTotalRevenue').innerText = formatCurrencyVN(desc.total_revenue);
  if (desc.has_cost_data === false) {
    document.getElementById('kpiTotalCost').innerText = 'Chưa ghi nhận';
    document.getElementById('kpiNetProfit').innerText = formatCurrencyVN(desc.net_profit);
    document.getElementById('kpiProfitMargin').innerText = '100% (Thuần)';
  } else {
    document.getElementById('kpiTotalCost').innerText = formatCurrencyVN(desc.total_cost);
    document.getElementById('kpiNetProfit').innerText = formatCurrencyVN(desc.net_profit);
    document.getElementById('kpiProfitMargin').innerText = `${desc.profit_margin}%`;
  }
  document.getElementById('kpiAvgValue').innerText = formatCurrencyVN(desc.avg_value_per_record);
  document.getElementById('kpiRecordCount').innerText = `${desc.total_records || 0} dòng`;

  // 3. Tab 1: Mô tả (Descriptive)
  const descSum = document.getElementById('descriptiveSummaryText');
  if (descSum) descSum.innerHTML = `<strong>Tóm lược hiện trạng:</strong> ${desc.summary_text}`;

  // 4. Tab 2: Chẩn đoán (Diagnostic) - Tách bạch tương quan vs nhân quả
  const corrText = document.getElementById('correlationCaseStudyText');
  if (corrText && diag.correlation_vs_causation) {
    corrText.innerHTML = `
      <div style="margin-bottom: 6px;"><em>${diag.correlation_vs_causation.concept}</em></div>
      <div><strong>Trường hợp cụ thể của doanh nghiệp:</strong> ${diag.correlation_vs_causation.case_study}</div>
    `;
  }
  const bnList = document.getElementById('bottlenecksList');
  if (bnList && diag.bottlenecks) {
    bnList.innerHTML = diag.bottlenecks.map(b => `<li style="margin-bottom: 6px;">${b}</li>`).join('');
  }

  // 5. Tab 3: Dự đoán (Predictive)
  const scContent = document.getElementById('predictiveScenariosContent');
  if (scContent && pred.scenarios) {
    const sc = pred.scenarios;
    scContent.innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-top: 8px;">
        <div style="background: #FFFFFF; padding: 10px; border-radius: 6px; border: 1px solid var(--border-delicate);">
          <div style="font-weight: 700; color: var(--sage-primary); font-size: 0.85rem;">${sc.base_case.label}</div>
          <div style="font-size: 1.1rem; font-weight: 700; margin: 4px 0;">${formatCurrencyVN(sc.base_case.values[2])}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">Mục tiêu Margin: ${sc.base_case.target_margin}%</div>
        </div>
        <div style="background: #FFFFFF; padding: 10px; border-radius: 6px; border: 1px solid #A5D6A7;">
          <div style="font-weight: 700; color: #2E7D32; font-size: 0.85rem;">${sc.optimistic_case.label}</div>
          <div style="font-size: 1.1rem; font-weight: 700; margin: 4px 0;">${formatCurrencyVN(sc.optimistic_case.values[2])}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">Mục tiêu Margin: ${sc.optimistic_case.target_margin}%</div>
        </div>
        <div style="background: #FFFFFF; padding: 10px; border-radius: 6px; border: 1px solid #FFCDD2;">
          <div style="font-weight: 700; color: #C62828; font-size: 0.85rem;">${sc.pessimistic_case.label}</div>
          <div style="font-size: 1.1rem; font-weight: 700; margin: 4px 0;">${formatCurrencyVN(sc.pessimistic_case.values[2])}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">Mục tiêu Margin: ${sc.pessimistic_case.target_margin}%</div>
        </div>
      </div>
    `;
  }
  const risksList = document.getElementById('predictiveRisksList');
  if (risksList && pred.projected_risks) {
    risksList.innerHTML = pred.projected_risks.map(r => `<li style="margin-bottom: 6px;">${r}</li>`).join('');
  }

  // 6. Tab 4: Đề xuất (Prescriptive)
  const presGoals = document.getElementById('prescriptiveGoalsContent');
  if (presGoals && pres.strategic_objectives) {
    presGoals.innerHTML = `
      <div style="margin-bottom: 6px;"><strong>Trọng tâm giải quyết:</strong> ${pres.focus_problem_addressed}</div>
      <ul style="padding-left: 20px;">
        ${pres.strategic_objectives.map(o => `<li style="margin-bottom: 4px;">${o}</li>`).join('')}
      </ul>
    `;
  }
  const p30 = document.getElementById('actionPlan30Days');
  if (p30 && pres.action_plan_30_days) {
    p30.innerHTML = pres.action_plan_30_days.map(a => `
      <div style="margin-bottom: 8px;">
        <strong>• ${a.title}:</strong> ${a.action}
        <div style="font-size: 0.75rem; color: var(--sage-primary);">Chủ trì: ${a.owner} | KPI: ${a.kpi}</div>
      </div>
    `).join('');
  }
  const p90 = document.getElementById('actionPlan90Days');
  if (p90 && pres.action_plan_90_days) {
    p90.innerHTML = pres.action_plan_90_days.map(a => `
      <div style="margin-bottom: 8px;">
        <strong>• ${a.title}:</strong> ${a.action}
        <div style="font-size: 0.75rem; color: var(--rose-primary);">Chủ trì: ${a.owner} | KPI: ${a.kpi}</div>
      </div>
    `).join('');
  }

  // 7. RENDER 4 BIỂU ĐỒ CHART.JS
  renderChartDonut(charts.chart_donut);
  renderChartComparison(charts.chart_bar_comparison);
  renderChartTrend(charts.chart_trend_forecast);
  renderChartRegion(charts.chart_region_performance);
}

function renderChartDonut(donutInfo) {
  if (!donutInfo) return;
  const ctx = document.getElementById('canvasDonut');
  if (!ctx) return;

  document.getElementById('donutChartTitle').innerText = donutInfo.title;
  document.getElementById('donutCommentary').innerText = '💡 Nhận xét: ' + donutInfo.commentary;

  if (chartDonutInstance) chartDonutInstance.destroy();

  const total = (donutInfo.data || []).reduce((a, b) => a + (parseFloat(b) || 0), 0);

  chartDonutInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: donutInfo.labels,
      datasets: [{
        data: donutInfo.data,
        backgroundColor: [
          ANORA_PALETTE.sage,
          ANORA_PALETTE.rose,
          ANORA_PALETTE.olive,
          ANORA_PALETTE.roseLight,
          ANORA_PALETTE.gold,
          '#7D8B74',
          '#B58A8D',
          '#8A9EA7',
          '#D9CBB8'
        ],
        borderWidth: 2,
        borderColor: '#FFFFFF'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            boxWidth: 12,
            font: { size: 11, family: '"Plus Jakarta Sans", sans-serif' },
            padding: 10
          }
        },
        tooltip: {
          callbacks: {
            label: function(item) {
              const val = item.raw || 0;
              const pct = total > 0 ? ((val / total) * 100).toFixed(1) : '0.0';
              const rawLabel = (donutInfo.raw_labels && donutInfo.raw_labels[item.dataIndex])
                ? donutInfo.raw_labels[item.dataIndex]
                : item.label;
              return ` ${rawLabel}: ${formatCurrencyVN(val)} (${pct}%)`;
            }
          }
        }
      },
      cutout: '62%'
    }
  });
}

function renderChartComparison(compInfo) {
  if (!compInfo) return;
  const ctx = document.getElementById('canvasComparison');
  if (!ctx) return;

  document.getElementById('barChartTitle').innerText = compInfo.title;
  document.getElementById('comparisonCommentary').innerText = '💡 Nhận xét: ' + compInfo.commentary;

  if (chartComparisonInstance) chartComparisonInstance.destroy();

  const datasets = [
    {
      label: 'Doanh thu (VNĐ)',
      data: compInfo.series_revenue || [],
      backgroundColor: ANORA_PALETTE.sage,
      borderRadius: 4
    }
  ];

  // Chỉ hiển thị cột Chi phí nếu dữ liệu thực sự có ghi nhận chi phí
  if (compInfo.series_cost && compInfo.series_cost.length > 0 && compInfo.series_cost.some(v => v > 0)) {
    datasets.push({
      label: 'Chi phí (VNĐ)',
      data: compInfo.series_cost,
      backgroundColor: ANORA_PALETTE.rose,
      borderRadius: 4
    });
  }

  chartComparisonInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: compInfo.labels,
      datasets: datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: function(v) {
              if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(1) + ' Tỷ';
              if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(0) + ' Tr';
              return v.toLocaleString('vi-VN');
            },
            font: { size: 10 }
          },
          grid: { color: 'rgba(200, 190, 180, 0.2)' }
        },
        x: {
          grid: { display: false },
          ticks: { font: { size: 10 } }
        }
      },
      plugins: {
        legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: function(item) {
              return ` ${item.dataset.label}: ${formatCurrencyVN(item.raw)}`;
            }
          }
        }
      }
    }
  });
}

function renderChartTrend(trendInfo) {
  if (!trendInfo) return;
  const ctx = document.getElementById('canvasTrend');
  if (!ctx) return;

  document.getElementById('trendChartTitle').innerText = trendInfo.title;
  document.getElementById('trendCommentary').innerText = '💡 Nhận xét: ' + trendInfo.commentary;

  if (chartTrendInstance) chartTrendInstance.destroy();

  const splitIdx = trendInfo.split_index || 6;
  const fullData = trendInfo.data || [];
  const actualData = fullData.map((v, i) => (i < splitIdx ? v : null));
  const forecastData = fullData.map((v, i) => (i >= splitIdx - 1 ? v : null));

  chartTrendInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: trendInfo.labels,
      datasets: [
        {
          label: 'Thực tế (Doanh thu các kỳ đã qua)',
          data: actualData,
          borderColor: ANORA_PALETTE.sage,
          backgroundColor: 'rgba(92, 107, 82, 0.1)',
          tension: 0.35,
          pointRadius: 4,
          pointHoverRadius: 6,
          fill: true
        },
        {
          label: 'Dự báo AI (Kịch bản Cơ sở +5%/kỳ)',
          data: forecastData,
          borderColor: ANORA_PALETTE.rose,
          backgroundColor: 'transparent',
          borderDash: [5, 5],
          tension: 0.35,
          pointRadius: 4,
          pointHoverRadius: 6,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          ticks: {
            callback: function(v) {
              if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(1) + ' Tỷ';
              if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(0) + ' Tr';
              return v.toLocaleString('vi-VN');
            },
            font: { size: 10 }
          },
          grid: { color: 'rgba(200, 190, 180, 0.2)' }
        },
        x: {
          grid: { display: false },
          ticks: { font: { size: 9 }, maxRotation: 25 }
        }
      },
      plugins: {
        legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: function(item) {
              return ` ${item.dataset.label}: ${formatCurrencyVN(item.raw)}`;
            }
          }
        }
      }
    }
  });
}

function renderChartRegion(regionInfo) {
  if (!regionInfo) return;
  const ctx = document.getElementById('canvasRegion');
  if (!ctx) return;

  document.getElementById('regionChartTitle').innerText = regionInfo.title;
  document.getElementById('regionCommentary').innerText = '💡 Nhận xét: ' + regionInfo.commentary;

  if (chartRegionInstance) chartRegionInstance.destroy();

  chartRegionInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: regionInfo.labels,
      datasets: [{
        label: 'Doanh thu (VNĐ)',
        data: regionInfo.data,
        backgroundColor: [
          ANORA_PALETTE.sage,
          ANORA_PALETTE.olive,
          ANORA_PALETTE.sand,
          ANORA_PALETTE.rose
        ],
        borderRadius: 4
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          ticks: {
            callback: function(v) { return (v / 1e6).toFixed(0) + ' Tr'; },
            font: { size: 10 }
          },
          grid: { color: 'rgba(200, 190, 180, 0.2)' }
        },
        y: {
          grid: { display: false },
          ticks: { font: { size: 11 } }
        }
      },
      plugins: {
        legend: { display: false }
      }
    }
  });
}
