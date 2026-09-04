// Minimal progressive enhancement. The app works fully without JS.

// Confirm dialogs on destructive buttons.
document.addEventListener("click", (event) => {
  const el = event.target.closest("[data-confirm]");
  if (el && !window.confirm(el.dataset.confirm)) {
    event.preventDefault();
  }
});

// Auto-resize textareas marked with data-autoresize.
document.querySelectorAll("textarea[data-autoresize]").forEach((ta) => {
  const fit = () => {
    ta.style.height = "auto";
    ta.style.height = ta.scrollHeight + "px";
  };
  ta.addEventListener("input", fit);
  fit();
});
