/**
 * assistant.js - Trợ lý ảo AI AnoraAI & Đánh giá 1 - 5 Sao
 */

function toggleChatDrawer() {
  const drawer = document.getElementById("aiChatDrawer");
  if (drawer) {
    drawer.classList.toggle("open");
    if (drawer.classList.contains("open")) {
      document.getElementById("chatInput").focus();
    }
  }
}

function sendQuickPrompt(promptText) {
  const input = document.getElementById("chatInput");
  if (input) {
    input.value = promptText;
    sendChatMessage();
  }
}

function sendChatMessage() {
  const input = document.getElementById("chatInput");
  const msgContainer = document.getElementById("chatMessages");
  const text = input.value.trim();
  if (!text) return;

  // Render tin nhắn của User
  const userDiv = document.createElement("div");
  userDiv.className = "chat-msg user";
  userDiv.innerText = text;
  msgContainer.appendChild(userDiv);
  input.value = "";
  msgContainer.scrollTop = msgContainer.scrollHeight;

  // Tin nhắn tạm thời của Assistant
  const assistantDiv = document.createElement("div");
  assistantDiv.className = "chat-msg assistant";
  assistantDiv.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Anora đang phân tích...';
  msgContainer.appendChild(assistantDiv);
  msgContainer.scrollTop = msgContainer.scrollHeight;

  const formData = new FormData();
  formData.append("message", text);

  fetch("/api/assistant/chat", {
    method: "POST",
    body: formData
  })
  .then(window.parseJsonResponse)
  .then(data => {
    if (data.status === "success") {
      // Chuyển đổi định dạng markdown cơ bản sang HTML sạch đẹp
      let formatted = data.reply
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/^### (.*)$/gm, '<strong>$1</strong>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
      assistantDiv.innerHTML = formatted;
    } else {
      assistantDiv.innerText = "Xin lỗi bạn, Anora gặp gián đoạn tạm thời. Vui lòng thử lại nhé.";
    }
    msgContainer.scrollTop = msgContainer.scrollHeight;
  })
  .catch(err => {
    assistantDiv.innerText = "Lỗi kết nối máy chủ: " + err.message;
    msgContainer.scrollTop = msgContainer.scrollHeight;
  });
}

// Khởi tạo Star Rating
document.addEventListener("DOMContentLoaded", () => {
  const fab = document.getElementById("mascotFab");
  const topChatBtn = document.getElementById("openChatTopBtn");
  if (fab) fab.addEventListener("click", toggleChatDrawer);
  if (topChatBtn) topChatBtn.addEventListener("click", toggleChatDrawer);

  let selectedStars = 5;
  const stars = document.querySelectorAll("#starRatingRow .star");

  stars.forEach(star => {
    star.addEventListener("click", () => {
      selectedStars = parseInt(star.getAttribute("data-star"));
      stars.forEach(s => {
        const val = parseInt(s.getAttribute("data-star"));
        s.classList.toggle("selected", val <= selectedStars);
      });
    });

    star.addEventListener("mouseenter", () => {
      const hoverVal = parseInt(star.getAttribute("data-star"));
      stars.forEach(s => {
        const val = parseInt(s.getAttribute("data-star"));
        s.classList.toggle("hovered", val <= hoverVal);
      });
    });

    star.addEventListener("mouseleave", () => {
      stars.forEach(s => s.classList.remove("hovered"));
    });
  });

  const submitFbBtn = document.getElementById("submitFeedbackBtn");
  if (submitFbBtn) {
    submitFbBtn.addEventListener("click", () => {
      const comment = document.getElementById("feedbackComment").value;
      const notice = document.getElementById("feedbackNotice");

      const formData = new FormData();
      formData.append("stars", selectedStars);
      formData.append("comments", comment);

      fetch("/api/feedback", {
        method: "POST",
        body: formData
      })
      .then(window.parseJsonResponse)
      .then(data => {
        if (notice) {
          notice.style.display = "block";
          notice.style.color = "var(--sage-primary)";
          notice.innerText = `✓ Đã gửi đánh giá ${selectedStars} sao về Agent thành công! Cảm ơn bạn.`;
        }
        confetti({ particleCount: 20, spread: 40 });
        document.getElementById("feedbackComment").value = "";
      })
      .catch(err => {
        if (notice) {
          notice.style.display = "block";
          notice.style.color = "#C62828";
          notice.innerText = "Không thể gửi đánh giá: " + err.message;
        }
      });
    });
  }
});
