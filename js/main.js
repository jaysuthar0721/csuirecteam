document.addEventListener("DOMContentLoaded", () => {
  document.documentElement.classList.add("has-js");
  const toggle = document.querySelector(".nav-toggle");
  const links = document.querySelector(".nav-links");
  const header = document.querySelector(".site-header");

  if (toggle && links && header) {
    const setOpen = (open, restoreFocus = false) => {
      links.classList.toggle("open", open);
      toggle.setAttribute("aria-expanded", String(open));
      toggle.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
      if (restoreFocus) toggle.focus();
    };
    toggle.addEventListener("click", () => setOpen(toggle.getAttribute("aria-expanded") !== "true"));
    links.addEventListener("click", (event) => {
      if (event.target.closest("a")) setOpen(false);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && links.classList.contains("open")) setOpen(false, true);
    });
    document.addEventListener("click", (event) => {
      if (!header.contains(event.target)) setOpen(false);
    });
    header.addEventListener("focusout", (event) => {
      if (event.relatedTarget && !header.contains(event.relatedTarget)) setOpen(false);
    });
    window.matchMedia("(max-width: 1060px)").addEventListener("change", () => setOpen(false));
  }

  const path = window.location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".nav-links a[data-page]").forEach((link) => {
    const active = link.dataset.page === path;
    link.classList.toggle("active", active);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });

  const year = document.getElementById("year");
  if (year) year.textContent = new Date().getFullYear();
});
