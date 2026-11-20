/**
 * cleaning.js - Xử lý Bảng tương tác, Tô màu phân loại, Sửa trực tiếp từng ô và Cổng HITL
 */

let currentTableData = [];
let currentColumns = [];
let currentCellTags = {};

function renderInteractiveTable(columns, rows, cellTags = {}) {
  currentColumns = columns || [];
  currentTableData = rows || [];
  currentCellTags = cellTags || {};

  const headerRow = document.getElementById("tableHeaderRow");
  const tableBody = document.getElementById("tableBody");
  const colSelect = document.getElementById("filterColumnSelect");

  if (!headerRow || !tableBody) return;

  // Render Header
  headerRow.innerHTML = "<th>#</th>" + columns.map(c => `<th>${c}</th>`).join("");

  // Update filter select options (giữ lại cột người dùng đang chọn nếu có)
  if (colSelect) {
    const prevSelected = colSelect.value;
    colSelect.innerHTML = columns.map(c => `<option value="${c}">${c}</option>`).join("");
    if (prevSelected && columns.includes(prevSelected)) {
      colSelect.value = prevSelected;
    } else {
      const regionCol = columns.find(c => c.toLowerCase().includes("mien") || c.toLowerCase().includes("vung"));
      if (regionCol) {
        colSelect.value = regionCol;
      }
    }
  }

  // Render Body
  if (rows.length === 0) {
    tableBody.innerHTML = `<tr><td colspan="${columns.length + 1}" style="text-align: center; color: var(--text-muted); padding: 24px;">Không có dữ liệu hiển thị.</td></tr>`;
    return;
  }

  tableBody.innerHTML = rows.map((row, rIdx) => {
    const cells = columns.map(col => {
      const val = row[col] !== undefined && row[col] !== null ? row[col] : "";
      const tagKey = `${rIdx}_${col}`;
      const tag = currentCellTags[tagKey];

      let tagClass = "";
      let titleTooltip = "";

      if (tag) {
        if (tag.category === "format") {
          tagClass = "cell-tag-format";
          titleTooltip = `Chuẩn hóa định dạng: '${tag.old}' → '${tag.new}'`;
        } else if (tag.category === "anomaly" || tag.category === "numeric") {
          tagClass = "cell-tag-anomaly";
          titleTooltip = `Xử lý lỗi số/ngoại lai: '${tag.old}' → '${tag.new}'`;
        } else if (tag.category === "imputed" || tag.category === "missing") {
          tagClass = "cell-tag-imputed";
          titleTooltip = `Điền giá trị thiếu (${tag.desc || ''})`;
        } else if (tag.category === "manual") {
          tagClass = "cell-tag-manual";
          titleTooltip = `Sửa thủ công theo phản hồi / HITL: '${tag.old}' → '${tag.new}'`;
        }
      }

      // Format số nếu là tiền tệ hoặc hiển thị badge Chưa xác định
      let displayVal = val;
      if (val === "Chưa xác định") {
        displayVal = `<span style="color: #1565C0; font-style: italic; background: #E3F2FD; padding: 2px 8px; border-radius: 4px; font-weight: 500; font-size: 0.8rem;"><i class="fa-solid fa-circle-question" style="font-size: 0.75rem;"></i> Chưa xác định</span>`;
      } else if (typeof val === "number" && Math.abs(val) >= 1000) {
        displayVal = val.toLocaleString("vi-VN");
      }

      return `<td class="editable-cell ${tagClass}" title="${titleTooltip || 'Nhấp đúp để chỉnh sửa ô này'}" ondblclick="startInlineEdit(this, ${rIdx}, '${col}', '${val}')">${displayVal}</td>`;
    }).join("");

    return `<tr><td style="color: var(--text-muted); font-weight: 600;">${rIdx + 1}</td>${cells}</tr>`;
  }).join("");
}

/**
 * Chỉnh sửa trực tiếp từng ô (Inline Cell Editing)
 */
