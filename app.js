document.addEventListener("DOMContentLoaded", () => {
  const tg = window.Telegram?.WebApp;
  const bgMusic = document.getElementById("bg-music");
  const musicToggleBtn = document.getElementById("btn-toggle-music");
  const loadingScreen = document.getElementById("loading-screen");
  const loaderStatus = document.getElementById("loader-status");

  let isPlayingMusic = false;
  let currentUserId = "N/A";
  let selectedApp = "ACC_LV5";

  // FUNCTION LẤY THÔNG TIN TELEGRAM
  const initTelegramUser = () => {
    if (!tg) {
      console.warn("Chưa tải được Telegram WebApp SDK");
      return;
    }

    // Báo cho Telegram biết Mini App đã sẵn sàng
    tg.ready();
    tg.expand();

    // Lấy thông tin User từ Telegram SDK
    const user = tg.initDataUnsafe?.user;

    if (user && user.id) {
      currentUserId = user.id;

      // 1. Lấy Tên
      const firstName = user.first_name || "";
      const lastName = user.last_name || "";
      const fullName = (firstName + " " + lastName).trim() || user.username || "Telegram User";

      document.getElementById("user-name").textContent = fullName;
      document.getElementById("user-id").textContent = user.id;

      // 2. Lấy Avatar
      if (user.photo_url) {
        document.getElementById("user-avatar").src = user.photo_url;
        document.getElementById("loader-avatar").src = user.photo_url;
      } else {
        // Nếu Telegram không trả photo_url (do bảo mật), dùng Avatar tạo theo tên
        const fallbackAvatar = `https://ui-avatars.com/api/?name=${encodeURIComponent(fullName)}&background=00d2ff&color=fff&bold=true`;
        document.getElementById("user-avatar").src = fallbackAvatar;
        document.getElementById("loader-avatar").src = fallbackAvatar;
      }

      if (loaderStatus) loaderStatus.textContent = `Xin chào ${firstName}!`;
    } else {
      // Trường hợp mở ngoài Telegram
      document.getElementById("user-name").textContent = "Mở qua Bot Tele";
      document.getElementById("user-id").textContent = "N/A";
      if (loaderStatus) loaderStatus.textContent = "Chưa kết nối Bot Telegram";
    }
  };

  // Gọi hàm khởi tạo ngay lập tức
  initTelegramUser();

  // MÀN HÌNH LOADING CHUYỂN CẢNH AUTOMATIC
  setTimeout(() => {
    if (loadingScreen) {
      loadingScreen.classList.add("fade-out");
    }

    // Tự động phát nhạc
    if (bgMusic) {
      bgMusic.play().then(() => {
        isPlayingMusic = true;
        if (musicToggleBtn) musicToggleBtn.innerHTML = '<i class="fa-solid fa-compact-disc fa-spin"></i>';
      }).catch(() => {
        // Nếu trình duyệt chặn Autoplay, chờ tương tác bấm bất kỳ
      });
    }
  }, 1800);

  // Phát nhạc ở tương tác bấm đầu tiên nếu trình duyệt chặn tự phát
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

  // XỬ LÝ MODAL & CÁC NÚT BẤM
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

  const btnMenu = document.getElementById("btn-menu");
  if (btnMenu) {
    btnMenu.addEventListener("click", () => {
      openModal("Menu Gun Store", `
        <div style="display:flex; flex-direction:column; gap:12px;">
          <button class="btn-primary" style="background:#1e2338; color:#fff;" onclick="sendTelegramAction('OPEN_HISTORY')">📜 Lịch Sử Mua Hàng</button>
          <button class="btn-primary" style="background:#1e2338; color:#fff;" onclick="sendTelegramAction('DEPOSIT_MONEY')">💳 Nạp Tiền Tài Khoản</button>
          <button class="btn-primary" style="background:#1e2338; color:#fff;" onclick="sendTelegramAction('SUPPORT')">💬 Hỗ Trợ Admin</button>
        </div>
      `);
    });
  }

  const btnProfile = document.getElementById("btn-profile");
  if (btnProfile) {
    btnProfile.addEventListener("click", () => {
      openModal("Tài Khoản Gun Store", `<p style="font-size:13px;">ID Telegram: <strong>${currentUserId}</strong></p>`);
    });
  }

  const btnBuyKey = document.getElementById("btn-buy-key");
  if (btnBuyKey) {
    btnBuyKey.addEventListener("click", () => {
      openModal("Xác Nhận Mua Key", `
        <p style="font-size:13px; color:#ccc;">Hệ thống tự động cấp Key instant 24/7.</p>
        <button class="btn-primary" onclick="sendTelegramAction('BUY_KEY')">Bắt Đầu Mua Key</button>
      `);
    });
  }

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
      alert(`Đã chọn: ${actionType} (Vui lòng mở trong Bot Telegram)`);
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
