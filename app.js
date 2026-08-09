// Hàm giải mã thông tin User chuẩn 100% kể cả khi SDK iOS bị chậm
function getTelegramUser() {
  const tg = window.Telegram?.WebApp;
  if (!tg) return null;

  // 1. Thử lấy từ SDK có sẵn
  if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
    return tg.initDataUnsafe.user;
  }

  // 2. Dự phòng: Tự bóc tách chuỗi mã hóa initData của Telegram (Sửa lỗi cho iOS)
  if (tg.initData) {
    try {
      const params = new URLSearchParams(tg.initData);
      const userJSON = params.get('user');
      if (userJSON) {
        return JSON.parse(decodeURIComponent(userJSON));
      }
    } catch (e) {
      console.error("Lỗi parse initData:", e);
    }
  }

  return null;
}

// Hàm cập nhật giao diện
function renderUserData(user) {
  if (!user || !user.id) return false;

  // 1. Nạp Tên
  const firstName = user.first_name || "";
  const lastName = user.last_name || "";
  const fullName = (firstName + " " + lastName).trim() || user.username || "Khách";
  
  document.getElementById("user-name").textContent = fullName;
  document.getElementById("user-id").textContent = user.id;

  // 2. Nạp Avatar
  if (user.photo_url) {
    document.getElementById("user-avatar").src = user.photo_url;
    document.getElementById("loader-avatar").src = user.photo_url;
  } else {
    const avatarUrl = `https://ui-avatars.com/api/?name=${encodeURIComponent(fullName)}&background=00d2ff&color=fff&bold=true`;
    document.getElementById("user-avatar").src = avatarUrl;
    document.getElementById("loader-avatar").src = avatarUrl;
  }

  return true;
}

window.addEventListener("DOMContentLoaded", () => {
  const tg = window.Telegram?.WebApp;
  const bgMusic = document.getElementById("bg-music");
  const musicToggleBtn = document.getElementById("btn-toggle-music");
  const loadingScreen = document.getElementById("loading-screen");
  
  let isPlayingMusic = false;
  let currentUserId = "N/A";
  let selectedApp = "ACC_LV5";

  if (tg) {
    tg.ready();
    tg.expand();
  }

  // Vòng lặp chờ iOS Telegram inject dữ liệu (Tối đa 1.5 giây)
  let attempts = 0;
  const checkUserInterval = setInterval(() => {
    attempts++;
    const user = getTelegramUser();

    if (user && user.id) {
      currentUserId = user.id;
      renderUserData(user);
      clearInterval(checkUserInterval); // Lấy thành công thì dừng lặp
    } else if (attempts >= 10) {
      clearInterval(checkUserInterval); // Quá 10 lần không thấy (mở ngoài Tele)
      document.getElementById("user-name").textContent = "Mở bằng Bot Tele";
      document.getElementById("user-id").textContent = "N/A";
    }
  }, 150);

  // Màn hình xoay Loading
  setTimeout(() => {
    if (loadingScreen) loadingScreen.classList.add("fade-out");

    if (bgMusic) {
      bgMusic.play().then(() => {
        isPlayingMusic = true;
        if (musicToggleBtn) musicToggleBtn.innerHTML = '<i class="fa-solid fa-compact-disc fa-spin"></i>';
      }).catch(() => {});
    }
  }, 1800);

  // Tự kích hoạt phát nhạc ở lần bấm đầu
  const enableAudioOnFirstTouch = () => {
    if (!isPlayingMusic && bgMusic) {
      bgMusic.play().then(() => {
        isPlayingMusic = true;
        if (musicToggleBtn) musicToggleBtn.innerHTML = '<i class="fa-solid fa-compact-disc fa-spin"></i>';
      }).catch(() => {});
    }
    document.removeEventListener("click", enableAudioOnFirstTouch);
  };
  document.addEventListener("click", enableAudioOnFirstTouch);

  // Toggle Nhạc
  if (musicToggleBtn) {
    musicToggleBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (isPlayingMusic) {
        bgMusic.pause();
        isPlayingMusic = false;
        musicToggleBtn.innerHTML = '<i class="fa-solid fa-volume-xmark"></i>';
      } else {
        bgMusic.play();
        isPlayingMusic = true;
        musicToggleBtn.innerHTML = '<i class="fa-solid fa-compact-disc fa-spin"></i>';
      }
    });
  }

  // Xử lý Modal & Click
  const modalOverlay = document.getElementById("modal-overlay");
  const modalTitle = document.getElementById("modal-title");
  const modalBody = document.getElementById("modal-body");
  const modalClose = document.getElementById("modal-close");

  const openModal = (title, htmlContent) => {
    if (modalTitle) modalTitle.textContent = title;
    if (modalBody) modalBody.innerHTML = htmlContent;
    if (modalOverlay) modalOverlay.classList.add("active");
  };

  if (modalClose) modalClose.addEventListener("click", () => modalOverlay.classList.remove("active"));
  if (modalOverlay) {
    modalOverlay.addEventListener("click", (e) => {
      if (e.target === modalOverlay) modalOverlay.classList.remove("active");
    });
  }

  document.getElementById("btn-menu")?.addEventListener("click", () => {
    openModal("Menu Gun Store", `
      <div style="display:flex; flex-direction:column; gap:12px;">
        <button class="btn-primary" style="background:#1e2338; color:#fff;" onclick="sendTelegramAction('OPEN_HISTORY')">📜 Lịch Sử Mua Hàng</button>
        <button class="btn-primary" style="background:#1e2338; color:#fff;" onclick="sendTelegramAction('DEPOSIT_MONEY')">💳 Nạp Tiền Tài Khoản</button>
        <button class="btn-primary" style="background:#1e2338; color:#fff;" onclick="sendTelegramAction('SUPPORT')">💬 Hỗ Trợ Admin</button>
      </div>
    `);
  });

  document.getElementById("btn-profile")?.addEventListener("click", () => {
    openModal("Tài Khoản Gun Store", `<p style="font-size:13px;">ID Telegram: <strong>${currentUserId}</strong></p>`);
  });

  document.getElementById("btn-buy-key")?.addEventListener("click", () => {
    openModal("Xác Nhận Mua Key", `
      <p style="font-size:13px; color:#ccc;">Hệ thống tự động cấp Key instant 24/7.</p>
      <button class="btn-primary" onclick="sendTelegramAction('BUY_KEY')">Bắt Đầu Mua Key</button>
    `);
  });

  const appItems = document.querySelectorAll(".app-item");
  appItems.forEach((item) => {
    item.addEventListener("click", () => {
      appItems.forEach((el) => el.classList.remove("active"));
      item.classList.add("active");
      selectedApp = item.getAttribute("data-app");

      if (selectedApp === "ACC_LV5") {
        openModal("ACC LV5 Free Fire", `
          <div style="text-align:center;">
            <img src="https://cdn-icons-png.flaticon.com/512/3408/3408506.png" style="width:60px; margin-bottom:10px;">
            <p style="font-size:13px; color:#aaa;">Acc Free Fire LV5 tạo sẵn, sạch 100%.</p>
          </div>
          <button class="btn-primary" onclick="sendTelegramAction('BUY_ACC_LV5')">Mua Acc LV5 Ngay (10.000đ)</button>
        `);
      }
    });
  });

  window.sendTelegramAction = (actionType) => {
    if (!tg || !tg.sendData) {
      alert(`Đã chọn: ${actionType}`);
      return;
    }

    tg.sendData(JSON.stringify({
      action: actionType,
      selectedApp: selectedApp,
      userId: currentUserId,
      timestamp: Date.now()
    }));
  };
});