function startInlineEdit(cellElement, rIdx, colName, currentValue) {
  if (cellElement.querySelector("input")) return; // Đang trong chế độ sửa

  const originalContent = cellElement.innerHTML;
  const input = document.createElement("input");
  input.type = "text";
  input.value = currentValue;
  input.className = "anora-input";
  input.style.padding = "4px 8px";
  input.style.fontSize = "0.85rem";
  input.style.width = "100%";
  input.style.minWidth = "100px";

  cellElement.innerHTML = "";
  cellElement.appendChild(input);
  input.focus();

  function saveEdit() {
    const newVal = input.value.trim();
    if (newVal === currentValue) {
      cellElement.innerHTML = originalContent;
      return;
    }

    const formData = new FormData();
    formData.append("row_idx", rIdx);
    formData.append("col_name", colName);
    formData.append("new_value", newVal);

    fetch("/api/step2/edit-cell", {
      method: "POST",
      body: formData
    })
    .then(r => r.json())
    .then(data => {
      if (data.status === "success") {
        currentTableData[rIdx][colName] = newVal;
        currentCellTags = data.cell_tags;
        updateStatsDisplay(data.after_stats);
        updateAuditLog(data.audit_log);
        renderInteractiveTable(currentColumns, currentTableData, currentCellTags);
      } else {
        alert("Lỗi khi lưu ô: " + data.detail);
        cellElement.innerHTML = originalContent;
      }
    })
    .catch(err => {
      console.error(err);
      cellElement.innerHTML = originalContent;
    });
  }

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      saveEdit();
    } else if (e.key === "Escape") {
      cellElement.innerHTML = originalContent;
    }
  });

  input.addEventListener("blur", () => {
    saveEdit();
  });
}

/**
 * Thực hiện làm sạch tự động theo cấu hình (Auto Clean)
 */
function triggerAutoClean() {
  const cleanBtn = document.getElementById("btnAutoClean") || document.querySelector('button[onclick="triggerAutoClean()"]');
  if (cleanBtn) {
    cleanBtn.disabled = true;
    cleanBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Đang tối ưu & làm sạch...</span>';
  }

  const config = {
    remove_duplicates: document.getElementById("cfgRemoveDups") ? document.getElementById("cfgRemoveDups").checked : true,
    fix_negatives: document.getElementById("cfgFixNegatives") ? document.getElementById("cfgFixNegatives").checked : true,
    standardize_dates: document.getElementById("cfgStandardizeDates") ? document.getElementById("cfgStandardizeDates").checked : true,
    standardize_text: document.getElementById("cfgTrimText") ? document.getElementById("cfgTrimText").checked : true,
    handle_missing: document.getElementById("cfgMissingSelect") ? document.getElementById("cfgMissingSelect").value : "unspecified"
  };

  fetch("/api/step2/clean", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config)
  })
  .then(r => r.json())
  .then(data => {
    if (data.status === "success") {
      updateStatsDisplay(data.after_stats, data.before_stats);
      updateAuditLog(data.audit_log);
      renderInteractiveTable(data.columns, data.preview_rows, data.cell_tags);
      confetti({ particleCount: 35, spread: 65, origin: { y: 0.6 } });
      if (cleanBtn) {
        cleanBtn.innerHTML = '<i class="fa-solid fa-check"></i> <span>Đã hoàn tất làm sạch!</span>';
        setTimeout(() => {
          cleanBtn.disabled = false;
          cleanBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> <span>Thực hiện làm sạch</span>';
        }, 1800);
      }
    } else {
      alert("Lỗi làm sạch: " + (data.detail || "Không rõ nguyên nhân"));
      if (cleanBtn) {
        cleanBtn.disabled = false;
        cleanBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> <span>Thực hiện làm sạch</span>';
      }
    }
  })
  .catch(err => {
    alert("Lỗi kết nối: " + err.message);
    if (cleanBtn) {
      cleanBtn.disabled = false;
      cleanBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> <span>Thực hiện làm sạch</span>';
    }
  });
}

/**
 * Lọc xóa hoặc giữ dòng theo điều kiện (Ví dụ: Bỏ Miền Bắc, giữ Miền Trung và Nam)
 */
function applyConditionFilter(action = "remove") {
  const col = document.getElementById("filterColumnSelect").value;
  const op = document.getElementById("filterOperatorSelect").value;
  const val = document.getElementById("filterValueInput").value;

  if (!col || !val) {
    alert("Vui lòng chọn cột và nhập giá trị điều kiện lọc.");
    return;
  }

  const formData = new FormData();
  formData.append("column", col);
  formData.append("operator", op);
  formData.append("value", val);
  formData.append("action", action);

  fetch("/api/step2/filter", {
    method: "POST",
    body: formData
  })
  .then(r => r.json())
  .then(data => {
    if (data.status === "success") {
      updateStatsDisplay(data.after_stats);
      updateAuditLog(data.audit_log);
      renderInteractiveTable(data.columns, data.preview_rows, data.cell_tags);
    } else {
      alert("Lỗi khi lọc: " + (data.detail || data.message));
    }
  })
  .catch(err => alert("Lỗi khi gửi điều kiện lọc: " + err.message));
}

