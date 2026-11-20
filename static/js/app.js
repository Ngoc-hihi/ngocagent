/**
 * app.js - Trình điều phối ứng dụng Single Page Application AnoraAI
 */

let currentPage = 1;
let selectedSampleType = "retail";
let selectedUploadFile = null;
let needsReportRefresh = true;

/**
 * Xử lý response an toàn cho mọi môi trường (Localhost & Vercel Serverless)
 * Tránh lỗi SyntaxError khi server trả về văn bản hoặc mã lỗi HTTP không phải JSON
 */
async function parseJsonResponse(response) {
  const text = await response.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch (e) {
    if (!response.ok) {
      throw new Error(`Máy chủ phản hồi lỗi (${response.status}): ${text.slice(0, 150)}`);
    }
    throw new Error(`Định dạng dữ liệu không hợp lệ: ${text.slice(0, 100)}`);
  }
  if (!response.ok) {
    const errorMsg = json.detail || json.message || `Lỗi máy chủ (${response.status})`;
    throw new Error(errorMsg);
  }
  return json;
}

// =============================================================================
// ĐIỀU HƯỚNG 5 TRANG (SPA PAGE SWITCHER)
// =============================================================================
function switchPage(pageNum) {
  currentPage = pageNum;

  // Cập nhật giao diện trang
  for (let i = 1; i <= 5; i++) {
    const p = document.getElementById(`pageView${i}`);
    const w = document.getElementById(`wizardStep${i}`);
    if (p) p.classList.toggle("active", i === pageNum);
    if (w) {
      w.classList.toggle("active", i === pageNum);
      if (i < pageNum) w.classList.add("completed");
    }
  }

  // Nếu chuyển sang Bước 5 và dữ liệu mới vừa được nạp/phê duyệt, tự động kết xuất bản mới nhất
  if (pageNum === 5 && needsReportRefresh) {
    triggerExportAllFiles(true);
  }

  // Cuộn lên đầu trang
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// =============================================================================
// THEME SÁNG / TỐI (LIGHT / DARK THEME TOGGLE)
// =============================================================================
function initTheme() {
  const toggleBtn = document.getElementById("themeToggleBtn");
  const savedTheme = localStorage.getItem("anora_theme") || "light";
  applyTheme(savedTheme);

  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") || "light";
      const next = current === "light" ? "dark" : "light";
      applyTheme(next);
      localStorage.setItem("anora_theme", next);
    });
  }
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  const toggleBtn = document.getElementById("themeToggleBtn");
  if (!toggleBtn) return;

  const icon = toggleBtn.querySelector("i");
  const label = toggleBtn.querySelector(".theme-label-text");

  if (theme === "dark") {
    if (icon) icon.className = "fa-solid fa-sun";
    if (label) label.innerText = "Sáng";
  } else {
    if (icon) icon.className = "fa-solid fa-moon";
    if (label) label.innerText = "Tối";
  }
}

// =============================================================================
// LÀM MỚI PHIÊN (RESET SESSION)
// =============================================================================
function initSessionControls() {
  const resetBtn = document.getElementById("resetSessionBtn");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      if (confirm("Bạn có chắc chắn muốn làm mới toàn bộ phiên làm việc? Dữ liệu hiện tại sẽ được khởi tạo lại.")) {
        fetch("/api/session/reset", { method: "POST" })
          .then(parseJsonResponse)
          .then(() => {
            selectedSampleType = "retail";
            selectedUploadFile = null;
            document.getElementById("businessNameInput").value = "Công ty Cổ phần Anora Retail";
            document.getElementById("fileNameDisplay").innerText = "Bấm vào đây để chọn file (.xlsx, .xls, .csv)";
            document.getElementById("gsheetUrlInput").value = "";
            switchPage(1);
            alert("Phiên làm việc đã được làm mới thành công!");
          });
      }
    });
  }
}

