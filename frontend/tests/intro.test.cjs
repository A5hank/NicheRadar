"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  colourProgressForElapsedTime,
  createSpriteFrames,
  highlightProgressForElapsedTime,
  shouldPlayBrandIntro,
  typedCharacterCount,
  wordmarkStyleForLandingTitle,
} = require("../intro.js");

test("plays the brand intro only for an unseen, motion-enabled session", () => {
  assert.equal(shouldPlayBrandIntro({}), true);
  assert.equal(shouldPlayBrandIntro({ seen: true }), false);
  assert.equal(shouldPlayBrandIntro({ reducedMotion: true }), false);
  assert.equal(
    shouldPlayBrandIntro({
      force: true,
      seen: true,
    }),
    true,
  );
});

test("splits Skiper's 15 by 7 sprite sheet into its 105 portrait frames", () => {
  const frames = createSpriteFrames(3_600, 2_268);

  assert.equal(frames.length, 105);
  assert.deepEqual(frames[0], { height: 324, width: 240, x: 0, y: 0 });
  assert.deepEqual(frames.at(-1), { height: 324, width: 240, x: 3_360, y: 1_944 });
});

test("matches the intro wordmark to the landing title's measured geometry", () => {
  assert.deepEqual(
    wordmarkStyleForLandingTitle(
      { left: 328, top: 286 },
      {
        fontSize: "96px",
        letterSpacing: "-7.2px",
        lineHeight: "88.32px",
      },
    ),
    {
      fontSize: "96px",
      left: "328px",
      letterSpacing: "-7.2px",
      lineHeight: "88.32px",
      top: "286px",
    },
  );
});

test("reveals typewriter copy from left to right without exposing future characters", () => {
  const text = "NicheRadar";

  assert.equal(typedCharacterCount(text, 0, 500), 0);
  assert.equal(typedCharacterCount(text, 250, 500), 5);
  assert.equal(typedCharacterCount(text, 500, 500), text.length);
});

test("keeps the crowd monochrome before the planned highlight and colour phases", () => {
  assert.equal(highlightProgressForElapsedTime(2_000), 0);
  assert.equal(highlightProgressForElapsedTime(2_700), 0.5);
  assert.equal(highlightProgressForElapsedTime(4_000), 1);

  assert.equal(colourProgressForElapsedTime(9_200), 0);
  assert.equal(colourProgressForElapsedTime(10_350), 0.5);
  assert.equal(colourProgressForElapsedTime(11_500), 1);
});
