const PANEL_URLS = {
  account: "/panels/account/",
  journal: "/panels/journal/",
  sticker: "/panels/sticker",
};

const navbtns = document.querySelectorAll(".navbtn");

navbtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    const panelName = btn.dataset.panel;
    const url = btn.dataset.url ?? PANEL_URLS[panelName];

    if (!url) {
      console.warn(`No URL configured for panel: "${panelName}"`);
      return;
    }

    panelManager.open(panelName, url);
  });
});
