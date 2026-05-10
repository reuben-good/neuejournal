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
