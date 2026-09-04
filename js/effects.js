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

/* ---------- 4. lab mascot: click-to-run distillation toy ---------- */
/* Click the wheel: the mascot takes off running, the pot flask heats,
   vapour travels through the condenser to the receiving flask, and the
   pot's mixed colour separates into its two components -- one ends up
   in the receiver, the other stays behind. One run at a time; clicks
   are ignored while a run is already in progress. Purely decorative,
   not real chemistry. */
(function () {
  "use strict";

  var rig = document.getElementById("mascot-rig");
  if (!rig) return;
  var svg = rig.querySelector("svg");
  var control = document.getElementById("mascot-wheel-control");
  var potLiquid = document.getElementById("liquid-pot");
  var recLiquid = document.getElementById("liquid-receiver");
  if (!svg || !control || !potLiquid || !recLiquid) return;

  var PAIRS = [
    { mix: "#8e5ec9", a: "#3d7fd6", b: "#e0457b" },
    { mix: "#2f8f6f", a: "#29abe2", b: "#e6c73d" },
    { mix: "#c1546a", a: "#ff8a3d", b: "#7a4fd6" },
    { mix: "#5fae8f", a: "#5fbf7a", b: "#f2b807" }
  ];

  var START_LINES = [
    "New reaction, here we go!",
    "Let's make something new.",
    "Spinning up an experiment…",
    "Fingers crossed for a new compound."
  ];
  var MID_LINES = [
    "Distilling…",
    "Could be something new in there.",
    "Almost separated…",
    "This one might be paper-worthy."
  ];
  var DONE_LINES = [
    ["Hooray, a new substance!", "New paper soon — see our papers."],
    ["We got something new!", "Watch for the paper meanwhile."],
    ["New compound, logged!", "A paper's coming — read our work."],
    ["Success in the wheel!", "New paper ahead — see what's out."]
  ];

  var DURATION = 6000;
  var RECEIVER_MAX_H = 48;
  var RECEIVER_BOTTOM = 330;

  var WAYPOINTS = [
    { x: 340, y: 225 },
    { x: 340, y: 150 },
    { x: 340, y: 115 },
    { x: 362, y: 130 },
    { x: 372, y: 140 },
    { x: 520, y: 262 },
    { x: 548, y: 280 },
    { x: 547, y: 303 }
  ];

  var state = { pair: randomOf(PAIRS), progress: 0, running: false, lastTs: 0 };
  var bubbleTimer = null, vaporTimer = null, midTimer = null;

  var speech = rig.querySelector("#mascot-speech");
  var speechL1 = rig.querySelector("#mascot-speech-l1");
  var speechL2 = rig.querySelector("#mascot-speech-l2");
  var jumpLink = rig.querySelector("#mascot-jump");
  var hideTimer = null;

  function randomOf(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

  function say(line1, line2, withJump) {
    if (!speech) return;
    speechL1.textContent = line1 || "";
    speechL2.textContent = line2 || "";
    speech.setAttribute("opacity", "1");
    if (jumpLink) jumpLink.setAttribute("opacity", withJump ? "1" : "0");
    window.clearTimeout(hideTimer);
    if (!withJump) {
      hideTimer = window.setTimeout(function () { speech.setAttribute("opacity", "0"); }, 2800);
    }
  }

  function sayOne(text) { say(text, ""); }

  function hexToRgb(hex) {
    var n = parseInt(hex.replace("#", ""), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function rgbToHex(r, g, b) {
    function h(v) { v = Math.max(0, Math.min(255, Math.round(v))); var s = v.toString(16); return s.length < 2 ? "0" + s : s; }
    return "#" + h(r) + h(g) + h(b);
  }
  function lerpColor(c1, c2, t) {
    var a = hexToRgb(c1), b = hexToRgb(c2);
    return rgbToHex(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t);
  }

  function applyProgress() {
    potLiquid.setAttribute("fill", lerpColor(state.pair.mix, state.pair.b, state.progress));
    var h = RECEIVER_MAX_H * state.progress;
    recLiquid.setAttribute("y", String(RECEIVER_BOTTOM - h));
    recLiquid.setAttribute("height", String(h));
    recLiquid.setAttribute("fill", state.pair.a);
  }

  function resetPair() {
    state.pair = randomOf(PAIRS);
    state.progress = 0;
    applyProgress();
    window.clearTimeout(hideTimer);
    speech.setAttribute("opacity", "0");
    if (jumpLink) jumpLink.setAttribute("opacity", "0");
  }

  function spawnBubbles() {
    var box;
    try { box = potLiquid.getBBox(); } catch (e) { return; }
    var ns = "http://www.w3.org/2000/svg";
    for (var i = 0; i < 3; i++) {
      var b = document.createElementNS(ns, "circle");
      var cx = box.x + Math.random() * box.width;
      var r = 1.5 + Math.random() * 2.5;
      b.setAttribute("cx", String(cx));
      b.setAttribute("cy", String(box.y + box.height - 2));
      b.setAttribute("r", String(r));
      b.setAttribute("fill", "rgba(255,255,255,.8)");
      b.setAttribute("class", "mascot-bubble");
      b.style.setProperty("--rise", (10 + Math.random() * 14) + "px");
      svg.appendChild(b);
      (function (el) { window.setTimeout(function () { el.remove(); }, 1200); })(b);
    }
  }

  function spawnVapor() {
    var ns = "http://www.w3.org/2000/svg";
    var dot = document.createElementNS(ns, "circle");
    dot.setAttribute("r", "4");
    dot.setAttribute("fill", "rgba(255,255,255,.85)");
    dot.setAttribute("class", "mascot-vapor");
    dot.setAttribute("cx", String(WAYPOINTS[0].x));
    dot.setAttribute("cy", String(WAYPOINTS[0].y));
    svg.appendChild(dot);
    var segDur = 200;
    var totalSegs = WAYPOINTS.length - 1;
    var startTs = null;
    function frame(ts) {
      if (!dot.isConnected) return;
      if (startTs === null) startTs = ts;
      var elapsed = ts - startTs;
      var segIdx = Math.min(totalSegs - 1, Math.floor(elapsed / segDur));
      var segT = Math.min(1, (elapsed - segIdx * segDur) / segDur);
      var p0 = WAYPOINTS[segIdx], p1 = WAYPOINTS[segIdx + 1];
      dot.setAttribute("cx", String(p0.x + (p1.x - p0.x) * segT));
      dot.setAttribute("cy", String(p0.y + (p1.y - p0.y) * segT));
      dot.setAttribute("opacity", String(1 - elapsed / (segDur * totalSegs)));
      if (elapsed < segDur * totalSegs) {
        window.requestAnimationFrame(frame);
      } else {
        dot.remove();
      }
    }
    window.requestAnimationFrame(frame);
  }

  function clearTimers() {
    window.clearInterval(bubbleTimer); bubbleTimer = null;
    window.clearInterval(vaporTimer); vaporTimer = null;
    window.clearInterval(midTimer); midTimer = null;
  }

  function onComplete() {
    var done = randomOf(DONE_LINES);
    say(done[0], done[1], true);
    stopRunning();
  }

  function startRunning() {
    if (state.running) return;
    if (state.progress >= 1) { resetPair(); }
    state.running = true;
    state.lastTs = 0;
    rig.classList.add("running");
    sayOne(randomOf(START_LINES));
    bubbleTimer = window.setInterval(spawnBubbles, 380);
    vaporTimer = window.setInterval(spawnVapor, 480);
    midTimer = window.setInterval(function () { sayOne(randomOf(MID_LINES)); }, 2600);
    window.requestAnimationFrame(tick);
  }

  function stopRunning() {
    state.running = false;
    rig.classList.remove("running");
    clearTimers();
  }

  function tick(ts) {
    if (!state.running) return;
    if (!state.lastTs) state.lastTs = ts;
    var dt = ts - state.lastTs;
    state.lastTs = ts;
    state.progress = Math.min(1, state.progress + dt / DURATION);
    applyProgress();
    if (state.progress >= 1) { onComplete(); return; }
    window.requestAnimationFrame(tick);
  }

  applyProgress();

  control.addEventListener("click", function (e) { e.preventDefault(); startRunning(); });
  control.addEventListener("keydown", function (e) {
    if ((e.key === "Enter" || e.key === " ") && !e.repeat) { e.preventDefault(); startRunning(); }
  });
})();
