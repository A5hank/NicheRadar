"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  buildAnalysisSummaryRequest,
  getUsableAnalysisSummary,
} = require("../analysis-summary.js");

const summaryContext = {
  query_count: 5,
  videos_considered: 100,
  videos_returned: 50,
  videos_with_subscriber_data: 45,
  breakout_count: 4,
  breakout_channel_count: 3,
  exceptional_count: 2,
  unique_channel_count: 28,
  virality_score: 66,
  confidence_score: 88,
  median_views_per_day: 42_000,
};

test("builds a summary request from server-provided deterministic facts", () => {
  assert.deepEqual(
    buildAnalysisSummaryRequest({
      niche: " Minecraft ",
      summary_context: summaryContext,
    }),
    {
      niche: "Minecraft",
      summary_context: summaryContext,
    },
  );
});

test("accepts a valid AI summary and deterministic creator signal", () => {
  const summary = getUsableAnalysisSummary("Minecraft", {
    niche: "minecraft",
    observations: [
      "Current velocity shows active recent interest.",
      "The sample is broad enough to support the confidence score.",
      "Breakout activity is spread across multiple channels.",
    ],
    new_creator_signal: {
      label: "favourable",
      rationale: "Recent breakouts span multiple creators.",
    },
  });

  assert.deepEqual(summary, {
    observations: [
      "Current velocity shows active recent interest.",
      "The sample is broad enough to support the confidence score.",
      "Breakout activity is spread across multiple channels.",
    ],
    newCreatorSignal: {
      label: "favourable",
      labelText: "Favourable",
      rationale: "Recent breakouts span multiple creators.",
    },
  });
});

test("keeps a valid deterministic signal when AI observations are unavailable", () => {
  const summary = getUsableAnalysisSummary("Minecraft", {
    niche: "Minecraft",
    observations: null,
    new_creator_signal: {
      label: "insufficient_evidence",
      rationale: "Too few approved queries were used for a useful assessment.",
    },
  });

  assert.equal(summary.observations, null);
  assert.equal(summary.newCreatorSignal.labelText, "Insufficient evidence");
});

test("rejects malformed or stale summary responses", () => {
  assert.equal(
    getUsableAnalysisSummary("Minecraft", {
      niche: "Fortnite",
      observations: [],
      new_creator_signal: {
        label: "mixed",
        rationale: "A mixed signal.",
      },
    }),
    null,
  );

  assert.equal(
    getUsableAnalysisSummary("Minecraft", {
      niche: "Minecraft",
      observations: ["Only one."],
      new_creator_signal: {
        label: "unknown",
        rationale: "A mixed signal.",
      },
    }),
    null,
  );
});
