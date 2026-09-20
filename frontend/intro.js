"use strict";

/*
 * Crowd animation adapted from Skiper UI's Canvas Crowd component:
 * https://skiper-ui.com/v1/skiper39
 * Illustration sprites by Open Peeps: https://www.openpeeps.com/
 * Skiper UI's free-use terms require attribution.
 */
(function exposeBrandIntro(globalScope) {
  const FRAME_COLUMNS = 15;
  const FRAME_ROWS = 7;
  const INTRO_DURATION_MS = 8_000;
  const INTRO_SEEN_STORAGE_KEY = "nicheradar-brand-intro-seen";
  const SPRITE_SOURCE = "/assets/skiper-all-peeps.png";

  function clamp(value, minimum, maximum) {
    return Math.min(Math.max(value, minimum), maximum);
  }

  function shouldPlayBrandIntro({ force = false, reducedMotion = false, seen = false }) {
    return !reducedMotion && (force || !seen);
  }

  function colourProgressForElapsedTime(elapsedTime) {
    return clamp((elapsedTime - 9_300) / 2_100, 0, 1);
  }

  function highlightProgressForElapsedTime(elapsedTime) {
    return clamp((elapsedTime - 2_100) / 1_200, 0, 1);
  }

  function typedCharacterCount(text, elapsedTime, duration) {
    if (elapsedTime <= 0) {
      return 0;
    }

    return Math.min(text.length, Math.ceil((text.length * elapsedTime) / duration));
  }

  function createSpriteFrames(imageWidth, imageHeight) {
    const frameWidth = imageWidth / FRAME_COLUMNS;
    const frameHeight = imageHeight / FRAME_ROWS;

    return Array.from({ length: FRAME_COLUMNS * FRAME_ROWS }, (_, index) => ({
      height: frameHeight,
      width: frameWidth,
      x: (index % FRAME_COLUMNS) * frameWidth,
      y: Math.floor(index / FRAME_COLUMNS) * frameHeight,
    }));
  }

  function wordmarkStyleForLandingTitle(rect, computedStyle) {
    return {
      fontSize: computedStyle.fontSize,
      left: `${rect.left}px`,
      letterSpacing: computedStyle.letterSpacing,
      lineHeight: computedStyle.lineHeight,
      top: `${rect.top}px`,
    };
  }

  function startBrandIntro() {
    if (typeof document === "undefined" || typeof window === "undefined") {
      return;
    }

    const intro = document.querySelector("#brand-intro");
    const canvas = document.querySelector("#brand-intro-canvas");
    const skipButton = document.querySelector("#skip-brand-intro");
    const nicheInput = document.querySelector("#niche-input");
    const landingTitle = document.querySelector("#landing-title");
    const wordmark = document.querySelector(".brand-intro-wordmark");
    const introLines = Array.from(document.querySelectorAll(".brand-intro-line"));

    if (!intro || !canvas || !skipButton) {
      return;
    }

    const parameters = new URLSearchParams(window.location.search);
    const forceIntro = parameters.get("intro") === "1";
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let introSeen = false;

    try {
      introSeen = window.sessionStorage.getItem(INTRO_SEEN_STORAGE_KEY) === "true";
    } catch {
      /* Private browsing can disable session storage; the intro can still run. */
    }

    if (!shouldPlayBrandIntro({ force: forceIntro, reducedMotion, seen: introSeen })) {
      document.documentElement.classList.remove("brand-intro-pending");
      return;
    }

    const context = canvas.getContext("2d");

    if (!context) {
      return;
    }

    const sprite = new Image();
    const crowd = [];
    let animationFrameId = 0;
    let endTimerId = 0;
    let startTime = 0;
    let completed = false;
    let highlightedPeep = null;
    let stageWidth = 0;
    let stageHeight = 0;
    const typingFrameIds = new Set();
    const typingTimerIds = new Set();

    function typeLine(line, duration) {
      const text = line.dataset.introText || "";
      const startedAt = window.performance.now();

      line.textContent = "";

      function renderTypedText(currentTime) {
        if (completed) {
          return;
        }

        const characterCount = typedCharacterCount(text, currentTime - startedAt, duration);
        line.textContent = text.slice(0, characterCount);

        if (characterCount < text.length) {
          const frameId = window.requestAnimationFrame(renderTypedText);
          typingFrameIds.add(frameId);
        }
      }

      const frameId = window.requestAnimationFrame(renderTypedText);
      typingFrameIds.add(frameId);
    }

    function alignWordmarkToLandingTitle() {
      if (!landingTitle || !wordmark) {
        return;
      }

      const style = wordmarkStyleForLandingTitle(
        landingTitle.getBoundingClientRect(),
        window.getComputedStyle(landingTitle),
      );

      Object.assign(wordmark.style, style);
      wordmark.style.translate = "0 0";
    }

    function resetPeep(peep, elapsedTime) {
      const direction = Math.random() > 0.5 ? 1 : -1;
      const offsetY = 100 - 250 * Math.pow(Math.random(), 2);
      const startX = direction === 1 ? -peep.frame.width : stageWidth + peep.frame.width;
      const endX = direction === 1 ? stageWidth : -peep.frame.width;

      peep.direction = direction;
      peep.endX = endX;
      peep.speed = 0.5 + Math.random();
      peep.startTime = elapsedTime;
      peep.startX = startX;
      peep.y = stageHeight - peep.frame.height + offsetY;
      peep.anchorY = peep.y;
      peep.bobOffset = Math.random() * Math.PI * 2;
      peep.x = startX;
    }

    function buildCrowd() {
      crowd.length = 0;
      const frames = createSpriteFrames(sprite.naturalWidth, sprite.naturalHeight);

      frames.forEach((frame) => {
        const peep = { frame };
        resetPeep(peep, 0);
        peep.startTime -= Math.random() * 10_000;
        crowd.push(peep);
      });

      crowd.sort((first, second) => first.anchorY - second.anchorY);
      highlightedPeep = crowd[Math.floor(crowd.length * 0.52)] || null;
    }

    function renderPeep(peep, elapsedTime, highlighted) {
      const duration = 10_000 / peep.speed;
      const progress = (elapsedTime - peep.startTime) / duration;

      if (progress >= 1) {
        resetPeep(peep, elapsedTime);
        return;
      }

      const bob = Math.sin((elapsedTime / 250) * peep.speed + peep.bobOffset) * 5;
      peep.x = peep.startX + (peep.endX - peep.startX) * progress;
      peep.y = peep.anchorY + bob;

      context.save();
      context.translate(peep.x, peep.y);
      context.scale(peep.direction, 1);

      if (highlighted) {
        context.filter = `drop-shadow(0 0 18px rgba(91, 166, 190, ${0.9 * highlightProgressForElapsedTime(elapsedTime)}))`;
      }

      context.drawImage(
        sprite,
        peep.frame.x,
        peep.frame.y,
        peep.frame.width,
        peep.frame.height,
        0,
        0,
        peep.frame.width,
        peep.frame.height,
      );

      context.restore();
    }

    function render(currentTime) {
      if (completed) {
        return;
      }

      const elapsedTime = currentTime - startTime;
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);

      context.clearRect(0, 0, canvas.width, canvas.height);
      context.save();
      context.scale(pixelRatio, pixelRatio);

      crowd.forEach((peep) => {
        if (peep !== highlightedPeep) {
          renderPeep(peep, elapsedTime, false);
        }
      });

      if (highlightedPeep) {
        renderPeep(highlightedPeep, elapsedTime, elapsedTime >= 2_100 && elapsedTime < 7_900);
      }

      context.restore();
      animationFrameId = window.requestAnimationFrame(render);
    }

    function resizeCanvas() {
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
      stageWidth = canvas.clientWidth;
      stageHeight = canvas.clientHeight;
      canvas.width = Math.round(stageWidth * pixelRatio);
      canvas.height = Math.round(stageHeight * pixelRatio);

      if (sprite.complete && sprite.naturalWidth) {
        buildCrowd();
      }

      alignWordmarkToLandingTitle();
    }

    function clearForcedIntroParameter() {
      if (!forceIntro) {
        return;
      }

      parameters.delete("intro");
      const query = parameters.toString();
      const nextUrl = `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`;
      window.history.replaceState({}, "", nextUrl);
    }

    function finishIntro({ immediately = false } = {}) {
      if (completed) {
        return;
      }

      completed = true;
      window.cancelAnimationFrame(animationFrameId);
      typingFrameIds.forEach((frameId) => window.cancelAnimationFrame(frameId));
      typingTimerIds.forEach((timerId) => window.clearTimeout(timerId));
      window.clearTimeout(endTimerId);
      window.removeEventListener("resize", resizeCanvas);
      document.removeEventListener("keydown", handleKeydown);
      intro.classList.add("is-exiting");
      document.body.classList.remove("intro-active");
      clearForcedIntroParameter();

      try {
        window.sessionStorage.setItem(INTRO_SEEN_STORAGE_KEY, "true");
      } catch {
        /* The main application must remain usable when storage is unavailable. */
      }

      window.setTimeout(
        () => {
          intro.hidden = true;
          nicheInput?.focus();
        },
        immediately ? 0 : 400,
      );
    }

    function handleKeydown(event) {
      if (event.key === "Escape") {
        finishIntro();
      }
    }

    function beginAnimation() {
      resizeCanvas();
      startTime = window.performance.now();
      animationFrameId = window.requestAnimationFrame(render);
    }

    intro.hidden = false;
    intro.classList.add("is-playing");
    document.body.classList.add("intro-active");
    document.documentElement.classList.remove("brand-intro-pending");
    alignWordmarkToLandingTitle();
    window.addEventListener("resize", resizeCanvas);
    document.addEventListener("keydown", handleKeydown);
    skipButton.addEventListener("click", () => finishIntro());
    skipButton.focus();
    sprite.addEventListener("load", beginAnimation, { once: true });
    sprite.src = SPRITE_SOURCE;
    const firstLine = introLines.find((line) => line.classList.contains("brand-intro-line-first"));
    const secondLine = introLines.find((line) => line.classList.contains("brand-intro-line-second"));

    if (firstLine) {
      typingTimerIds.add(window.setTimeout(() => typeLine(firstLine, 760), 2_800));
    }

    if (secondLine) {
      typingTimerIds.add(window.setTimeout(() => typeLine(secondLine, 850), 4_900));
    }

    endTimerId = window.setTimeout(() => finishIntro(), INTRO_DURATION_MS);
  }

  const brandIntro = Object.freeze({
    colourProgressForElapsedTime,
    createSpriteFrames,
    highlightProgressForElapsedTime,
    shouldPlayBrandIntro,
    startBrandIntro,
    typedCharacterCount,
    wordmarkStyleForLandingTitle,
  });

  if (typeof module !== "undefined" && module.exports) {
    module.exports = brandIntro;
  }

  if (globalScope) {
    globalScope.NicheRadarBrandIntro = brandIntro;
  }

  startBrandIntro();
})(typeof globalThis === "undefined" ? undefined : globalThis);