// =============================================================================
// TRANG 2 — BƯỚC 1: TIẾP NHẬN DỮ LIỆU & RÀNG BUỘC CHẶN
// =============================================================================
function initStep1Events() {
  // Toggle Mô hình kinh doanh tùy chỉnh
  const modelSelect = document.getElementById("businessModelSelect");
  const customModelInput = document.getElementById("customModelInput");
  if (modelSelect && customModelInput) {
    modelSelect.addEventListener("change", () => {
      customModelInput.style.display = modelSelect.value === "custom" ? "block" : "none";
      if (modelSelect.value === "custom") customModelInput.focus();
      checkStep1Validity();
    });
  }

  // Toggle Bài toán trọng tâm tùy chỉnh
  const problemSelect = document.getElementById("coreProblemSelect");
  const customProblemInput = document.getElementById("customProblemInput");
  if (problemSelect && customProblemInput) {
    problemSelect.addEventListener("change", () => {
      customProblemInput.style.display = problemSelect.value === "custom" ? "block" : "none";
      if (problemSelect.value === "custom") customProblemInput.focus();
    });
  }
}

function selectSampleDataset(type) {
  selectedSampleType = type;
  selectedUploadFile = null;
  document.getElementById("fileNameDisplay").innerText = "Bấm vào đây để chọn file (.xlsx, .xls, .csv)";
  document.getElementById("gsheetUrlInput").value = "";

  document.querySelectorAll(".sample-data-card").forEach(c => {
    const isThis = c.getAttribute("data-sample") === type;
    c.classList.toggle("selected", isThis);
    const icon = c.querySelector("i");
    if (icon) {
      icon.className = isThis ? "fa-solid fa-circle-check" : "fa-regular fa-circle";
      icon.style.color = isThis ? "var(--sage-primary)" : "var(--text-muted)";
    }
  });

  // Tự động gợi ý mô hình phù hợp với bộ dữ liệu
  const modelSelect = document.getElementById("businessModelSelect");
  if (type === "retail") modelSelect.value = "B2C Bán lẻ & Chuỗi F&B";
  else if (type === "saas") modelSelect.value = "B2B SaaS & Phần mềm dịch vụ";
  else if (type === "manufacturing") modelSelect.value = "Sản xuất & Chuỗi cung ứng";

  checkStep1Validity();
}

function handleFileSelected(event) {
  const file = event.target.files[0];
  if (file) {
    selectedUploadFile = file;
    selectedSampleType = null;
    document.querySelectorAll(".sample-data-card").forEach(c => {
      c.classList.remove("selected");
      const icon = c.querySelector("i");
      if (icon) {
        icon.className = "fa-regular fa-circle";
        icon.style.color = "var(--text-muted)";
      }
    });
    document.getElementById("fileNameDisplay").innerText = `✓ Đã chọn: ${file.name} (${(file.size/1024).toFixed(1)} KB)`;
    checkStep1Validity();
  }
}

function checkStep1Validity() {
  const modelSelect = document.getElementById("businessModelSelect");
  const customModel = document.getElementById("customModelInput").value.trim();
  const gsheetUrl = document.getElementById("gsheetUrlInput").value.trim();
  const hasModel = (modelSelect.value !== "custom" && modelSelect.value !== "") || (modelSelect.value === "custom" && customModel !== "");
  const hasData = selectedSampleType !== null || selectedUploadFile !== null || gsheetUrl !== "";

  const alertBox = document.getElementById("guardAlertBox");
  const alertText = document.getElementById("guardAlertText");
  const proceedBtn = document.getElementById("proceedStep2Btn");

  if (!hasModel) {
    if (alertBox) alertBox.className = "guard-alert";
    if (alertText) alertText.innerText = "⚠ Chặn: Vui lòng chọn hoặc nhập Mô hình kinh doanh trước khi đi tiếp.";
    if (proceedBtn) proceedBtn.disabled = true;
    return false;
  }

  if (!hasData) {
    if (alertBox) alertBox.className = "guard-alert";
    if (alertText) alertText.innerText = "⚠ Chặn: Chưa có dữ liệu nào được nạp! Vui lòng chọn mẫu dữ liệu hoặc tải file lên.";
    if (proceedBtn) proceedBtn.disabled = true;
    return false;
  }

  if (alertBox) alertBox.className = "guard-alert success";
  if (alertText) alertText.innerText = "✓ Đã sẵn sàng: Mô hình kinh doanh và nguồn dữ liệu hợp lệ. Bạn có thể sang Bước 2.";
  if (proceedBtn) proceedBtn.disabled = false;
  return true;
}

