document.addEventListener("DOMContentLoaded", () => {
  const tg = window.Telegram?.WebApp;
  let currentUserId = "8348411770";
  let selectedApp = "ACC_LV5"; // Mặc định chọn ACC LV5 Free Fire

  if (tg) {
    tg.ready();
    tg.expand();

    const user = tg.initDataUnsafe?.user;
    if (user) {
      currentUserId = user.id;
      document.getElementById("user-name").textContent = user.first_name + (user.last_name ? " " + user.last_name : "");
      document.getElementById("user-id").textContent = user.id;
      if (user.photo_url) {
        document.getElementById("user-avatar").src = user.photo_url;
      }
    }
  }

  // Hàm kích hoạt rung phản hồi khi bấm nút
  const triggerHaptic = () => {
    if (tg?.HapticFeedback) {
      tg.HapticFeedback.impactOccurred("medium");
    }
  };

  // Quản lý Modal Popup
  const modalOverlay = document.getElementById("modal-overlay");
  const modalTitle = document.getElementById("modal-title");
  const modalBody = document.getElementById("modal-body");
  const modalClose = document.getElementById("modal-close");

  const openModal = (title, htmlContent) => {
    triggerHaptic();
    modalTitle.textContent = title;
    modalBody.innerHTML = htmlContent;
    modalOverlay.classList.add("active");
  };

  const closeModal = () => {
    modalOverlay.classList.remove("active");
  };

  modalClose.addEventListener("click", closeModal);
  modalOverlay.addEventListener("click", (e) => {
    if (e.target === modalOverlay) closeModal();
  });

  // HÀM TƯƠNG TÁC CHO TẤT CẢ CÁC NÚT (ALL BUTTONS CLICKABLE)

  // 1. Nút Menu góc trên phải
  document.getElementById("btn-menu").addEventListener("click", () => {
    openModal("Menu Hệ Thống", `
      <div style="display:flex; flex-direction:column; gap:12px;">
        <button class="btn-primary" style="background:#1e2338; color:#fff;" onclick="sendTelegramAction('OPEN_HISTORY')">
          <i class="fa-solid fa-clock-rotate-left"></i> Lịch Sử Mua Hàng
        </button>
        <button class="btn-primary" style="background:#1e2338; color:#fff;" onclick="sendTelegramAction('DEPOSIT_MONEY')">
          <i class="fa-solid fa-wallet"></i> Nạp Tiền Vào Tài Khoản
        </button>
        <button class="btn-primary" style="background:#1e2338; color:#fff;" onclick="sendTelegramAction('SUPPORT')">
          <i class="fa-solid fa-headset"></i> Liên Hệ Hỗ Trợ Admin
        </button>
      </div>
    `);
  });

  // 2. Nút bấm vào User Profile / ID
  document.getElementById("btn-profile").addEventListener("click", () => {
    openModal("Thông Tin Tài Khoản", `
      <p style="font-size:13px; color:#aaa; margin-bottom:10px;">ID Telegram: <strong style="color:#fff;">${currentUserId}</strong></p>
      <p style="font-size:13px; color:#aaa; margin-bottom:10px;">Cấp độ: <span style="color:#00d2ff; font-weight:bold;">VIP CUSTOMER</span></p>
      <p style="font-size:13px; color:#aaa;">Trạng thái: <span style="color:#00ff88;">Đã xác minh ★ VN</span></p>
    `);
  });

  // 3. Nút bấm vào Số Dư (Balance)
  document.getElementById("btn-balance").addEventListener("click", () => {
    openModal("Ví Của Bạn", `
      <div style="text-align:center; padding:10px 0;">
        <h2 style="color:#00ff88; font-size:28px;">0đ</h2>
        <p style="font-size:12px; color:#aaa; margin-top:4px;">Số dư khả dụng</p>
      </div>
      <button class="btn-primary" onclick="sendTelegramAction('DEPOSIT_MONEY')">
        <i class="fa-solid fa-plus-circle"></i> Nạp Thêm Tiền
      </button>
    `);
  });

  // 4. Nút Mua Key Auto
  document.getElementById("btn-buy-key").addEventListener("click", () => {
    openModal("Xác Nhận Mua Key", `
      <p style="font-size:13px; color:#ccc; margin-bottom:12px;">Hệ thống sẽ tự động khởi tạo Key kích hoạt cho gói dịch vụ bạn đã chọn.</p>
      <button class="btn-primary" onclick="sendTelegramAction('BUY_KEY')">
        <i class="fa-solid fa-key"></i> Bắt Đầu Mua Key Ngay
      </button>
    `);
  });

  // 5. Grid các ứng dụng (Android, iOS, Acc Lv5 Free Fire)
  const appItems = document.querySelectorAll(".app-item");
  appItems.forEach((item) => {
    item.addEventListener("click", () => {
      triggerHaptic();
      appItems.forEach((el) => el.classList.remove("active"));
      item.classList.add("active");
      selectedApp = item.getAttribute("data-app");

      if (selectedApp === "ACC_LV5") {
        openModal("ACC LV5 Free Fire", `
          <div style="text-align:center;">
            <img src="https://cdn-icons-png.flaticon.com/512/3408/3408506.png" style="width:60px; height:60px; margin-bottom:10px;">
            <p style="font-size:13px; color:#aaa;">Acc Free Fire LV5 tạo sẵn, sạch 100%, tự động bàn giao tài khoản/mật khẩu qua Bot.</p>
          </div>
          <button class="btn-primary" onclick="sendTelegramAction('BUY_ACC_LV5')">
            <i class="fa-solid fa-cart-shopping"></i> Mua Acc LV5 Ngay (Giá: 10.000đ)
          </button>
        `);
      }
    });
  });

  // 6. Nút Danh Mục Dịch Vụ Khác
  document.getElementById("btn-sub-category").addEventListener("click", () => {
    openModal("Danh Mục Dịch Vụ", `
      <div style="display:flex; flex-direction:column; gap:10px;">
        <div style="padding:10px; background:rgba(255,255,255,0.05); border-radius:12px; cursor:pointer;" onclick="sendTelegramAction('CAT_REG_ACC')">
          <strong style="font-size:13px; color:#00d2ff;">1. Reg Acc Free Fire Tự Động</strong>
          <p style="font-size:11px; color:#8a8d9b;">Tạo acc trắng theo số lượng</p>
        </div>
        <div style="padding:10px; background:rgba(255,255,255,0.05); border-radius:12px; cursor:pointer;" onclick="sendTelegramAction('CAT_BUFF_KEY')">
          <strong style="font-size:13px; color:#00ff88;">2. Gói Key Tool VIP</strong>
          <p style="font-size:11px; color:#8a8d9b;">Key trải nghiệm 1 ngày / 7 ngày / 30 ngày</p>
        </div>
      </div>
    `);
  });

  // 7. Nút Toast Thông Báo Vừa Mua
  document.getElementById("btn-recent-order").addEventListener("click", () => {
    openModal("Thông Báo Mới Nhất", `
      <p style="font-size:13px; color:#ccc;">Khách hàng <strong>Bin_FreeFire</strong> vừa hoàn tất đơn hàng mua <strong style="color:#00ff88;">ACC LV5 VIP</strong> thành công vào 1 phút trước.</p>
    `);
  });

  // Hàm chuyển tiếp hành động về Telegram Bot qua tg.sendData()
  window.sendTelegramAction = (actionType) => {
    triggerHaptic();
    if (!tg) {
      alert(`Đã chọn hành động: ${actionType}`);
      return;
    }

    const payload = {
      action: actionType,
      selectedApp: selectedApp,
      userId: currentUserId,
      timestamp: Date.now()
    };

    // Gửi dữ liệu về Bot Telegram và đóng Mini App
    tg.sendData(JSON.stringify(payload));
  };
});
