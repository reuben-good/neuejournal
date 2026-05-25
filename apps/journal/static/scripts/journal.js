// Align the binder rings with the punch holes
function alignRings() {
  requestAnimationFrame(() => {
    const journal = document.getElementById("journal");
    const binder = document.getElementById("binder");
    const rings = document.querySelectorAll(".binder-ring");
    const isMobile = window.innerWidth <= 600;

    const sourcePunches = document.querySelectorAll("#right-punches .punch");
    const journalRect = journal.getBoundingClientRect();
    const binderWidth = binder.offsetWidth;
    const binderRect = binder.getBoundingClientRect();

    sourcePunches.forEach((punch, i) => {
      if (!rings[i]) return;
      const punchRect = punch.getBoundingClientRect();
      const punchCentreY =
        punchRect.top + punchRect.height / 2 - binderRect.top;
      const ringHeight = rings[i].offsetHeight;
      rings[i].style.top = `${punchCentreY - ringHeight / 2}px`;
    });

    if (isMobile) {
      const punchStrip = document.querySelector("#right-punches .punches");
      const stripRect = punchStrip.getBoundingClientRect();
      const stripCentreX =
        stripRect.left + stripRect.width / 2 - journalRect.left;
      binder.style.left = `${stripCentreX - binderWidth / 2}px`;
      binder.style.top = "0";
      binder.style.transform = "none";
      binder.style.height = "100%";
    } else {
      const leftPage = document.getElementById("left-page");
      const rightPage = document.getElementById("right-page");
      const leftRect = leftPage.getBoundingClientRect();
      const rightRect = rightPage.getBoundingClientRect();

      // Pages' rects are viewport space; subtract journalRect.left to get
      // journal-local X (now that journal is the offset parent)
      const spineCentreX =
        (leftRect.right + rightRect.left) / 2 - journalRect.left;

      binder.style.left = `${spineCentreX - binderWidth / 2}px`;
      binder.style.top = "50%";
      binder.style.transform = "translateY(-50%)";
      binder.style.height = "calc(88vh - 1.7em)";
    }
  });
}

// Align rings on load and resize
window.addEventListener("load", alignRings);
window.addEventListener("resize", alignRings);

const buttons = document.querySelectorAll(".type-btn");
const hiddenInput = document.getElementById("entry_type");

buttons.forEach((button) => {
  button.addEventListener("click", () => {
    // remove active state
    buttons.forEach((btn) => btn.classList.remove("active"));

    // set active state
    button.classList.add("active");

    // update hidden field
    hiddenInput.value = button.dataset.type;
  });
});

// Prevent default dragover everywhere so drops always work
document.addEventListener("dragover", (e) => e.preventDefault());
// Single delegated dragstart listener — works for all stickers, even after panel reloads
document.addEventListener("dragstart", (e) => {
  if (!e.target.classList.contains("sticker-img")) return;
  e.dataTransfer.setData("text/plain", e.target.src);
  e.dataTransfer.setData("sticker-id", e.target.dataset.stickerid);

  const canvas = document.createElement("canvas");
  canvas.width = 64;
  canvas.height = 64;
  canvas.getContext("2d").drawImage(e.target, 0, 0, 64, 64);
  canvas.style.cssText = "position:fixed;top:-9999px";
  document.body.appendChild(canvas);
  e.dataTransfer.setDragImage(canvas, 32, 32);
  requestAnimationFrame(() => canvas.remove());

  window.panelManager.hideBackdropForDrag();
});
document.addEventListener("dragend", (e) => {
  if (!e.target.classList.contains("sticker-img")) return;
  // If dropped on a page, re-open the panel; otherwise just close
  window.panelManager.showAfterDrag();
});

function stickerdrop(e) {
  e.preventDefault();
  e.stopPropagation();

  const src = e.dataTransfer.getData("text/plain");
  if (!src) return;

  const stickerId = e.dataTransfer.getData("sticker-id");

  const page = e.target.closest(".page");
  if (!page) return;

  const rect = page.getBoundingClientRect();
  const xPct = ((e.clientX - rect.left) / rect.width) * 100;
  const yPct = ((e.clientY - rect.top) / rect.height) * 100;

  const img = document.createElement("img");
  img.src = src;
  img.classList.add("placed-sticker");
  img.style.left = `${xPct}%`;
  img.style.top = `${yPct}%`;
  page.appendChild(img);

  // Re-open the panel after drop
  window.panelManager.showAfterDrag();

  fetch("/stickers/place/", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "X-CSRFToken": document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? "",
      // No Content-Type header — let the browser set it for FormData
    },
    body: new URLSearchParams({
      x: xPct,
      y: yPct,
      page_id: page.dataset.pageId ?? "",
      sticker_id: stickerId ?? "",
    }),
  }).catch((err) => console.error("Failed to save sticker placement:", err));
}

for (let page of document.getElementsByClassName("page")) {
  page.addEventListener("drop", stickerdrop);
}
