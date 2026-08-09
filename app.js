document.addEventListener("DOMContentLoaded", () => {
  const tg = window.Telegram?.WebApp;
  let selectedApp = "GENPLAY";

  if (tg) {
    tg.ready();
    tg.expand();

    const user = tg.initDataUnsafe?.user;
    if (user) {
      document.getElementById("user-name").textContent = user.first_name + (user.last_name ? " " + user.last_name : "");
      document.getElementById("user-id").textContent = user.id;
      if (user.photo_url) {
        document.getElementById("user-avatar").src = user.photo_url;
      }
    }
  }

  // Chọn App
  const appItems = document.querySelectorAll(".app-item");
  appItems.forEach((item) => {
    item.addEventListener("click", () => {
      appItems.forEach((el) => el.classList.remove("active"));
      item.classList.add("active");
      selectedApp = item.getAttribute("data-app");

      if (tg?.HapticFeedback) {
        tg.HapticFeedback.impactOccurred("light");
      }
    });
  });

  // Bấm Mua Key -> Gửi dữ liệu về Telegram Bot thông qua tg.sendData()
  const buyKeyBtn = document.getElementById("btn-buy-key");
  buyKeyBtn.addEventListener("click", () => {
    if (!tg) {
      alert("Hãy mở ứng dụng này bên trong Telegram!");
      return;
    }

    const payload = {
      action: "BUY_KEY",
      appName: selectedApp,
      timestamp: Date.now()
    };

    // Gửi trực tiếp dữ liệu tới Bot và đóng Mini App
    tg.sendData(JSON.stringify(payload));
  });
});
