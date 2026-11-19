// Barre de progression, retour en haut, thème clair/sombre mémorisé, apparition au défilement.
(function () {
  var root = document.documentElement;
  var bar = document.querySelector(".progress");
  var up = document.querySelector(".to-top");
  var toggle = document.querySelector(".theme-toggle");

  function onScroll() {
    var h = root.scrollHeight - root.clientHeight;
    var p = h > 0 ? Math.min(1, root.scrollTop / h) : 0;
    if (bar) bar.style.transform = "scaleX(" + p + ")";
    if (up) up.classList.toggle("show", root.scrollTop > 400);
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);
  onScroll();
  if (up) up.addEventListener("click", function () { window.scrollTo({ top: 0, behavior: "smooth" }); });

  function current() {
    return root.dataset.theme || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  }
  if (toggle) {
    toggle.setAttribute("aria-pressed", current() === "light");
    toggle.addEventListener("click", function () {
      var next = current() === "light" ? "dark" : "light";
      root.dataset.theme = next;
      toggle.setAttribute("aria-pressed", next === "light");
      try { localStorage.setItem("theme", next); } catch (e) {}
    });
  }

  if (!("IntersectionObserver" in window) || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  var items = document.querySelectorAll(".game, ul.links li, .card, .theme h2, .content > *, .pager a");
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    });
  }, { rootMargin: "0px 0px -40px 0px" });
  items.forEach(function (el, i) {
    var r = el.getBoundingClientRect();
    if (r.top < innerHeight) return; // déjà visible : pas d'animation au chargement
    el.classList.add("reveal");
    io.observe(el);
  });
})();
