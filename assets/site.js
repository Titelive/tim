// Barre de progression, retour en haut, thème clair/sombre mémorisé, apparition au défilement.
(function () {
  var root = document.documentElement;
  var bar = document.querySelector(".progress");
  var up = document.querySelector(".to-top");
  var toggle = document.querySelector(".theme-toggle");
  var top = document.querySelector(".top");
  var calm = matchMedia("(prefers-reduced-motion: reduce)").matches;

  function onScroll() {
    var h = root.scrollHeight - root.clientHeight;
    var p = h > 0 ? Math.min(1, root.scrollTop / h) : 0;
    if (bar) bar.style.transform = "scaleX(" + p + ")";
    if (up) up.classList.toggle("show", root.scrollTop > 400);
    if (up) up.style.setProperty("--p", p.toFixed(3));
    if (top) top.classList.toggle("scrolled", root.scrollTop > 10);
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);
  onScroll();
  if (up) up.addEventListener("click", function () {
    // petite animation propre au jeu (tir, propulsion…), puis remontée
    up.classList.remove("fire");
    up.offsetWidth;
    up.classList.add("fire");
    setTimeout(function () { up.classList.remove("fire"); }, 700);
    setTimeout(function () { window.scrollTo({ top: 0, behavior: calm ? "auto" : "smooth" }); }, calm ? 0 : 160);
  });

  function current() {
    return root.dataset.theme || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  }
  if (toggle) {
    toggle.setAttribute("aria-pressed", current() === "light");
    toggle.addEventListener("click", function () {
      var next = current() === "light" ? "dark" : "light";
      var apply = function () { root.dataset.theme = next; };
      // transition douce entre les deux thèmes quand le navigateur sait le faire
      if (document.startViewTransition && !calm) document.startViewTransition(apply); else apply();
      toggle.classList.remove("flip"); void toggle.offsetWidth; toggle.classList.add("flip");
      toggle.setAttribute("aria-pressed", next === "light");
      try { localStorage.setItem("theme", next); } catch (e) {}
    });
  }

  // Agrandissement des images (galeries) : clic, flèches du clavier, balayage au doigt, Échap pour fermer.
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
    var fig = box.querySelector("figure");
    // Changement d'image avec un petit glissement dans le sens du geste
    var go = function (step) {
      show(cur + step);
      fig.style.transition = "none";
      fig.style.transform = "translateX(" + (step > 0 ? 40 : -40) + "%)";
      fig.style.opacity = "0";
      fig.offsetWidth;
      fig.style.transition = "";
      fig.style.transform = "";
      fig.style.opacity = "";
    };
    box.querySelector(".lb-prev").addEventListener("click", function () { go(-1); });
    box.querySelector(".lb-next").addEventListener("click", function () { go(1); });
    // Balayage au doigt : gauche = suivante, droite = précédente, vers le bas = fermer
    var sx = null, sy = 0, dx = 0, dy = 0;
    box.addEventListener("touchstart", function (e) {
      if (e.touches.length !== 1 || e.target.closest("button")) { sx = null; return; }
      sx = e.touches[0].clientX; sy = e.touches[0].clientY; dx = dy = 0;
      fig.style.transition = "none";
    }, { passive: true });
    box.addEventListener("touchmove", function (e) {
      if (sx === null) return;
      dx = e.touches[0].clientX - sx; dy = e.touches[0].clientY - sy;
      if (Math.abs(dx) > Math.abs(dy)) fig.style.transform = "translateX(" + dx + "px) rotate(" + dx / 40 + "deg)";
      else if (dy > 0) fig.style.transform = "translateY(" + dy + "px) scale(" + Math.max(.85, 1 - dy / 1200) + ")";
      e.preventDefault();
    }, { passive: false });
    box.addEventListener("touchend", function () {
      if (sx === null) return;
      sx = null;
      fig.style.transition = "";
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) go(dx < 0 ? 1 : -1);
      else { fig.style.transform = ""; if (dy > 90 && dy > Math.abs(dx)) close(); }
    });
    box.addEventListener("click", function (e) { if (e.target === box) close(); });
    document.addEventListener("keydown", function (e) {
      if (!box.classList.contains("open")) return;
      if (e.key === "Escape") close();
      else if (e.key === "ArrowLeft") show(cur - 1);
      else if (e.key === "ArrowRight") show(cur + 1);
    });
  }

  // Montre de la page Goldeneye : affiche l'heure et la date du jour
  var clock = document.querySelector(".dial .clock"), day = document.querySelector(".dial .date");
  if (clock) {
    var tickClock = function () {
      var d = new Date();
      clock.textContent = String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
      if (day) day.textContent = d.toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "short" }).toUpperCase();
    };
    tickClock();
    setInterval(tickClock, 15000);
  }

  // Cartes des jeux : légère inclinaison 3D et lueur qui suit le pointeur
  if (!calm && matchMedia("(pointer: fine)").matches) {
    document.querySelectorAll(".tilt").forEach(function (el) {
      el.addEventListener("pointermove", function (e) {
        var r = el.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
        el.style.setProperty("--mx", x * 100 + "%");
        el.style.setProperty("--my", y * 100 + "%");
        el.style.setProperty("--rx", (0.5 - y) * 5 + "deg");
        el.style.setProperty("--ry", (x - 0.5) * 7 + "deg");
      });
      el.addEventListener("pointerleave", function () {
        el.style.setProperty("--rx", "0deg");
        el.style.setProperty("--ry", "0deg");
      });
    });
  }

  // Chiffres de l'accueil : comptent jusqu'à leur valeur
  var counters = document.querySelectorAll("[data-count]");
  function fmt(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, "\u202f"); }
  function count(el) {
    var end = +el.dataset.count, t0 = null, dur = 1400;
    function step(t) {
      if (!t0) t0 = t;
      var k = Math.min(1, (t - t0) / dur);
      el.textContent = fmt(Math.round(end * (1 - Math.pow(1 - k, 3))));
      if (k < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  if (!("IntersectionObserver" in window) || calm) return;
  counters.forEach(function (el) { el.textContent = "0"; setTimeout(function () { count(el); }, 900); });
  var items = document.querySelectorAll(".game, ul.links li, .card, .theme h2, .content > :not(.gallery), .gallery figure, .pager a");
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    });
  }, { rootMargin: "0px 0px -40px 0px" });
  items.forEach(function (el, i) {
    var r = el.getBoundingClientRect();
    if (r.top < innerHeight) return; // déjà visible : pas d'animation au chargement
    // décalage en cascade entre éléments voisins (cartes, liens, images)
    var sib = el.parentElement ? Array.prototype.indexOf.call(el.parentElement.children, el) : 0;
    el.style.setProperty("--d", Math.min(sib % 6, 5));
    el.classList.add("reveal");
    io.observe(el);
  });
})();
