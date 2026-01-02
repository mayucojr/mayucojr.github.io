document.addEventListener("DOMContentLoaded", () => {
  const toggleBtn = document.querySelector(".menu-toggle");
  const sideMenu = document.getElementById("side-menu");

  if (!toggleBtn || !sideMenu) return;

  // Ensure ARIA is initialized
  toggleBtn.setAttribute("aria-expanded", "false");
  toggleBtn.setAttribute("aria-controls", "side-menu");

  const closeMenu = () => {
    sideMenu.classList.remove("open");
    toggleBtn.classList.remove("open");
    toggleBtn.textContent = "☰";
    toggleBtn.setAttribute("aria-expanded", "false");
  };

  toggleBtn.addEventListener("click", () => {
    const isOpen = sideMenu.classList.toggle("open");
    toggleBtn.classList.toggle("open", isOpen);
    toggleBtn.textContent = isOpen ? "✕" : "☰";
    toggleBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
  });

  // Close menu when a link is clicked
  sideMenu.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", closeMenu);
  });

  // Close menu with Esc key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeMenu();
    }
  });
});