/**
 * Cập nhật số liệu Thống kê Trước - Sau
 */
function updateStatsDisplay(afterStats, beforeStats) {
  if (!afterStats) return;

  const totalRowsEl = document.getElementById("statTotalRows");
  const nullCellsEl = document.getElementById("statNullCells");
  const dupRowsEl = document.getElementById("statDuplicateRows");
  const scoreEl = document.getElementById("statQualityScore");

  if (totalRowsEl) totalRowsEl.innerText = afterStats.total_rows || 0;
  if (nullCellsEl) nullCellsEl.innerText = afterStats.null_cells || 0;
  if (dupRowsEl) dupRowsEl.innerText = afterStats.duplicate_rows || 0;
  if (scoreEl) scoreEl.innerText = `${afterStats.quality_score || 100}%`;

  if (beforeStats) {
    const deltaEl = document.getElementById("statRowsDelta");
    if (deltaEl) deltaEl.innerText = `Trước: ${beforeStats.total_rows} | Sau: ${afterStats.total_rows}`;
    const nullDeltaEl = document.getElementById("statNullDelta");
    if (nullDeltaEl) nullDeltaEl.innerText = `Đã xử lý: ${beforeStats.null_cells - afterStats.null_cells} ô`;
  }
}

/**
 * Cập nhật Audit Log
 */
function updateAuditLog(logArray) {
  const container = document.getElementById("auditLogList");
  const countLabel = document.getElementById("auditCountLabel");
  if (!container || !logArray) return;

  container.innerHTML = logArray.map(item => `<div>${item}</div>`).join("");
  container.scrollTop = container.scrollHeight;
  if (countLabel) countLabel.innerText = `${logArray.length} sự kiện`;
}

/**
 * Modal Chỉ đạo Rà soát lại HITL
 */
function openDirectiveModal() {
  const m = document.getElementById("directiveModal");
  if (m) m.classList.add("open");
}
function closeDirectiveModal() {
  const m = document.getElementById("directiveModal");
  if (m) m.classList.remove("open");
}

function submitReviewDirective() {
  const inputEl = document.getElementById("directiveTextInput");
  const text = inputEl ? inputEl.value.trim() : "";
  if (!text) {
    alert("Vui lòng nhập chỉ đạo rà soát.");
    return;
  }

  const submitBtn = document.querySelector("#directiveModal .btn-primary-sage");
  const originalBtnText = submitBtn ? submitBtn.innerHTML : "";
  if (submitBtn) {
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang thực thi chỉ đạo...';
    submitBtn.disabled = true;
  }

  const formData = new FormData();
  formData.append("directive", text);

  fetch("/api/step2/directive", {
    method: "POST",
    body: formData
  })
  .then(r => r.json())
  .then(data => {
    closeDirectiveModal();
    if (data.status === "success") {
      if (inputEl) inputEl.value = "";
      if (data.columns) currentColumns = data.columns;
      if (data.cell_tags) currentCellTags = data.cell_tags;
      updateStatsDisplay(data.after_stats);
      updateAuditLog(data.audit_log);
      renderInteractiveTable(currentColumns, data.preview_rows, currentCellTags);
      alert("✅ " + (data.message || "Đã áp dụng chỉ đạo rà soát HITL thành công!"));
    } else {
      alert("Lỗi: " + (data.detail || data.message || "Không thể thực hiện chỉ đạo."));
    }
  })
  .catch(err => alert("Lỗi kết nối: " + err.message))
  .finally(() => {
    if (submitBtn) {
      submitBtn.innerHTML = originalBtnText || '<i class="fa-solid fa-paper-plane"></i> Gửi chỉ đạo rà soát';
      submitBtn.disabled = false;
    }
  });
}

/**
 * Phê duyệt dữ liệu hợp lệ tại Cổng kiểm duyệt HITL
 */
function approveAndProceedToAnalytics() {
  fetch("/api/step2/approve", {
    method: "POST"
  })
  .then(r => r.json())
  .then(data => {
    if (data.status === "success") {
      if (typeof needsReportRefresh !== "undefined") needsReportRefresh = true;
      confetti({ particleCount: 70, spread: 80, origin: { y: 0.5 } });
      populateAnalyticsAndDashboard(data.analysis_data);
      switchPage(4); // Chuyển sang Bước 3 & Bước 4
    } else {
      alert("Lỗi phê duyệt: " + (data.detail || "Chưa thể phê duyệt."));
    }
  })
  .catch(err => alert("Lỗi kết nối: " + err.message));
}
