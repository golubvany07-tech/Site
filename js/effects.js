/* Cursor effects for the Chusov Group site.
   Two delicate, chemistry-flavoured touches:
     1. molecular network in the hero (atoms + bonds, reaching toward the cursor)
     2. 3D tilt + light sheen on the image cards
   Progressive enhancement: does nothing on touch devices or when the visitor
   asks for reduced motion. Pure vanilla JS, no dependencies. */
(function () {
  "use strict";

  var mq = window.matchMedia;
  var reduce = mq && mq("(prefers-reduced-motion: reduce)").matches;
  var fine = mq && mq("(hover: hover) and (pointer: fine)").matches;
  if (reduce || !fine) return; // no cursor effects on touch / reduced-motion

  var BLUE = "242,184,7"; // --accent #f2b807
  var ACCENT2 = "255,138,61"; // --accent2 #ff8a3d -- "catalyst" click flash
  var mouse = { x: -9999, y: -9999, has: false };
  window.addEventListener("mousemove", function (e) {
    mouse.x = e.clientX; mouse.y = e.clientY; mouse.has = true;
  }, { passive: true });

  /* ---------- 1. molecular network (hero only) ---------- */
  var hero = document.querySelector(".hero");
  if (hero) {
    var canvas = document.createElement("canvas");
    canvas.className = "fx-net";
    canvas.setAttribute("aria-hidden", "true");
    hero.insertBefore(canvas, hero.firstChild);

    var ctx = canvas.getContext("2d");
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var nodes = [], W = 0, H = 0, raf = null;
    var bursts = []; // click ripples: {x, y, t0} -- "catch the catalyst"

    hero.addEventListener("click", function (e) {
      var r = hero.getBoundingClientRect();
      var cx = e.clientX - r.left, cy = e.clientY - r.top;
      if (cx < 0 || cx > W || cy < 0 || cy > H) return;
      var now = performance.now();
      bursts.push({ x: cx, y: cy, t0: now });
      if (bursts.length > 6) bursts.shift();
      for (var k = 0; k < nodes.length; k++) {
        var n = nodes[k];
        var dx = n.x - cx, dy = n.y - cy;
        var d = Math.sqrt(dx * dx + dy * dy) || 1;
        if (d < 130) {
          n.energized = now;
          var kick = (1 - d / 130) * 0.9;
          n.vx = Math.max(-1.4, Math.min(1.4, n.vx + (dx / d) * kick));
          n.vy = Math.max(-1.4, Math.min(1.4, n.vy + (dy / d) * kick));
        }
      }
    });

    function size() {
      var r = hero.getBoundingClientRect();
      W = r.width; H = r.height;
      canvas.width = Math.round(W * dpr);
      canvas.height = Math.round(H * dpr);
      canvas.style.width = W + "px";
      canvas.style.height = H + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var n = Math.max(14, Math.min(38, Math.round(W * H / 22000)));
      nodes = [];
      for (var i = 0; i < n; i++) {
        nodes.push({
          x: Math.random() * W, y: Math.random() * H,
          vx: (Math.random() - 0.5) * 0.28, vy: (Math.random() - 0.5) * 0.28
        });
      }
    }

    function draw() {
      ctx.clearRect(0, 0, W, H);
      var r = hero.getBoundingClientRect();
      var mx = mouse.x - r.left, my = mouse.y - r.top;
      var inHero = mouse.has && mx >= 0 && mx <= W && my >= 0 && my <= H;
      var now = performance.now();

      for (var b = bursts.length - 1; b >= 0; b--) {
        var age = now - bursts[b].t0;
        if (age > 650) { bursts.splice(b, 1); continue; }
        var t = age / 650;
        ctx.strokeStyle = "rgba(" + ACCENT2 + "," + (0.5 * (1 - t)).toFixed(3) + ")";
        ctx.lineWidth = 1.6;
        ctx.beginPath(); ctx.arc(bursts[b].x, bursts[b].y, 8 + t * 130, 0, 6.2832); ctx.stroke();
      }

      for (var i = 0; i < nodes.length; i++) {
        var p = nodes[i];
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > W) p.vx *= -1;
        if (p.y < 0 || p.y > H) p.vy *= -1;

        for (var j = i + 1; j < nodes.length; j++) {
          var q = nodes[j];
          var dx = p.x - q.x, dy = p.y - q.y;
          var d = Math.sqrt(dx * dx + dy * dy);
          if (d < 118) {
            ctx.strokeStyle = "rgba(" + BLUE + "," + (0.11 * (1 - d / 118)).toFixed(3) + ")";
            ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke();
          }
        }

        if (inHero) {
          var ddx = p.x - mx, ddy = p.y - my;
          var dm = Math.sqrt(ddx * ddx + ddy * ddy);
          if (dm < 150) {
            ctx.strokeStyle = "rgba(" + BLUE + "," + (0.38 * (1 - dm / 150)).toFixed(3) + ")";
            ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(mx, my); ctx.stroke();
          }
        }

        var glow = p.energized ? Math.max(0, 1 - (now - p.energized) / 900) : 0;
        if (glow > 0) {
          ctx.fillStyle = "rgba(" + ACCENT2 + "," + (0.5 + glow * 0.4).toFixed(3) + ")";
          ctx.beginPath(); ctx.arc(p.x, p.y, 1.8 + glow * 3.4, 0, 6.2832); ctx.fill();
        } else {
          ctx.fillStyle = "rgba(" + BLUE + ",0.42)";
          ctx.beginPath(); ctx.arc(p.x, p.y, 1.8, 0, 6.2832); ctx.fill();
        }
      }
      raf = requestAnimationFrame(draw);
    }

    function play() { if (!raf) raf = requestAnimationFrame(draw); }
    function pause() { if (raf) { cancelAnimationFrame(raf); raf = null; } }

    size();
    var rt;
    window.addEventListener("resize", function () { clearTimeout(rt); rt = setTimeout(size, 150); }, { passive: true });

    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { en.isIntersecting ? play() : pause(); });
      }, { threshold: 0 }).observe(hero);
    } else {
      play();
    }
  }

  /* ---------- 2. 3D tilt + sheen on image cards ---------- */
  var MAX = 6; // degrees — deliberately gentle
  var cards = document.querySelectorAll(".pub-card, .person-card, .alum-card");
  Array.prototype.forEach.call(cards, function (card) {
    var sheen = document.createElement("span");
    sheen.className = "fx-sheen";
    sheen.setAttribute("aria-hidden", "true");
    card.appendChild(sheen);

    card.addEventListener("mousemove", function (e) {
      var r = card.getBoundingClientRect();
      var px = (e.clientX - r.left) / r.width;
      var py = (e.clientY - r.top) / r.height;
      card.style.transform =
        "perspective(760px) rotateX(" + ((0.5 - py) * MAX).toFixed(2) +
        "deg) rotateY(" + ((px - 0.5) * MAX).toFixed(2) + "deg)";
      card.style.setProperty("--fx-mx", (px * 100).toFixed(1) + "%");
      card.style.setProperty("--fx-my", (py * 100).toFixed(1) + "%");
      card.classList.add("fx-lit");
    }, { passive: true });

    card.addEventListener("mouseleave", function () {
      card.style.transform = "";
      card.classList.remove("fx-lit");
    });
  });
})();

