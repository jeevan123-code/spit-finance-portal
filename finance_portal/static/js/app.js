/* SPIT Finance Portal — interactions: glow cursor, card tilt, reveal,
   toasts, dynamic line items, modals, sidebar. Vanilla JS, no deps. */
(function () {
  "use strict";
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ── Reveal on scroll (staggered) ──────────────────────────────────── */
  const reveals = document.querySelectorAll(".reveal");
  if (reveals.length && !reduced && "IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry, i) => {
        if (entry.isIntersecting) {
          const el = entry.target;
          const delay = parseInt(el.dataset.delay || (i % 8) * 45, 10);
          setTimeout(() => el.classList.add("in"), delay);
          io.unobserve(el);
        }
      });
    }, { threshold: 0.08 });
    reveals.forEach((el) => io.observe(el));
  } else {
    reveals.forEach((el) => el.classList.add("in"));
  }

  /* ── Animated count-up for [data-count] ────────────────────────────── */
  document.querySelectorAll("[data-count]").forEach((el) => {
    const target = parseFloat(el.dataset.count) || 0;
    const prefix = el.dataset.prefix || "";
    const isInt = el.hasAttribute("data-int");
    const fmt = (v) => prefix + (isInt
      ? Math.round(v).toLocaleString("en-IN")
      : v.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
    if (reduced) { el.textContent = fmt(target); return; }
    const dur = 850; const start = performance.now();
    (function tick(now) {
      const t = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - t, 3);
      el.textContent = fmt(target * eased);
      if (t < 1) requestAnimationFrame(tick);
    })(start);
  });

  /* ── Toast auto-dismiss ────────────────────────────────────────────── */
  document.querySelectorAll(".toast").forEach((t) => {
    setTimeout(() => {
      t.classList.add("hide");
      setTimeout(() => t.remove(), 300);
    }, 4500);
  });

  /* ── Sidebar (mobile) ──────────────────────────────────────────────── */
  const menuBtn = document.querySelector(".menu-btn");
  const sidebar = document.querySelector(".sidebar");
  if (menuBtn && sidebar) {
    menuBtn.addEventListener("click", () => sidebar.classList.toggle("open"));
    document.addEventListener("click", (e) => {
      if (window.innerWidth <= 900 && sidebar.classList.contains("open") &&
          !e.target.closest(".sidebar") && !e.target.closest(".menu-btn")) {
        sidebar.classList.remove("open");
      }
    });
  }

  /* ── Modals (data-modal-open="id" / data-modal-close) ──────────────── */
  document.querySelectorAll("[data-modal-open]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const m = document.getElementById(btn.dataset.modalOpen);
      if (m) m.classList.add("open");
    });
  });
  document.querySelectorAll(".modal-backdrop").forEach((bk) => {
    bk.addEventListener("click", (e) => {
      if (e.target === bk || e.target.closest("[data-modal-close]")) bk.classList.remove("open");
    });
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape")
      document.querySelectorAll(".modal-backdrop.open").forEach((m) => m.classList.remove("open"));
  });

  /* ── Dynamic line-item rows ────────────────────────────────────────── */
  document.querySelectorAll("[data-repeater]").forEach((rep) => {
    const body = rep.querySelector("[data-rows]");
    const tplId = rep.dataset.repeater;
    const tpl = document.getElementById(tplId);
    const addBtn = rep.querySelector("[data-add-row]");

    function recalc() {
      let total = 0;
      body.querySelectorAll("[data-row]").forEach((row) => {
        const qtyEl = row.querySelector("[data-qty]");
        const costEl = row.querySelector("[data-cost]");
        const amtEl = row.querySelector("[data-amount]");
        let amount;
        if (qtyEl && costEl) {
          amount = (parseFloat(qtyEl.value) || 0) * (parseFloat(costEl.value) || 0);
          const lineEl = row.querySelector("[data-line]");
          if (lineEl) lineEl.textContent = "₹" + amount.toLocaleString("en-IN",
            { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        } else if (amtEl) {
          amount = parseFloat(amtEl.value) || 0;
        } else { amount = 0; }
        total += amount;
      });
      const totalEl = rep.querySelector("[data-total]");
      if (totalEl) totalEl.textContent = "₹" + total.toLocaleString("en-IN",
        { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function wire(row) {
      row.querySelectorAll("input").forEach((i) =>
        i.addEventListener("input", recalc));
      const rm = row.querySelector("[data-remove]");
      if (rm) rm.addEventListener("click", () => {
        row.style.transition = "opacity .2s, transform .2s";
        row.style.opacity = "0"; row.style.transform = "translateX(12px)";
        setTimeout(() => { row.remove(); recalc(); }, 180);
      });
    }

    function addRow() {
      const frag = tpl.content.cloneNode(true);
      const row = frag.querySelector("[data-row]");
      body.appendChild(frag);
      wire(row);
      const first = row.querySelector("input");
      if (first) first.focus();
      recalc();
    }

    if (addBtn) addBtn.addEventListener("click", addRow);
    body.querySelectorAll("[data-row]").forEach(wire);
    recalc();
    if (!body.querySelector("[data-row]")) addRow();
  });

  /* ── Confirm before destructive submit ─────────────────────────────── */
  document.querySelectorAll("form[data-confirm]").forEach((f) => {
    f.addEventListener("submit", (e) => {
      if (!window.confirm(f.dataset.confirm)) e.preventDefault();
    });
  });
})();
