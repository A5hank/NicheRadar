"use strict";

const landingView = document.querySelector("#landing-view");
const reviewView = document.querySelector("#review-view");
const dashboardView = document.querySelector("#dashboard-view");
const nicheForm = document.querySelector("#niche-form");
const nicheInput = document.querySelector("#niche-input");
const formError = document.querySelector("#form-error");
const analyseButton = document.querySelector(
  "#analyse-button",
);
const analyseButtonLabel = document.querySelector(
  "#analyse-button-label",
);
const queryReviewForm = document.querySelector("#query-review-form");
const reviewNiche = document.querySelector("#review-niche");
const queryCount = document.querySelector("#query-count");
const reviewQueryList = document.querySelector("#review-query-list");
const newQueryInput = document.querySelector("#new-query-input");
const addQueryButton = document.querySelector("#add-query-button");
const reviewError = document.querySelector("#review-error");
const runAnalysisButton = document.querySelector("#run-analysis-button");
const reviewBackButton = document.querySelector("#review-back-button");
const dashboardTitle = document.querySelector("#dashboard-title");
const queryList = document.querySelector("#query-list");
const resultList = document.querySelector("#result-list");
const newAnalysisButton = document.querySelector("#new-analysis-button");
const mobileNewAnalysis = document.querySelector("#mobile-new-analysis");

const REQUIRED_QUERY_COUNT = 5;
let activeNiche = "";
let reviewedQueries = [];

const resultTemplates = [
  {
    rank: 1,
    title: (niche) => `Why ${niche} Is Everywhere Right Now`,
    channel: "Signal Studio",
    views: "8.4M",
    viewsPerDay: "1.2M",
    subscribers: "328K",
    multiplier: "25.6x",
    performance: "breakout",
  },
  {
    rank: 2,
    title: (niche) => `The ${niche} Detail Everyone Missed`,
    channel: "Frame by Frame",
    views: "12.7M",
    viewsPerDay: "980K",
    subscribers: "210K",
    multiplier: "60.5x",
    performance: "exceptional",
  },
  {
    rank: 3,
    title: (niche) => `${niche} Explained in 60 Seconds`,
    channel: "The Daily Cut",
    views: "3.1M",
    viewsPerDay: "560K",
    subscribers: "640K",
    multiplier: "4.8x",
    performance: "regular",
  },
  {
    rank: 4,
    title: (niche) => `The Most Surprising ${niche} Story`,
    channel: "Minute Stories",
    views: "2.7M",
    viewsPerDay: "430K",
    subscribers: "96K",
    multiplier: "28.1x",
    performance: "breakout",
  },
  {
    rank: 5,
    title: (niche) => `What Comes Next for ${niche}?`,
    channel: "Culture Loop",
    views: "6.2M",
    viewsPerDay: "390K",
    subscribers: "145K",
    multiplier: "42.7x",
    performance: "exceptional",
  },
];

async function requestExpandedQueries(niche) {
  const response = await fetch("/api/queries", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      niche,
    }),
  });

  const payload = await response
    .json()
    .catch(() => null);

  if (!response.ok) {
    const errorMessage =
      payload &&
      typeof payload.detail === "string"
        ? payload.detail
        : "Could not generate search queries right now.";

    throw new Error(errorMessage);
  }

  const responseIsValid =
    payload &&
    typeof payload.niche === "string" &&
    Array.isArray(payload.queries) &&
    payload.queries.every(
      (query) => typeof query === "string",
    );

  if (!responseIsValid) {
    throw new Error(
      "NicheRadar received an invalid query response.",
    );
  }

  return {
    niche: payload.niche,
    queries: payload.queries,
  };
}

function renderQueries(queries) {
  queryList.replaceChildren();

  for (const query of queries) {
    const chip = document.createElement("span");
    chip.textContent = query;
    queryList.append(chip);
  }
}

function queriesAreUnique(queries) {
  const normalizedQueries = queries.map((query) => query.trim().toLowerCase());

  return new Set(normalizedQueries).size === normalizedQueries.length;
}

function reviewValidationMessage() {
  if (reviewedQueries.length !== REQUIRED_QUERY_COUNT) {
    return `Choose exactly ${REQUIRED_QUERY_COUNT} queries before continuing.`;
  }

  if (reviewedQueries.some((query) => !query.trim())) {
    return "Every query needs some text.";
  }

  if (!queriesAreUnique(reviewedQueries)) {
    return "Each query must be different.";
  }

  return "";
}

function updateReviewControls() {
  const count = reviewedQueries.length;
  const validationMessage = reviewValidationMessage();

  queryCount.textContent = `${count} of ${REQUIRED_QUERY_COUNT} queries ready`;

  addQueryButton.disabled = count >= REQUIRED_QUERY_COUNT;
  newQueryInput.disabled = count >= REQUIRED_QUERY_COUNT;
  runAnalysisButton.disabled = Boolean(validationMessage);
  reviewError.textContent = validationMessage;
}

function renderQueryReview() {
  reviewQueryList.replaceChildren();

  reviewedQueries.forEach((query, index) => {
    const item = document.createElement("div");
    item.className = "review-query-item";

    const number = document.createElement("span");
    number.className = "query-number";
    number.textContent = index + 1;

    const input = document.createElement("input");
    input.type = "text";
    input.value = query;
    input.setAttribute("aria-label", `Search query ${index + 1}`);

    input.addEventListener("input", () => {
      reviewedQueries[index] = input.value;
      reviewError.textContent = "";
      updateReviewControls();
    });

    const removeButton = document.createElement("button");
    removeButton.className = "remove-query-button";
    removeButton.type = "button";
    removeButton.textContent = "Remove";
    removeButton.setAttribute("aria-label", `Remove query ${index + 1}`);

    removeButton.addEventListener("click", () => {
      reviewedQueries.splice(index, 1);
      reviewError.textContent = "";
      renderQueryReview();
      newQueryInput.focus();
    });

    item.append(number, input, removeButton);

    reviewQueryList.append(item);
  });

  updateReviewControls();
}

