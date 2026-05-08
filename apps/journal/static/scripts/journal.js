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

window.onload = function () {
  const d = new Date();
  const monthEl = this.document.getElementById("month");
  const yearEl = this.document.getElementById("year");
  const dateEl = this.document.getElementById("date");
  const months = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];
  const days = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
  ];

  const date = d.getDate();
  function getOrdinalSuffix(num) {
    // Convert input to integer (handles cases like 15.0)
    const integer = Math.floor(num);

    // Step 1: Check for 11, 12, 13 exceptions
    const mod100 = integer % 100;
    if (mod100 >= 11 && mod100 <= 13) {
      return "th";
    }

    // Step 2: Check last digit
    const mod10 = integer % 10;
    switch (mod10) {
      case 1:
        return "st";
      case 2:
        return "nd";
      case 3:
        return "rd";
      default:
        return "th";
    }
  }

  monthEl.innerText = months[d.getMonth()];
  yearEl.innerText = d.getFullYear();
  dateEl.innerText = `${days[d.getDay()]}, ${date}${getOrdinalSuffix(date)}`;
};

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
