"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  DEFAULT_RANKING_MODE,
  RANKING_MODES,
  sortResultVideos,
} = require("../result-ranking.js");

function resultIdsAndRanks(results) {
  return results.map((video) => [video.video_id, video.rank]);
}

const sampleVideos = [
  {
    video_id: "velocity-leader",
    rank: 1,
    views: 150_000,
    views_per_day: 125_000,
    subscriber_multiplier: 50,
  },
  {
    video_id: "total-views-leader",
    rank: 2,
    views: 950_000,
    views_per_day: 20_000,
    subscriber_multiplier: 9.5,
  },
  {
    video_id: "zero-multiplier",
    rank: 3,
    views: 400_000,
    views_per_day: 10_000,
    subscriber_multiplier: 0,
  },
  {
    video_id: "unknown-multiplier",
    rank: 4,
    views: 300_000,
    views_per_day: 8_000,
    subscriber_multiplier: null,
  },
];

test("uses views per day by default and renumbers displayed ranks", () => {
  assert.equal(DEFAULT_RANKING_MODE, RANKING_MODES.VIEWS_PER_DAY);

  assert.deepEqual(
    resultIdsAndRanks(sortResultVideos(sampleVideos)),
    [
      ["velocity-leader", 1],
      ["total-views-leader", 2],
      ["zero-multiplier", 3],
      ["unknown-multiplier", 4],
    ],
  );
});

test("sorts result rows by total views and renumbers them", () => {
  assert.deepEqual(
    resultIdsAndRanks(sortResultVideos(sampleVideos, RANKING_MODES.VIEWS)),
    [
      ["total-views-leader", 1],
      ["zero-multiplier", 2],
      ["unknown-multiplier", 3],
      ["velocity-leader", 4],
    ],
  );
});

test("sorts available multipliers first while retaining zero as a real value", () => {
  const videos = [
    ...sampleVideos,
    {
      video_id: "also-unknown",
      rank: 5,
      views: 20_000,
      views_per_day: 2_000,
      subscriber_multiplier: undefined,
    },
    {
      video_id: "invalid-multiplier",
      rank: 6,
      views: 10_000,
      views_per_day: 1_000,
      subscriber_multiplier: Number.NaN,
    },
  ];

  assert.deepEqual(
    resultIdsAndRanks(
      sortResultVideos(videos, RANKING_MODES.SUBSCRIBER_MULTIPLIER),
    ),
    [
      ["velocity-leader", 1],
      ["total-views-leader", 2],
      ["zero-multiplier", 3],
      ["unknown-multiplier", 4],
      ["also-unknown", 5],
      ["invalid-multiplier", 6],
    ],
  );
});

test("preserves source order for equal values without mutating API data", () => {
  const tiedVideos = [
    {
      video_id: "first-tie",
      rank: 7,
      views: 100,
      views_per_day: 10,
      subscriber_multiplier: 1,
    },
    {
      video_id: "second-tie",
      rank: 8,
      views: 100,
      views_per_day: 10,
      subscriber_multiplier: 1,
    },
  ];
  const originalVideos = structuredClone(tiedVideos);

  assert.deepEqual(
    resultIdsAndRanks(sortResultVideos(tiedVideos, RANKING_MODES.VIEWS)),
    [
      ["first-tie", 1],
      ["second-tie", 2],
    ],
  );
  assert.deepEqual(tiedVideos, originalVideos);
});
