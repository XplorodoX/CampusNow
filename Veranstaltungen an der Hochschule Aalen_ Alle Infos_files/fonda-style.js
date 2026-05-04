document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-cookiebot-renew]").forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      if (window.Cookiebot && typeof Cookiebot.renew === "function") {
        Cookiebot.renew();
      }
    });
  });
});

         