function submitStep1AndProceed() {
  if (!checkStep1Validity()) {
    alert("Vui lòng đáp ứng đầy đủ điều kiện (Mô hình kinh doanh & Nguồn dữ liệu) để tiếp tục!");
    return;
  }

  const bizName = document.getElementById("businessNameInput").value.trim() || "Doanh nghiệp Mẫu";
  const modelSelect = document.getElementById("businessModelSelect");
  const bizModel = modelSelect.value === "custom" ? document.getElementById("customModelInput").value.trim() : modelSelect.value;
  
  const probSelect = document.getElementById("coreProblemSelect");
  const coreProb = probSelect.value === "custom" ? document.getElementById("customProblemInput").value.trim() : probSelect.value;
  const addInfo = document.getElementById("additionalInfoInput").value.trim();
  const gsheetUrl = document.getElementById("gsheetUrlInput").value.trim();

  const formData = new FormData();
  formData.append("business_name", bizName);
  formData.append("business_model", bizModel);
  formData.append("core_problem", coreProb);
  formData.append("additional_info", addInfo);

  if (selectedSampleType) {
    formData.append("sample_type", selectedSampleType);
  } else if (selectedUploadFile) {
    formData.append("file", selectedUploadFile);
  } else if (gsheetUrl) {
    formData.append("gsheet_url", gsheetUrl);
  }

  const proceedBtn = document.getElementById("proceedStep2Btn");
  if (proceedBtn) proceedBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang nạp dữ liệu...';

  fetch("/api/step1/ingest", {
    method: "POST",
    body: formData
  })
  .then(parseJsonResponse)
  .then(data => {
    if (proceedBtn) proceedBtn.innerHTML = '<span>Tiếp tục sang Bước 2 (Làm sạch HITL)</span> <i class="fa-solid fa-arrow-right"></i>';
    if (data.status === "success") {
      needsReportRefresh = true;
      const dlCards = document.getElementById("downloadCardsContainer");
      if (dlCards) dlCards.style.display = "none";
      const previewContainer = document.getElementById("printPreviewSheet");
      if (previewContainer) previewContainer.innerHTML = "";
      updateStatsDisplay(data.stats, data.stats);
      renderInteractiveTable(data.columns, data.preview_rows, {});
      switchPage(3); // Chuyển sang Bước 2
    } else {
      alert("Lỗi tiếp nhận dữ liệu: " + (data.detail || "Không rõ nguyên nhân"));
    }
  })
  .catch(err => {
    if (proceedBtn) proceedBtn.innerHTML = '<span>Tiếp tục sang Bước 2 (Làm sạch HITL)</span> <i class="fa-solid fa-arrow-right"></i>';
    alert("Lỗi kết nối máy chủ: " + err.message);
  });
}

// =============================================================================
// TRANG 5 — XUẤT 3 TỆP & XEM TRƯỚC KHI IN
// =============================================================================
function triggerExportAllFiles(isAuto = false) {
  const exportBtn = document.getElementById("btnExportAll");
  if (exportBtn) exportBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang kết xuất 3 tệp theo dữ liệu mới...';

  fetch("/api/step5/export-all", {
    method: "POST"
  })
  .then(parseJsonResponse)
  .then(data => {
    if (exportBtn) exportBtn.innerHTML = '<i class="fa-solid fa-file-arrow-down"></i> <span>Tạo & Xuất Trọn Bộ 3 Tệp</span>';
    if (data.status === "success") {
      needsReportRefresh = false;
      if (!isAuto) confetti({ particleCount: 100, spread: 100, origin: { y: 0.4 } });

      // Hiển thị khung tải 3 tệp
      const dlCards = document.getElementById("downloadCardsContainer");
      if (dlCards) dlCards.style.display = "block";

      document.getElementById("linkDownloadExcel").href = data.files.excel + `?t=${Date.now()}`;
      document.getElementById("linkDownloadDocx").href = data.files.docx + `?t=${Date.now()}`;
      document.getElementById("linkDownloadHtml").href = data.files.html + `?t=${Date.now()}`;

      // Nạp nội dung Xem trước khi in (Print Preview) không dùng cache cũ
      loadHtmlPrintPreview();
      if (!isAuto) {
        alert("✓ Đã kết xuất trọn bộ 3 tệp (.xlsx, .docx, .html) và lưu thành công vào Lịch sử chạy!");
      }
    } else if (!isAuto) {
      alert("Lỗi xuất tệp: " + (data.detail || "Không rõ"));
    }
  })
  .catch(err => {
    if (exportBtn) exportBtn.innerHTML = '<i class="fa-solid fa-file-arrow-down"></i> <span>Tạo & Xuất Trọn Bộ 3 Tệp</span>';
    if (!isAuto) alert("Lỗi kết nối: " + err.message);
  });
}

