let isOpen = false,
  selectedType = "milestone",
  selectedMood = 1,
  entryCount = 0;

(function init() {
  const now = new Date();
  document.getElementById("cover-year").textContent = now.getFullYear();
  document.getElementById("month-label").textContent =
    "— " +
    now.toLocaleDateString("en-GB", {
      month: "long",
      year: "numeric",
    }) +
    " —";
  const d = now.getDate();
  const s =
    d === 1 || d === 21 || d === 31
      ? "st"
      : d === 2 || d === 22
        ? "nd"
        : d === 3 || d === 23
          ? "rd"
          : "th";
  document.getElementById("date-display").textContent =
    now.toLocaleDateString("en-GB", { weekday: "long" }) + ", the " + d + s;
  try {
    const m = now.getFullYear() + "-" + (now.getMonth() + 1);
    const all = JSON.parse(localStorage.getItem("journal_entries") || "[]");
    entryCount = all.filter((e) => {
      const ed = new Date(e.date);
      return ed.getFullYear() + "-" + (ed.getMonth() + 1) === m;
    }).length;
  } catch (e) {}
  updateCount();
})();

function updateCount() {
  document.getElementById("entry-count-display").textContent =
    entryCount + " entr" + (entryCount === 1 ? "y" : "ies") + " this month";
}

function openJournal() {
  if (isOpen) return;
  isOpen = true;
  const journal = document.getElementById("journal");
  const spread = document.getElementById("spread");
  const isMobile = window.innerWidth <= 600;

  // Press down, then blast to fill screen (zoom transition)
  anime({
    targets: journal,
    scale: [1, 0.95, 1.08, 22],
    opacity: [1, 1, 1, 0],
    duration: 880,
    easing: "easeInExpo",
    complete: () => {
      journal.style.display = "none";
      spread.style.display = "block";
      const startScale = isMobile ? 0.85 : 0.7;
      spread.style.transform = "scale(" + startScale + ")";
      anime({
        targets: spread,
        opacity: [0, 1],
        scale: [startScale, 1],
        duration: 680,
        easing: "easeOutExpo",
      });
    },
  });
}

function selectType(btn) {
  document
    .querySelectorAll(".type-btn")
    .forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");
  selectedType = btn.dataset.type;
  anime({
    targets: btn,
    scale: [0.9, 1],
    duration: 210,
    easing: "easeOutBack",
  });
}

function selectMood(dot) {
  document
    .querySelectorAll(".mood-dot")
    .forEach((d) => d.classList.remove("sel"));
  dot.classList.add("sel");
  selectedMood = parseInt(dot.dataset.mood);
  anime({
    targets: dot,
    scale: [0.6, 1.25, 1],
    duration: 300,
    easing: "easeOutElastic(1, 0.5)",
  });
}

function submitEntry() {
  const text = document.getElementById("entry-text").value.trim();
  if (!text) {
    anime({
      targets: "#entry-text",
      translateX: [0, -8, 8, -5, 5, -2, 2, 0],
      duration: 370,
      easing: "easeInOutSine",
    });
    return;
  }
  try {
    const now = new Date(),
      m = now.getFullYear() + "-" + (now.getMonth() + 1);
    const all = JSON.parse(localStorage.getItem("journal_entries") || "[]");
    all.push({
      type: selectedType,
      mood: selectedMood,
      text,
      date: now.toISOString(),
    });
    localStorage.setItem("journal_entries", JSON.stringify(all));
    entryCount = all.filter((e) => {
      const ed = new Date(e.date);
      return ed.getFullYear() + "-" + (ed.getMonth() + 1) === m;
    }).length;
    updateCount();
  } catch (e) {}
  anime({
    targets: "#submit-btn",
    scale: [1, 0.93, 1],
    duration: 170,
    easing: "easeInOutSine",
  });
  setTimeout(pageTurnAnimation, 130);
}

function pageTurnAnimation() {
  const formArea = document.getElementById("log-form-area");
  const submitted = document.getElementById("submitted-page");
  anime({
    targets: "#page-left",
    skewX: [0, -1.2, 0],
    duration: 660,
    easing: "easeInOutSine",
  });
  anime({
    targets: formArea,
    opacity: [1, 0],
    translateX: [0, -14],
    duration: 360,
    easing: "easeInSine",
    complete: () => {
      formArea.style.display = "none";
      submitted.style.display = "flex";
      anime({
        targets: submitted,
        opacity: [0, 1],
        translateY: [8, 0],
        duration: 420,
        easing: "easeOutSine",
      });
      anime({
        targets: "#submitted-page .submitted-icon",
        rotate: [0, 11, -5, 0],
        scale: [0.4, 1.12, 1],
        duration: 580,
        delay: 70,
        easing: "easeOutElastic(1, 0.6)",
      });
      anime({
        targets:
          "#submitted-page h3, #submitted-page p, #submitted-page .entry-count",
        opacity: [0, 1],
        translateY: [5, 0],
        delay: anime.stagger(85, { start: 160 }),
        duration: 360,
        easing: "easeOutSine",
      });
    },
  });
  anime({
    targets: "#page-right",
    translateX: [0, 3, 0],
    duration: 660,
    easing: "easeInOutSine",
  });
  showToast("Entry sealed ✦");
}

function showToast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  anime.remove(t);
  anime({
    targets: t,
    keyframes: [
      { opacity: 0, translateY: 48, duration: 0 },
      {
        opacity: 1,
        translateY: 0,
        duration: 360,
        easing: "easeOutExpo",
      },
      { opacity: 1, translateY: 0, duration: 1700 },
      {
        opacity: 0,
        translateY: -7,
        duration: 460,
        easing: "easeInSine",
      },
    ],
  });
}