function addReviewedQuery() {
  const query = newQueryInput.value.trim();

  if (reviewedQueries.length >= REQUIRED_QUERY_COUNT) {
    reviewError.textContent = `You already have ${REQUIRED_QUERY_COUNT} queries.`;

    return;
  }

  if (!query) {
    reviewError.textContent = "Type a query before adding it.";
    newQueryInput.focus();
    return;
  }

  const queryAlreadyExists = reviewedQueries.some(
    (item) => item.trim().toLowerCase() === query.toLowerCase(),
  );

  if (queryAlreadyExists) {
    reviewError.textContent = "That query is already in the list.";

    newQueryInput.focus();
    return;
  }

  reviewedQueries.push(query);
  newQueryInput.value = "";
  reviewError.textContent = "";
  renderQueryReview();
}

function createTextCell(label, value, emphasis = false) {
  const elementName = emphasis ? "strong" : "span";
  const cell = document.createElement(elementName);

  cell.dataset.label = label;
  cell.textContent = value;

  return cell;
}

function createResultRow(template, niche) {
  const row = document.createElement("article");
  const title = template.title(niche);

  row.className = `result-row ${template.performance}-row`;

  row.setAttribute("role", "row");

  const rank = document.createElement("strong");
  rank.className = "result-rank";
  rank.textContent = template.rank;

  const video = document.createElement("div");
  video.className = "result-video";

  const thumbnail = document.createElement("span");
  thumbnail.className = "thumbnail";
  thumbnail.setAttribute("aria-hidden", "true");
  thumbnail.append(document.createElement("i"));

  const videoText = document.createElement("div");
  const heading = document.createElement("h3");
  const channel = document.createElement("p");

  heading.textContent = title;
  channel.textContent = template.channel;

  videoText.append(heading, channel);

  video.append(thumbnail, videoText);

  const link = document.createElement("a");
  link.href = "https://www.youtube.com/";
  link.target = "_blank";
  link.rel = "noreferrer";
  link.textContent = "Open ↗";

  link.setAttribute("aria-label", `Open ${title} on YouTube`);

  row.append(
    rank,
    video,
    createTextCell("Views", template.views),
    createTextCell("Views/day", template.viewsPerDay),
    createTextCell("Subscribers", template.subscribers),
    createTextCell("Multiplier", template.multiplier, true),
    link,
  );

  return row;
}

function renderResults(niche) {
  resultList.replaceChildren();

  for (const template of resultTemplates) {
    const resultRow = createResultRow(template, niche);

    resultList.append(resultRow);
  }
}

function showReview(
  niche,
  queries,
) {
  activeNiche = niche;
  reviewedQueries = [...queries];

  reviewNiche.textContent = niche;
  reviewError.textContent = "";
  newQueryInput.value = "";

  renderQueryReview();

  landingView.hidden = true;
  dashboardView.hidden = true;
  reviewView.hidden = false;

  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
}

function showDashboard(niche, queries) {
  dashboardTitle.textContent = niche;

  renderQueries(queries);
  renderResults(niche);

  landingView.hidden = true;
  reviewView.hidden = true;
  dashboardView.hidden = false;

  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
}

function showLanding({ clearInput = true } = {}) {
  dashboardView.hidden = true;
  reviewView.hidden = true;
  landingView.hidden = false;

  if (clearInput) {
    nicheInput.value = "";
  }

  formError.textContent = "";

  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });

  nicheInput.focus();
}

nicheForm.addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();

    const niche = nicheInput.value.trim();

    if (!niche) {
      formError.textContent =
        "Enter a niche to begin your analysis.";

      nicheInput.focus();
      return;
    }

    formError.textContent = "";
    analyseButton.disabled = true;
    analyseButtonLabel.textContent =
      "Finding angles...";

    try {
      const expansion =
        await requestExpandedQueries(niche);

      showReview(
        expansion.niche,
        expansion.queries,
      );
    } catch (error) {
      formError.textContent =
        error instanceof Error
          ? error.message
          : "Could not generate search queries right now.";
    } finally {
      analyseButton.disabled = false;
      analyseButtonLabel.textContent = "Analyse";
    }
  },
);

addQueryButton.addEventListener("click", addReviewedQuery);

newQueryInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    addReviewedQuery();
  }
});

queryReviewForm.addEventListener("submit", (event) => {
  event.preventDefault();

  reviewedQueries = reviewedQueries.map((query) => query.trim());

  const validationMessage = reviewValidationMessage();

  if (validationMessage) {
    reviewError.textContent = validationMessage;

    renderQueryReview();
    return;
  }

  reviewError.textContent = "";

  showDashboard(activeNiche, reviewedQueries);
});

reviewBackButton.addEventListener("click", () =>
  showLanding({ clearInput: false }),
);

newAnalysisButton.addEventListener("click", () => showLanding());

mobileNewAnalysis.addEventListener("click", () => showLanding());

for (const homeLink of document.querySelectorAll(".brand")) {
  homeLink.addEventListener("click", (event) => {
    event.preventDefault();
    showLanding();
  });
}
