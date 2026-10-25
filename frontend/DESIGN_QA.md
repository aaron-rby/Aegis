# Command-center design QA

The redesigned frontend uses the existing Python API and 3-second polling. Run `npm run build` from `frontend/`; the Python backend serves `dist/` at `http://localhost:5000/`. Fonts, icons, and background effects are local build assets, so the page makes no third-party runtime requests.

## Checked on 20 October 2026

- [x] Production build succeeds without warnings.
- [x] Gallery loads old photos, status, and ML results from the existing backend.
- [x] All five filters return the expected result counts or empty state; pagination advances through filtered results. Original and annotated images switch.
- [x] Full-image inspector opens, navigates to the next image, closes with Escape, traps Shift+Tab, and restores focus to the opening card.
- [x] Burst `582ABD7BB88C-5f2cc18f-22` shows **Received 3/5**, with frames **1 and 2 MISSING** and frames 3–5 present.
- [x] At 360, 768, 1280, and 1920 px there is no horizontal page overflow. The grid has 1, 2, 3, and 4 columns respectively.
- [x] With `prefers-reduced-motion: reduce`, orb and card animation durations are effectively zero.
- [x] Browser console has no errors. The page loads no third-party scripts, images, stylesheets, or fonts at runtime.

## Manual checks for the next live session

- [ ] In a second browser session, recheck each filter and Next/Previous pagination against a new live burst.
- [ ] Open a photo and recheck Original/Annotated, previous/next buttons, Left/Right arrows, Escape, backdrop click, Tab and Shift+Tab focus cycling, and focus returning to the card. The inspector's next button, Escape, Shift+Tab trap, and focus restoration were checked in this pass.
- [ ] Temporarily stop only the backend and confirm the red offline banner appears while existing cards stay visible and usable. Restart it and confirm the banner clears. Do this when no camera burst is uploading.
- [ ] Temporarily stop only the ML worker and wait over 30 seconds for the amber stale-heartbeat banner. Restart the worker and confirm it clears. Do this when no burst is uploading.
- [ ] With the laptop and ESP32-CAM on the same Wi-Fi, trigger one fresh burst. Watch for the 8-second NEW highlight, rising burst count, and final prediction badges without refreshing the page.
- [ ] In Chrome Performance, profile rapid scrolling and hover over a development fixture with 100+ cards. Normal gallery pagination currently renders 18 cards per page, so this stress test needs a separate fixture; do not change production pagination for it.
- [ ] Recheck 360, 768, 1280, and 1920 px with browser zoom and long filenames; verify no horizontal scroll. Repeat with reduced motion and increased contrast enabled.

The offline/stale checks were left for a controlled session because stopping live services could interrupt camera uploads. The live NEW highlight and 100-card stress profile were not independently verified in this design pass.
