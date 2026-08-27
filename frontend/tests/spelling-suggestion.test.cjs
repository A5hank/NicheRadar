"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  chooseNicheAfterSpellingCheck,
  getUsableSpellingSuggestion,
} = require("../spelling-suggestion.js");

test("returns a high-confidence correction without replacing the original", () => {
  const suggestion = getUsableSpellingSuggestion("meincraft", {
    niche: "meincraft",
    suggestion: "Minecraft",
  });

  assert.equal(suggestion, "Minecraft");
  assert.equal(
    chooseNicheAfterSpellingCheck("meincraft", suggestion, "keep"),
    "meincraft",
  );
  assert.equal(
    chooseNicheAfterSpellingCheck("meincraft", suggestion, "use"),
    "Minecraft",
  );

  assert.equal(
    getUsableSpellingSuggestion("chadgpt", {
      niche: "chadgpt",
      suggestion: "ChatGPT",
    }),
    "ChatGPT",
  );

  assert.equal(
    getUsableSpellingSuggestion("twitch clups", {
      niche: "twitch clups",
      suggestion: "Twitch clips",
    }),
    "Twitch clips",
  );
});

test("returns no suggestion for a correct niche or capitalization-only change", () => {
  assert.equal(
    getUsableSpellingSuggestion("Minecraft", {
      niche: "Minecraft",
      suggestion: null,
    }),
    null,
  );

  assert.equal(
    getUsableSpellingSuggestion("minecraft", {
      niche: "minecraft",
      suggestion: "Minecraft",
    }),
    null,
  );
});

test("leaves uncommon niches alone when the check returns no suggestion", () => {
  assert.equal(
    getUsableSpellingSuggestion("AetherFlux", {
      niche: "AetherFlux",
      suggestion: null,
    }),
    null,
  );
});

test("treats service failures and invalid responses as no suggestion", () => {
  assert.equal(getUsableSpellingSuggestion("meincraft", null), null);

  assert.equal(
    getUsableSpellingSuggestion("meincraft", {
      niche: "another niche",
      suggestion: "Minecraft",
    }),
    null,
  );

  assert.equal(
    getUsableSpellingSuggestion("meincraft", {
      niche: "meincraft",
      suggestion: 42,
    }),
    null,
  );
});