function loadHtmlPrintPreview() {
  const ts = Date.now();
  const container = document.getElementById("printPreviewSheet");
  if (container) {
    container.innerHTML = `<iframe src="/api/preview-html?t=${ts}" style="width: 100%; min-height: 900px; border: none; border-radius: 4px;"></iframe>`;
  }
}

function printReportPreview() {
  window.open(`/api/preview-html?t=${Date.now()}`, "_blank");
}

// =============================================================================
// MODAL LỊCH SỬ CHẠY (RUN HISTORY)
// =============================================================================
function initHistoryModal() {
  const openBtn = document.getElementById("historyModalBtn");
  if (openBtn) {
    openBtn.addEventListener("click", () => {
      const m = document.getElementById("historyModal");
      if (m) {
        m.classList.add("open");
        fetchHistoryList();
      }
    });
  }
}

function closeHistoryModal() {
  const m = document.getElementById("historyModal");
  if (m) m.classList.remove("open");
}

function fetchHistoryList() {
  const container = document.getElementById("historyListContainer");
  if (!container) return;

  fetch("/api/history")
    .then(parseJsonResponse)
    .then(list => {
      if (!list || list.length === 0) {
        container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 20px;">Chưa có phiên chạy nào được lưu trữ.</div>`;
        return;
      }

      container.innerHTML = list.map(item => `
        <div style="background: var(--bg-subtle); border: 1px solid var(--border-delicate); border-radius: var(--radius-sm); padding: 14px 18px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <strong style="color: var(--sage-primary); font-size: 0.95rem;">${item.business_name}</strong>
            <span style="font-size: 0.75rem; color: var(--text-muted);"><i class="fa-regular fa-clock"></i> ${item.timestamp}</span>
          </div>
          <div style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 8px;">
            Mô hình: <em>${item.business_model}</em> | Trọng tâm: <em>${item.core_problem}</em>
          </div>
          <div style="font-size: 0.82rem; margin-bottom: 10px;">
            Doanh thu: <strong>${Math.round(item.summary_metrics.revenue).toLocaleString('vi-VN')} đ</strong> |
            Lợi nhuận ròng: <strong>${Math.round(item.summary_metrics.net_profit).toLocaleString('vi-VN')} đ</strong> |
            Biên lãi: <strong>${item.summary_metrics.profit_margin}%</strong>
          </div>
          <div style="display: flex; gap: 8px;">
            <a href="${item.files.excel}" class="export-btn excel" style="padding: 4px 10px; font-size: 0.78rem;" download><i class="fa-solid fa-file-excel"></i> Excel</a>
            <a href="${item.files.docx}" class="export-btn docx" style="padding: 4px 10px; font-size: 0.78rem;" download><i class="fa-solid fa-file-word"></i> Word DIID</a>
            <a href="${item.files.html}" class="export-btn html" style="padding: 4px 10px; font-size: 0.78rem;" download><i class="fa-solid fa-file-code"></i> Web HTML</a>
          </div>
        </div>
      `).join('');
    })
    .catch(err => {
      container.innerHTML = `<div style="color: #C62828;">Lỗi khi tải lịch sử: ${err.message}</div>`;
    });
}

// =============================================================================
// KHỞI ĐỘNG HỆ THỐNG
// =============================================================================
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initSessionControls();
  initStep1Events();
  initHistoryModal();
});
