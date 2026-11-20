// Barre de progression, retour en haut, thème clair/sombre mémorisé, apparition au défilement,
// navigation sans rechargement (la musique continue d'une page à l'autre).
(function () {
  var root = document.documentElement;
  var calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  var fine = matchMedia("(pointer: fine)").matches;
  function $(s) { return document.querySelector(s); }
  function $$(s) { return Array.prototype.slice.call(document.querySelectorAll(s)); }

  // ------------------------------------------------------------ défilement
  function onScroll() {
    var bar = $(".progress"), up = $(".to-top"), top = $(".top");
    var h = root.scrollHeight - root.clientHeight;
    var p = h > 0 ? Math.min(1, root.scrollTop / h) : 0;
    if (bar) bar.style.transform = "scaleX(" + p + ")";
    if (up) { up.classList.toggle("show", root.scrollTop > 400); up.style.setProperty("--p", p.toFixed(3)); }
    if (top) top.classList.toggle("scrolled", root.scrollTop > 10);
  }
  addEventListener("scroll", onScroll, { passive: true });
  addEventListener("resize", onScroll);

  // ------------------------------------------------------------ thème
  function current() {
    return root.dataset.theme || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  }

  // ------------------------------------------------------------ clics délégués (valables sur toutes les pages)
  var box = null, fig, bimg, bcap, cur = 0, last = null, zooms = [];
  document.addEventListener("click", function (e) {
    var up = e.target.closest(".to-top");
    if (up) {
      // petite animation propre au jeu (tir, propulsion…), puis remontée
      up.classList.remove("fire"); void up.offsetWidth; up.classList.add("fire");
      setTimeout(function () { up.classList.remove("fire"); }, 700);
      setTimeout(function () { scrollTo({ top: 0, behavior: calm ? "auto" : "smooth" }); }, calm ? 0 : 160);
      return;
    }
    var toggle = e.target.closest(".theme-toggle");
    if (toggle) {
      var next = current() === "light" ? "dark" : "light";
      var apply = function () { root.dataset.theme = next; };
      if (document.startViewTransition && !calm) document.startViewTransition(apply); else apply();
      toggle.classList.remove("flip"); void toggle.offsetWidth; toggle.classList.add("flip");
      toggle.setAttribute("aria-pressed", next === "light");
      try { localStorage.setItem("theme", next); } catch (_) {}
      return;
    }
    var z = e.target.closest(".gallery .zoom");
    if (z && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
      zooms = $$(".gallery .zoom");
      openBox(zooms.indexOf(z), z);
      return;
    }
    var v = e.target.closest(".yt-go");
    if (v && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
      // vidéo : le lecteur YouTube remplace la vignette, la musique du site se met en pause
      e.preventDefault();
      var f = document.createElement("iframe");
      f.src = "https://www.youtube-nocookie.com/embed/" + v.dataset.yt + "?autoplay=1&rel=0&playsinline=1";
      f.title = v.getAttribute("aria-label") || "Vidéo";
      f.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
      f.allowFullscreen = true;
      v.parentNode.classList.add("playing");
      v.replaceWith(f);
      if (audio) audio.pauseForVideo();
    }
  });

  // ------------------------------------------------------------ agrandissement des images
  var svg = function (d) { return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + d + "</svg>"; };
  function show(i) {
    cur = (i + zooms.length) % zooms.length;
    var a = zooms[cur], im = a.querySelector("img");
    bimg.src = a.getAttribute("href");
    bimg.alt = im ? im.alt : "";
    bcap.textContent = im ? im.alt : "";
  }
  function closeBox() { if (!box) return; box.classList.remove("open"); if (last && last.isConnected) last.focus(); }
  function go(step) {
    show(cur + step);
    fig.style.transition = "none";
    fig.style.transform = "translateX(" + (step > 0 ? 40 : -40) + "%)";
    fig.style.opacity = "0";
    fig.offsetWidth;
    fig.style.transition = ""; fig.style.transform = ""; fig.style.opacity = "";
  }
  function buildBox() {
    box = document.createElement("div");
    box.className = "lightbox";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-label", "Image agrandie");
    box.innerHTML = '<figure><img alt=""><figcaption></figcaption></figure>' +
      '<button class="lb-close" type="button" aria-label="Fermer">' + svg('<path d="M6 6l12 12M18 6L6 18"/>') + "</button>" +
      '<button class="lb-prev" type="button" aria-label="Image précédente">' + svg('<path d="M15 6l-6 6 6 6"/>') + "</button>" +
      '<button class="lb-next" type="button" aria-label="Image suivante">' + svg('<path d="M9 6l6 6-6 6"/>') + "</button>";
    document.body.appendChild(box);
    bimg = box.querySelector("img"); bcap = box.querySelector("figcaption"); fig = box.querySelector("figure");
    box.querySelector(".lb-close").addEventListener("click", closeBox);
    box.querySelector(".lb-prev").addEventListener("click", function () { go(-1); });
    box.querySelector(".lb-next").addEventListener("click", function () { go(1); });
    // balayage au doigt : gauche = suivante, droite = précédente, vers le bas = fermer
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
      sx = null; fig.style.transition = "";
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) go(dx < 0 ? 1 : -1);
      else { fig.style.transform = ""; if (dy > 90 && dy > Math.abs(dx)) closeBox(); }
    });
    box.addEventListener("click", function (e) { if (e.target === box) closeBox(); });
  }
  function openBox(i, a) {
    if (!box) buildBox();
    last = a; show(i);
    box.classList.add("open");
    box.querySelector(".lb-close").focus();
  }
  document.addEventListener("keydown", function (e) {
    if (!box || !box.classList.contains("open")) return;
    if (e.key === "Escape") closeBox();
    else if (e.key === "ArrowLeft") show(cur - 1);
    else if (e.key === "ArrowRight") show(cur + 1);
  });

  // ------------------------------------------------------------ montre de la page Goldeneye
  function tickClock() {
    var clock = $(".dial .clock"), day = $(".dial .date");
    if (!clock) return;
    var d = new Date();
    var colon = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
    colon.setAttribute("class", "colon"); colon.textContent = ":";
    clock.textContent = String(d.getHours()).padStart(2, "0");
    clock.appendChild(colon);
    clock.appendChild(document.createTextNode(String(d.getMinutes()).padStart(2, "0")));
    if (day) day.textContent = d.toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "short" }).toUpperCase();
  }
  setInterval(tickClock, 10000);

  // ------------------------------------------------------------ bandeaux d'images (boucle JS qui ne se fige jamais)
  var marquees = [], lastT = 0, looping = false;
  function setupMarquees() {
    marquees = calm ? [] : $$(".marquee .track").map(function (t) {
      t.style.animation = "none";
      var m = t.parentNode;
      var o = { t: t, x: 0, half: 0, speed: m.classList.contains("rev") ? 0.6 : 0.75, dir: m.classList.contains("rev") ? 1 : -1, paused: false };
      m.addEventListener("pointerenter", function () { o.paused = true; });
      m.addEventListener("pointerleave", function () { o.paused = false; });
      return o;
    });
    measure();
    if (marquees.length && !looping) { looping = true; requestAnimationFrame(loop); }
  }
  function measure() {
    marquees.forEach(function (o) {
      var gap = parseFloat(getComputedStyle(o.t).columnGap) || 0;
      o.half = (o.t.scrollWidth + gap) / 2;
      if (o.dir > 0 && o.x === 0) o.x = -o.half;
    });
  }
  function loop(now) {
    var dt = lastT ? Math.min(now - lastT, 50) : 16; lastT = now;
    marquees.forEach(function (o) {
      if (!o.half) return;
      if (!o.paused) o.x += o.dir * o.speed * dt / 16;
      if (o.x <= -o.half) o.x += o.half;
      if (o.x > 0) o.x -= o.half;
      o.t.style.transform = "translate3d(" + o.x.toFixed(2) + "px,0,0)";
    });
    if (marquees.length) requestAnimationFrame(loop); else looping = false;
  }
  addEventListener("resize", measure);
  addEventListener("load", measure);
  document.addEventListener("visibilitychange", function () { lastT = 0; });
  // retour arrière (cache du navigateur) : relance toutes les animations CSS
  addEventListener("pageshow", function (e) {
    if (!e.persisted || !document.getAnimations) return;
    document.getAnimations().forEach(function (a) { try { a.play(); } catch (_) {} });
  });

  // ------------------------------------------------------------ cartes des jeux : inclinaison 3D
  function setupTilt() {
    if (calm || !fine) return;
    $$(".tilt").forEach(function (el) {
      el.addEventListener("pointermove", function (e) {
        var r = el.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
        el.style.setProperty("--mx", x * 100 + "%");
        el.style.setProperty("--my", y * 100 + "%");
        el.style.setProperty("--rx", (0.5 - y) * 5 + "deg");
        el.style.setProperty("--ry", (x - 0.5) * 7 + "deg");
      });
      el.addEventListener("pointerleave", function () { el.style.setProperty("--rx", "0deg"); el.style.setProperty("--ry", "0deg"); });
    });
  }

  // ------------------------------------------------------------ lecteur audio
  // La musique d'une vidéo YouTube, sans afficher la vidéo. Le lecteur reste en place quand on
  // change de page : la musique continue, et ne change que si l'on passe d'un jeu à l'autre.
  var AUDIO = {
    ge: { id: "ljsgAMrFUoM", game: "GoldenEye 007", title: "Thème de GoldenEye 007", artist: "Grant Kirkhope & Graeme Norgate" },
    pd: { id: "DneuOuF8shQ", game: "Perfect Dark", title: "Alien Conflict", artist: "Perfect Dark · remake non compressé" }
  };
  function pageGame() {
    var b = document.body.classList;
    return b.contains("theme-pd") ? "pd" : b.contains("theme-ge") ? "ge" : null;
  }
  function cleanTitle(t, g) {
    t = String(t || "")
      .replace(/^\s*(goldeneye(\s*007)?|perfect\s*dark)\s*(\(n64\))?\s*(ost|soundtrack|music)?\s*[:\-–—|]\s*/i, "")
      .replace(/\s*[\[(](?:n64|hq|hd|ost|official[^)\]]*|nintendo 64)[\])]\s*/gi, " ")
      .replace(/\s{2,}/g, " ").trim();
    return t || AUDIO[g].title;
  }
  var audio = (function () {
    var store = {
      get: function (k, d) { try { var v = localStorage.getItem("audio-" + k); return v === null ? d : v; } catch (_) { return d; } },
      set: function (k, v) { try { localStorage.setItem("audio-" + k, v); } catch (_) {} }
    };
    var game = pageGame() || (store.get("last", "") in AUDIO ? store.get("last") : (Math.random() < .5 ? "ge" : "pd"));
    var ui = document.createElement("div");
    ui.className = "game-audio " + game;
    ui.innerHTML = '<button class="pa-play" type="button">' +
      '<svg class="i-play" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l10.5-6.5z"/></svg>' +
      '<svg class="i-pause" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z"/></svg></button>' +
      '<span class="pa-txt"><span class="pa-song"><b class="pa-title"></b></span><span class="pa-sub"></span></span>' +
      '<span class="pa-eq" aria-hidden="true"><i></i><i></i><i></i><i></i></span>' +
      '<input class="pa-vol" type="range" min="0" max="100" step="1" aria-label="Volume">' +
      '<div class="pa-yt" aria-hidden="true"><div id="pa-yt"></div></div>';
    document.body.appendChild(ui);
    var btn = ui.querySelector(".pa-play"), title = ui.querySelector(".pa-title"), sub = ui.querySelector(".pa-sub"), vol = ui.querySelector(".pa-vol");
    var song = ui.querySelector(".pa-song");
    vol.value = store.get("vol", "60");
    var player = null, ready = false, want = false, loading = false, meta = {};

    function info() { return meta[game] || AUDIO[game]; }
    function render() {
      var m = info(), on = ui.classList.contains("on");
      title.textContent = m.title;
      sub.textContent = m.artist;
      ui.title = m.title + " — " + m.artist;
      btn.setAttribute("aria-label", (on ? "Mettre en pause : " : "Écouter : ") + m.title + " (" + m.artist + ")");
      requestAnimationFrame(scrollTitle);
    }
    // titre trop long pour la place : il défile doucement
    function scrollTitle() {
      title.classList.remove("run");
      var over = title.scrollWidth - song.clientWidth;
      if (over > 4 && !calm) {
        title.style.setProperty("--over", -over - 12 + "px");
        title.style.setProperty("--dur", Math.max(6, over / 18) + "s");
        title.classList.add("run");
      }
    }
    // vrais titre et artiste de la vidéo (mis en cache) ; sinon les valeurs ci-dessus
    function fetchMeta(g) {
      var id = AUDIO[g].id, key = "meta-" + id, c = store.get(key, "");
      if (c) { try { meta[g] = JSON.parse(c); render(); return; } catch (_) {} }
      if (!window.fetch) return;
      fetch("https://noembed.com/embed?url=" + encodeURIComponent("https://www.youtube.com/watch?v=" + id))
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d || !d.title) return;
          meta[g] = { title: cleanTitle(d.title, g), artist: d.author_name || AUDIO[g].artist };
          store.set(key, JSON.stringify(meta[g]));
          if (g === game) render();
        }).catch(function () {});
    }
    function setState(on) { ui.classList.toggle("on", on); render(); }
    function load() {
      if (loading) return; loading = true;
      sub.textContent = "Chargement…";
      window.onYouTubeIframeAPIReady = function () {
        var id = AUDIO[game].id;
        player = new YT.Player("pa-yt", {
          host: "https://www.youtube-nocookie.com", videoId: id, width: 200, height: 200,
          playerVars: { autoplay: 1, controls: 0, playsinline: 1, rel: 0, start: Math.floor(+store.get("t-" + id, "0")) },
          events: {
            onReady: function () { ready = true; player.setVolume(+vol.value); if (want) player.playVideo(); },
            onStateChange: function (e) {
              if (e.data === 0) { player.seekTo(0); player.playVideo(); return; } // en boucle
              if (e.data === 1) {
                var d = player.getVideoData && player.getVideoData();
                if (d && d.title && !store.get("meta-" + AUDIO[game].id, "")) {
                  meta[game] = { title: cleanTitle(d.title, game), artist: d.author || AUDIO[game].artist };
                  store.set("meta-" + AUDIO[game].id, JSON.stringify(meta[game]));
                }
              }
              setState(e.data === 1 || e.data === 3);
            }
          }
        });
      };
      var tag = document.createElement("script"); tag.src = "https://www.youtube.com/iframe_api"; document.head.appendChild(tag);
    }
    function saveTime() { if (ready && player.getCurrentTime) store.set("t-" + AUDIO[game].id, String(player.getCurrentTime() || 0)); }
    function play() { want = true; store.set("on", "1"); ui.classList.remove("resume"); if (ready) player.playVideo(); else load(); setState(true); }
    function pause() { want = false; store.set("on", "0"); if (ready) player.pauseVideo(); setState(false); }
    btn.addEventListener("click", function () { ui.classList.contains("on") ? pause() : play(); });
    vol.addEventListener("input", function () { store.set("vol", vol.value); if (ready) player.setVolume(+vol.value); });
    setInterval(function () { if (ui.classList.contains("on")) saveTime(); }, 2000);
    addEventListener("pagehide", saveTime);

    // se replie en pastille pour ne pas gêner la lecture ; se déplie au survol, au focus ou au toucher
    var foldT;
    function fold() { if (!ui.matches(":hover") && !ui.contains(document.activeElement)) { ui.classList.add("mini"); requestAnimationFrame(scrollTitle); } }
    function unfold(later) { ui.classList.remove("mini"); clearTimeout(foldT); foldT = setTimeout(fold, later || 3500); requestAnimationFrame(scrollTitle); }
    ui.addEventListener("pointerenter", function () { unfold(); });
    ui.addEventListener("pointerleave", function () { clearTimeout(foldT); foldT = setTimeout(fold, 1200); });
    ui.addEventListener("focusin", function () { unfold(); });
    ui.addEventListener("click", function (e) { if (ui.classList.contains("mini") && !e.target.closest(".pa-play")) unfold(); });
    addEventListener("scroll", function () { if (!ui.matches(":hover") && !ui.classList.contains("mini")) { clearTimeout(foldT); fold(); } }, { passive: true });
    addEventListener("resize", function () { requestAnimationFrame(scrollTitle); });

    setState(false);
    fetchMeta(game);
    unfold(4000);
    store.set("last", game);
    // arrivée par un lien extérieur ou un rechargement alors que la musique était en route :
    // le navigateur exige un geste ; le bouton pulse et un clic dessus relance la musique là où elle était
    if (store.get("on", "0") === "1") ui.classList.add("resume");

    return {
      // nouvelle page : on garde la musique, sauf si l'on passe à l'autre jeu
      page: function () {
        var g = pageGame();
        if (!g || g === game) return;
        saveTime();
        game = g; store.set("last", g);
        ui.classList.remove("ge", "pd"); ui.classList.add(g);
        fetchMeta(g);
        var id = AUDIO[g].id, at = Math.floor(+store.get("t-" + id, "0"));
        if (ready) {
          if (want) player.loadVideoById({ videoId: id, startSeconds: at });
          else player.cueVideoById({ videoId: id, startSeconds: at });
        }
        render();
        unfold(3000);
      },
      pauseForVideo: function () { if (ui.classList.contains("on")) pause(); }
    };
  })();

  // ------------------------------------------------------------ harmonie automatique des rangées
  // Pastilles (.jump, .stats) : on resserre la largeur jusqu'à des lignes équilibrées.
  // Cartes (ul.links, .grid, .videos) : un nombre de colonnes qui ne laisse jamais une carte seule.
  function rowsOf(el) {
    var tops = [];
    for (var i = 0; i < el.children.length; i++) {
      var t = el.children[i].offsetTop;
      if (tops.indexOf(t) < 0) tops.push(t);
    }
    return tops.length;
  }
  function balancePills(el) {
    el.style.maxWidth = "";
    var rows = rowsOf(el);
    if (rows < 2) return;
    var lo = 0, hi = el.clientWidth;
    while (hi - lo > 4) {
      var mid = (lo + hi) >> 1;
      el.style.maxWidth = mid + "px";
      if (rowsOf(el) > rows) lo = mid; else hi = mid;
    }
    el.style.maxWidth = (hi + 2) + "px";
  }
  function balanceCards(el) {
    el.removeAttribute("data-cols");
    var items = el.children, n = items.length;
    if (n < 3) return;
    var cs = getComputedStyle(el), gap = parseFloat(cs.columnGap) || 0, W = el.clientWidth;
    var basis = parseFloat(getComputedStyle(items[0]).flexBasis) || items[0].getBoundingClientRect().width;
    var cols = Math.max(1, Math.floor((W + gap) / (basis + gap)));
    if (cols < 2 || n <= cols || n % cols !== 1) return;
    var best = 0;
    for (var c = cols - 1; c >= 2 && !best; c--) if (n % c === 0) best = c;
    for (c = cols - 1; c >= 2 && !best; c--) if (n % c !== 1) best = c;
    if (!best && cols + 1 <= n) best = cols + 1;
    if (best) { el.setAttribute("data-cols", ""); el.style.setProperty("--cols", best); }
  }
  function harmonize() {
    $$(".jump, .stats").forEach(balancePills);
    $$("ul.links, .grid, .videos").forEach(balanceCards);
  }
  var hzT; addEventListener("resize", function () { clearTimeout(hzT); hzT = setTimeout(harmonize, 120); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(harmonize);
  addEventListener("load", harmonize);

  // ------------------------------------------------------------ menu du haut : indicateur qui glisse
  function setupNav() {
    $$("nav.main ul").forEach(function (ul) {
      var ind = ul.querySelector(".nav-ind");
      if (!ind) return;
      function to(a) {
        var r = a.getBoundingClientRect(), p = ul.getBoundingClientRect();
        ind.style.setProperty("--x", (r.left - p.left) + "px");
        ind.style.setProperty("--w", r.width + "px");
      }
      ul.querySelectorAll("a").forEach(function (a) {
        a.addEventListener("pointerenter", function () {
          if (!ul.classList.contains("hovering")) { ind.style.transition = "none"; to(a); ind.offsetWidth; ind.style.transition = ""; }
          ul.classList.add("hovering"); to(a);
        });
      });
      ul.addEventListener("pointerleave", function () { ul.classList.remove("hovering"); });
    });
  }

  // ------------------------------------------------------------ chiffres de l'accueil et apparitions
  function fmt(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " "); }
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
  var io = ("IntersectionObserver" in window && !calm) ? new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
  }, { rootMargin: "0px 0px -40px 0px" }) : null;
  function setupReveal() {
    if (!io) return;
    $$("[data-count]").forEach(function (el) { el.textContent = "0"; setTimeout(function () { count(el); }, 900); });
    $$(".game, ul.links li, .card, .theme h2, .content > :not(.gallery), .gallery figure, .pager a, .videos .yt").forEach(function (el) {
      var r = el.getBoundingClientRect();
      if (r.top < innerHeight) return; // déjà visible : pas d'animation au chargement
      var sib = el.parentElement ? Array.prototype.indexOf.call(el.parentElement.children, el) : 0;
      el.style.setProperty("--d", Math.min(sib % 6, 5));
      el.classList.add("reveal");
      io.observe(el);
    });
  }

  // ------------------------------------------------------------ préparation de chaque page
  function initPage() {
    var toggle = $(".theme-toggle");
    if (toggle) toggle.setAttribute("aria-pressed", current() === "light");
    onScroll();
    tickClock();
    setupMarquees();
    setupTilt();
    harmonize();
    setupNav();
    setupReveal();
  }
  initPage();

  // ------------------------------------------------------------ navigation sans rechargement
  // Les liens internes chargent la page suivante en arrière-plan et remplacent le contenu :
  // l'adresse, le titre, les métadonnées et le bouton « précédent » restent ceux d'une vraie page.
  if (!window.fetch || !window.DOMParser || !history.pushState) return;
  var base = new URL(".", (function () {
    var s = document.currentScript || $('script[src*="assets/site.js"]');
    return s ? new URL("..", s.src).href : location.href;
  })()).href; // racine du site (…/tim/)
  var cache = {}, shown = location.pathname + location.search;
  function eligible(a, e) {
    if (!a || a.target && a.target !== "_self" || a.hasAttribute("download")) return false;
    if (e && (e.defaultPrevented || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey)) return false;
    if (a.closest(".gallery .zoom, .yt-go, .game-audio")) return false;
    var u = new URL(a.href, location.href);
    if (u.origin !== location.origin || u.href.indexOf(base) !== 0) return false;
    if (!/(\/|\.html?|\/[^\/.]+)$/.test(u.pathname)) return false; // pages seulement, pas les fichiers
    if (u.pathname === location.pathname && u.search === location.search && u.hash) return false; // ancre sur la même page
    return u;
  }
  function get(url) {
    var k = url.split("#")[0];
    if (!cache[k]) cache[k] = fetch(k, { credentials: "same-origin" }).then(function (r) {
      if (!r.ok || !/html/.test(r.headers.get("content-type") || "")) throw new Error(r.status);
      return r.text();
    });
    cache[k].catch(function () { delete cache[k]; });
    return cache[k];
  }
  function swap(htmlText, url) {
    var doc = new DOMParser().parseFromString(htmlText, "text/html");
    // titre et métadonnées (description, partage, adresse canonique, données structurées)
    document.title = doc.title;
    var sel = 'meta[name="description"],link[rel="canonical"],meta[property^="og:"],meta[name^="twitter:"],script[type="application/ld+json"],meta[name="theme-color"]';
    $$(sel).forEach(function (n) { if (n.parentNode === document.head) n.remove(); });
    Array.prototype.forEach.call(doc.head.querySelectorAll(sel), function (n) { document.head.appendChild(document.importNode(n, true)); });
    // contenu : tout est remplacé, sauf le lecteur audio (et sa vidéo cachée) et la visionneuse d'images
    var keep = document.querySelector(".game-audio");
    if (box) closeBox();
    Array.prototype.slice.call(document.body.childNodes).forEach(function (n) {
      if (n !== keep && n !== box) document.body.removeChild(n);
    });
    var ref = document.body.firstChild;
    Array.prototype.slice.call(doc.body.childNodes).forEach(function (n) {
      if (n.nodeName === "SCRIPT") return;
      document.body.insertBefore(document.importNode(n, true), ref);
    });
    document.body.className = doc.body.className;
    if (!calm) { document.body.classList.add("swapped"); setTimeout(function () { document.body.classList.remove("swapped"); }, 600); }
    initPage();
    audio.page();
    var h = url.hash && document.getElementById(decodeURIComponent(url.hash.slice(1)));
    if (h) h.scrollIntoView(); else scrollTo(0, 0);
    onScroll();
  }
  function navigate(url, push) {
    document.body.classList.add("loading");
    return get(url.href).then(function (t) {
      if (push) history.pushState({ pj: 1 }, "", url.href);
      shown = url.pathname + url.search;
      swap(t, url);
      document.body.classList.remove("loading");
    }).catch(function () { location.href = url.href; });
  }
  history.replaceState({ pj: 1 }, "", location.href);
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("a[href]");
    var u = eligible(a, e);
    if (!u) return;
    e.preventDefault();
    if (u.href === location.href) { scrollTo({ top: 0, behavior: calm ? "auto" : "smooth" }); return; }
    navigate(u, true);
  });
  // préchargement au survol : la page suivante est souvent prête avant le clic
  document.addEventListener("pointerover", function (e) {
    var a = e.target.closest && e.target.closest("a[href]");
    var u = a && eligible(a);
    if (u && u.pathname !== location.pathname) get(u.href);
  }, { passive: true });
  addEventListener("popstate", function () {
    // une simple ancre de la même page : le navigateur s'en charge
    if (location.pathname + location.search === shown) return;
    navigate(new URL(location.href), false);
  });
})();
