document.addEventListener("DOMContentLoaded", () => {
  const tg = window.Telegram?.WebApp;
  const bgMusic = document.getElementById("bg-music");
  const musicToggleBtn = document.getElementById("btn-toggle-music");
  const loadingScreen = document.getElementById("loading-screen");
  const loaderStatus = document.getElementById("loader-status");

  let isPlayingMusic = false;
  let currentUserId = "N/A";
  let selectedApp = "ACC_LV5";

  // 1. LẬP TỨC NHẬN DIỆN USER TỪ MILISEC ĐẦU TIÊN
  if (tg) {
    tg.ready();
    tg.expand();

    const user = tg.initDataUnsafe?.user;

    if (user) {
      currentUserId = user.id;

      // Đưa Tên & ID hiển thị ngay lập tức
      const fullName = (user.first_name || "") + (user.last_name ? " " + user.last_name : "");
      document.getElementById("user-name").textContent = fullName.trim() || "Telegram User";
      document.getElementById("user-id").textContent = user.id;

      // Xử lý Avatar ngay lập tức
      if (user.photo_url) {
        document.getElementById("user-avatar").src = user.photo_url;
        document.getElementById("loader-avatar").src = user.photo_url;
      } else {
        const avatarUrl = `https://ui-avatars.com/api/?name=${encodeURIComponent(fullName || 'G')}&background=00d2ff&color=fff&bold=true`;
        document.getElementById("user-avatar").src = avatarUrl;
        document.getElementById("loader-avatar").src = avatarUrl;
      }
    }
  }

  // 2. XOAY LOADING 1.8 SECONDS RỒI TỰ ĐỘNG CHUYỂN MÀN HÌNH MÀ KHÔNG CẦN CHẠM NÚT
  setTimeout(() => {
    loaderStatus.textContent = "Hoàn tất!";
    
    // Tự động mờ và biến mất màn hình loading
    loadingScreen.classList.add("fade-out");

    // Thử tự động phát nhạc
    bgMusic.play().then(() => {
      isPlayingMusic = true;
      musicToggleBtn.innerHTML = '<i class="fa-solid fa-compact-disc fa-spin"></i>';
    }).catch(() => {
      console.log("Trình duyệt chặn autoplay nhạc, phát nhạc ở lần bấm đầu tiên.");
    });
  }, 1800);

  // Phát nhạc tự động ở tương tác chạm đầu tiên nếu trình duyệt chặn Autoplay
  const enableAudioOnFirstTouch = () => {
    if (!isPlayingMusic) {
      bgMusic.play().then(() => {
        isPlayingMusic = true;
        musicToggleBtn.innerHTML = '<i class="fa-solid fa-compact-disc fa-spin"></i>';
      }).catch(() => {});
    }
    document.removeEventListener("click", enableAudioOnFirstTouch);
  };
  document.addEventListener("click", enableAudioOnFirstTouch);

  // Toggle Bật/Tắt Nhạc
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

  // 3. XỬ LÝ SỰ KIỆN CÁC NÚT BẤM
  const modalOverlay = document.getElementById("modal-overlay");
  const modalTitle = document.getElementById("modal-title");
  const modalBody = document.getElementById("modal-body");
  const modalClose = document.getElementById("modal-close");

  const openModal = (title, htmlContent) => {
    modalTitle.textContent = title;
    modalBody.innerHTML = htmlContent;
    modalOverlay.classList.add("active");
  };

  modalClose.addEventListener("click", () => modalOverlay.classList.remove("active"));
  modalOverlay.addEventListener("click", (e) => {
    if (e.target === modalOverlay) modalOverlay.classList.remove("active");
  });

  document.getElementById("btn-menu").addEventListener("click", () => {
    openModal("Menu Gun Store", `
      <div style="display:flex; flex-direction:column; gap:12px;">
        <button class="btn-primary" style="background:#1e2338; color:#fff;" onclick="sendTelegramAction('OPEN_HISTORY')">📜 Lịch Sử Mua Hàng</button>
        <button class="btn-primary" style="background:#1e2338; color:#fff;" onclick="sendTelegramAction('DEPOSIT_MONEY')">💳 Nạp Tiền Tài Khoản</button>
        <button class="btn-primary" style="background:#1e2338; color:#fff;" onclick="sendTelegramAction('SUPPORT')">💬 Hỗ Trợ Admin</button>
      </div>
    `);
  });

  document.getElementById("btn-profile").addEventListener("click", () => {
    openModal("Tài Khoản Gun Store", `<p style="font-size:13px;">ID Telegram: <strong>${currentUserId}</strong></p>`);
  });

  document.getElementById("btn-buy-key").addEventListener("click", () => {
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
    if (!tg) {
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
