"use strict";

/*
 * NicheRadar About page behaviour
 *
 * This file handles:
 * 1. Switching between the project and developer panels.
 * 2. Accessible keyboard navigation between the tabs.
 */

/* --------------------------------------------------------------------------
 * About-page tabs
 * -------------------------------------------------------------------------- */

/*
 * Collect both tab buttons and both corresponding content panels.
 *
 * Array.from converts the NodeList returned by querySelectorAll into a
 * normal JavaScript array.
 */
const aboutTabs = Array.from(
  document.querySelectorAll(".about-tab"),
);

const aboutPanels = Array.from(
  document.querySelectorAll(".about-panel"),
);

/*
 * Display the panel controlled by the selected tab.
 *
 * Each tab's aria-controls value contains the ID of its panel. This keeps
 * the relationship between the button and content explicit and accessible.
 */
function activateAboutTab(
  selectedTab,
  {
    moveFocus = false,
  } = {},
) {
  const targetPanelId =
    selectedTab.getAttribute("aria-controls");

  if (!targetPanelId) {
    return;
  }

  /*
   * Update every tab:
   *
   * - active controls the visual styling.
   * - aria-selected announces the selection to screen readers.
   * - tabindex allows only the active tab into the normal Tab-key order.
   */
  for (const tab of aboutTabs) {
    const isSelected =
      tab === selectedTab;

    tab.classList.toggle(
      "active",
      isSelected,
    );

    tab.setAttribute(
      "aria-selected",
      String(isSelected),
    );

    tab.tabIndex =
      isSelected
        ? 0
        : -1;
  }

  /*
   * The selected panel is shown. Every other panel receives hidden=true,
   * which causes the browser and the global [hidden] CSS rule to hide it.
   */
  for (const panel of aboutPanels) {
    panel.hidden =
      panel.id !== targetPanelId;
  }

  /*
   * Mouse clicks already leave focus on the clicked button.
   * Keyboard navigation explicitly asks us to move focus.
   */
  if (moveFocus) {
    selectedTab.focus();
  }
}

/*
 * Mouse and touch users activate tabs by clicking them.
 */
for (const tab of aboutTabs) {
  tab.addEventListener("click", () => {
    activateAboutTab(tab);
  });
}

/*
 * Keyboard behaviour follows the standard accessible tab pattern:
 *
 * ArrowRight: next tab
 * ArrowLeft: previous tab
 * Home: first tab
 * End: last tab
 */
for (const tab of aboutTabs) {
  tab.addEventListener(
    "keydown",
    (event) => {
      const currentIndex =
        aboutTabs.indexOf(tab);

      let nextIndex = currentIndex;

      if (event.key === "ArrowRight") {
        nextIndex =
          (currentIndex + 1) %
          aboutTabs.length;
      } else if (event.key === "ArrowLeft") {
        nextIndex =
          (
            currentIndex -
            1 +
            aboutTabs.length
          ) %
          aboutTabs.length;
      } else if (event.key === "Home") {
        nextIndex = 0;
      } else if (event.key === "End") {
        nextIndex =
          aboutTabs.length - 1;
      } else {
        /*
         * Leave unrelated keys alone so normal browser behaviour continues.
         */
        return;
      }

      event.preventDefault();

      activateAboutTab(
        aboutTabs[nextIndex],
        {
          moveFocus: true,
        },
      );
    },
  );
}

/*
 * Normalize the initial state from the HTML.
 *
 * Prefer the tab marked aria-selected="true". If that attribute is missing,
 * use the tab carrying the active class, then fall back to the first tab.
 */
const initialTab =
  aboutTabs.find(
    (tab) =>
      tab.getAttribute("aria-selected") ===
      "true",
  ) ??
  aboutTabs.find(
    (tab) =>
      tab.classList.contains("active"),
  ) ??
  aboutTabs[0];

if (initialTab) {
  activateAboutTab(initialTab);
}
