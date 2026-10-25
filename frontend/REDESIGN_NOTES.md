# Sentinel AI frontend redesign — 24 October 2026

Implemented Overview, Events, Event Details, System and read-only Configuration.
The application uses a navy navigation shell, light workspace and dark evidence
viewer. It continues to use the existing Python API and local image routes.

## Behavior

- Photos are grouped by burst ID. Ungrouped legacy photos are individual captures.
- Six event cards per page, one representative image per event.
- Person-positive frames take preview priority; otherwise the latest frame is used.
- Person and error filters can overlap. Needs analysis includes pending results
  and missing uploads. No person includes only complete, fully negative events.
- Original/annotated switching, five frame slots, missing placeholders, keyboard
  navigation, expanded inspection and technical details are available in Event Details.
- Background updates retain the archive and do not reorder its cards. A user
  action admits newly received events. Polling pauses while the document is hidden.
- Configuration is informational; no backend settings controls were added.
- Worker health is separate from receiver availability and camera upload history.

## Verification

- Production build passed with Vite.
- Six domain tests passed: grouping, ordering, incomplete events, mixed positive/error
  events, unqueued legacy frames and individual ungrouped captures.
- Browser verification used the real local API: 565 photos, 122 events, 34 events
  with person-positive frames at the time of the check.
- Checked six-card rendering and three columns at 1440/1911 desktop widths.
- Checked one-column events, navigation drawer, System and Configuration at 390 px.
  No horizontal document overflow was observed at the checked sizes.
- Checked person filtering, Original/Annotated, frame navigation, expanded view
  and Escape. Returning to Events preserves the active filter.
- Browser console showed no errors or warnings during the checked flows.
- Physical capture, sensor operation and worker inference were not rerun.
- Disconnection/reconnection and reduced-motion behavior are implemented but were
  not exercised by interrupting live services during browser checks.

The archive reader loads paginated photo metadata to derive event-wide filtering
without backend changes. This is suitable for the present archive; significantly
larger archives should move event aggregation/filtering into a backend endpoint.

Previous source is preserved in `../backups/frontend-before-redesign-20261024-233205/`.
Legacy component/style files remain in the source but are no longer imported.
The production bundle is in `dist/`. Start the normal application with
`../START_ALL.bat`, then open http://localhost:5000/.