/* ---------- 3. "Life in the lab" mosaic rotation ---------- */
/* Periodically swaps a tile's photo in from a larger, curated pool so the
   mosaic keeps feeling current. Runs everywhere (including touch and
   reduced-motion, unlike the cursor effects above) since it's a content
   swap, not a continuous animation; reduced-motion visitors just get one
   shuffle on load instead of a repeating timer. */
(function () {
  "use strict";

  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function shuffle(arr) {
    for (var i = arr.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = arr[i]; arr[i] = arr[j]; arr[j] = t;
    }
    return arr;
  }

  function initRotator(container) {
    var poolScript = document.getElementById(container.id + "-pool");
    if (!poolScript) return;
    var pool;
    try { pool = JSON.parse(poolScript.textContent); } catch (e) { return; }
    var slots = Array.prototype.slice.call(container.querySelectorAll(".ph"));
    if (!pool || !pool.length || !slots.length) return;

    var shown = slots.map(function (el) { return el.getAttribute("data-img"); });

    function applyTo(slot, item) {
      var img = slot.querySelector("img");
      var cap = slot.querySelector(".cap");
      slot.setAttribute("data-img", item.img);
      var base = container.id === "gallery-home" ? "news.html" : "";
      slot.setAttribute("href", item.anchor ? (base + "#" + item.anchor) : (base || "news.html"));
      if (img) { img.src = "assets/" + item.img; img.alt = item.alt; }
      if (cap) { cap.textContent = item.alt; }
    }

    function swapOne() {
      var idx = Math.floor(Math.random() * slots.length);
      var slot = slots[idx];
      var candidates = pool.filter(function (p) { return shown.indexOf(p.img) === -1; });
      if (!candidates.length) return; // pool fully shown -- nothing fresh to rotate in
      var next = candidates[Math.floor(Math.random() * candidates.length)];
      var prevImg = slot.getAttribute("data-img");
      shown[idx] = next.img;
      slot.style.opacity = "0";
      window.setTimeout(function () {
        applyTo(slot, next);
        slot.style.opacity = "1";
      }, 420);
      void prevImg;
    }

    if (pool.length > slots.length) {
      if (reduce) {
        swapOne();
      } else {
        window.setInterval(swapOne, 9000);
      }
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    Array.prototype.forEach.call(document.querySelectorAll(".lablife[id]"), initRotator);
  });
})();

