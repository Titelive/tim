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

  // Agrandissement des images (galeries) : clic, flèches du clavier, Échap pour fermer.
  var zooms = Array.prototype.slice.call(document.querySelectorAll(".gallery .zoom"));
  if (zooms.length) {
    var svg = function (d) { return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + d + "</svg>"; };
    var box = document.createElement("div");
    box.className = "lightbox";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-label", "Image agrandie");
    box.innerHTML = '<figure><img alt=""><figcaption></figcaption></figure>' +
      '<button class="lb-close" type="button" aria-label="Fermer">' + svg('<path d="M6 6l12 12M18 6L6 18"/>') + "</button>" +
      '<button class="lb-prev" type="button" aria-label="Image précédente">' + svg('<path d="M15 6l-6 6 6 6"/>') + "</button>" +
      '<button class="lb-next" type="button" aria-label="Image suivante">' + svg('<path d="M9 6l6 6-6 6"/>') + "</button>";
    document.body.appendChild(box);
    var bimg = box.querySelector("img"), bcap = box.querySelector("figcaption"), cur = 0, last = null;
    var show = function (i) {
      cur = (i + zooms.length) % zooms.length;
      var a = zooms[cur], im = a.querySelector("img");
      bimg.src = a.getAttribute("href");
      bimg.alt = im ? im.alt : "";
      bcap.textContent = im ? im.alt : "";
    };
    var close = function () { box.classList.remove("open"); if (last) last.focus(); };
    zooms.forEach(function (a, i) {
      a.addEventListener("click", function (e) {
        e.preventDefault();
        last = a;
        show(i);
        box.classList.add("open");
        box.querySelector(".lb-close").focus();
      });
    });
    box.querySelector(".lb-close").addEventListener("click", close);
    box.querySelector(".lb-prev").addEventListener("click", function () { show(cur - 1); });
    box.querySelector(".lb-next").addEventListener("click", function () { show(cur + 1); });
    box.addEventListener("click", function (e) { if (e.target === box) close(); });
    document.addEventListener("keydown", function (e) {
      if (!box.classList.contains("open")) return;
      if (e.key === "Escape") close();
      else if (e.key === "ArrowLeft") show(cur - 1);
      else if (e.key === "ArrowRight") show(cur + 1);
    });
  }

  if (!("IntersectionObserver" in window) || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  var items = document.querySelectorAll(".game, ul.links li, .card, .theme h2, .content > :not(.gallery), .gallery figure, .pager a");
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
