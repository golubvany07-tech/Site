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

  var BLUE = "21,104,184"; // --blue #1568b8
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

        ctx.fillStyle = "rgba(" + BLUE + ",0.42)";
        ctx.beginPath(); ctx.arc(p.x, p.y, 1.8, 0, 6.2832); ctx.fill();
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