/* ---------- gallery carousel arrows (blog page) ---------- */
(function () {
  function initCarousel(car) {
    var track = car.querySelector(".lc-track");
    var prev = car.querySelector(".lc-prev");
    var next = car.querySelector(".lc-next");
    if (!track || !prev || !next) return;

    function step() { return Math.max(track.clientWidth * 0.8, 240); }
    prev.addEventListener("click", function () {
      track.scrollBy({ left: -step(), behavior: "smooth" });
    });
    next.addEventListener("click", function () {
      track.scrollBy({ left: step(), behavior: "smooth" });
    });

    function updateArrows() {
      var max = track.scrollWidth - track.clientWidth - 2;
      prev.disabled = track.scrollLeft <= 2;
      next.disabled = max <= 2 || track.scrollLeft >= max;
    }
    track.addEventListener("scroll", updateArrows, { passive: true });
    window.addEventListener("resize", updateArrows);
    updateArrows();
  }

  document.addEventListener("DOMContentLoaded", function () {
    Array.prototype.forEach.call(document.querySelectorAll(".lablife-carousel"), initCarousel);
  });
})();

/* ---------- 4. hero emblem: ring spins in place, click eases into a slow scroll ---------- */
(function () {
  "use strict";
  var emblem = document.getElementById("hero-emblem");
  var ring = document.querySelector(".emblem-ring");
  var target = document.getElementById("publications");
  if (!emblem || !ring || !target) return;

  var mq = window.matchMedia;
  var reduceMotion = mq && mq("(prefers-reduced-motion: reduce)").matches;

  function easeInOutCubic(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }
  function easeInOutQuad(t) { return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; }

  var IDLE_DEG_PER_MS = 360 / 22000;
  var BOOST_DEG_PER_MS = 360 / 2600;
  var SPIN_UP_MS = 650;
  var CRUISE_MS = 500;
  var SPIN_DOWN_MS = 1400;

  var angle = 0;
  var lastTime = null;
  var boosting = false;
  var boostStart = 0;

  function speedAt(now) {
    if (!boosting) return IDLE_DEG_PER_MS;
    var elapsed = now - boostStart;
    if (elapsed < SPIN_UP_MS) {
      return IDLE_DEG_PER_MS + (BOOST_DEG_PER_MS - IDLE_DEG_PER_MS) * easeInOutCubic(elapsed / SPIN_UP_MS);
    }
    if (elapsed < SPIN_UP_MS + CRUISE_MS) {
      return BOOST_DEG_PER_MS;
    }
    if (elapsed < SPIN_UP_MS + CRUISE_MS + SPIN_DOWN_MS) {
      var p = easeInOutCubic((elapsed - SPIN_UP_MS - CRUISE_MS) / SPIN_DOWN_MS);
      return BOOST_DEG_PER_MS + (IDLE_DEG_PER_MS - BOOST_DEG_PER_MS) * p;
    }
    boosting = false;
    return IDLE_DEG_PER_MS;
  }

  function frame(now) {
    if (lastTime === null) lastTime = now;
    var dt = now - lastTime;
    lastTime = now;
    angle = (angle + speedAt(now) * dt) % 360;
    ring.style.transform = "rotate(" + angle + "deg)";
    requestAnimationFrame(frame);
  }
  if (!reduceMotion) requestAnimationFrame(frame);

  function smoothScrollTo(el, duration) {
    var startY = window.scrollY;
    var endY = el.getBoundingClientRect().top + window.scrollY;
    var startTime = null;
    function step(ts) {
      if (startTime === null) startTime = ts;
      var t = Math.min((ts - startTime) / duration, 1);
      window.scrollTo(0, startY + (endY - startY) * easeInOutQuad(t));
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function go() {
    if (reduceMotion) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    if (boosting) return;
    boosting = true;
    boostStart = performance.now();
    window.setTimeout(function () {
      smoothScrollTo(target, 2200);
    }, 380);
  }

  emblem.addEventListener("click", go);
  emblem.addEventListener("keydown", function (e) {
    if ((e.key === "Enter" || e.key === " ") && !e.repeat) { e.preventDefault(); go(); }
  });
})();
