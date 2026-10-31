export const HIDDEN_EVENTS_KEY = 'aegis.hidden-events.v1'
export function parseHiddenEvents(raw) {
  try { const value = JSON.parse(raw); return Array.isArray(value) ? [...new Set(value.filter(id => typeof id === 'string' && id.length > 0 && id.length < 300))] : [] } catch { return [] }
}
export function hideEventIds(current, ids) { return [...new Set([...current, ...ids])] }
export function restoreEventIds(current, ids) { const restored = new Set(ids); return current.filter(id => !restored.has(id)) }
export function visibleEventCards(events, hidden) { const ids = new Set(hidden); return events.filter(event => !ids.has(event.id)) }
