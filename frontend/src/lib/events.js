export const PAGE_SIZE = 6
export const FILTERS = [['all', 'All events'], ['person', 'Person detected'], ['no_person', 'No person detected'], ['pending', 'Needs analysis'], ['error', 'Errors']]
export function formatDate(value, options = {}) {
  if (!value || !Number.isFinite(new Date(value).getTime())) return 'Not available'
  return new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric', ...options }).format(new Date(value))
}
export function formatClock(value) { return formatDate(value, { hour: '2-digit', minute: '2-digit', second: '2-digit' }) }
export function shortEvent(id) {
  const parts = String(id).split('-')
  return parts.length > 2 ? `Event ${parts.at(-1).padStart(3, '0')}` : 'Camera capture'
}
export function groupEvents(photos) {
  const groups = new Map()
  for (const photo of photos) {
    const id = photo.burst_id || `capture:${photo.id}`
    if (!groups.has(id)) groups.set(id, { id, burstId: photo.burst_id, photos: [], expected: photo.burst_id ? 5 : 1 })
    groups.get(id).photos.push(photo)
  }
  return [...groups.values()].map(event => {
    event.photos.sort((a, b) => (a.photo_number ?? 0) - (b.photo_number ?? 0))
    event.received = event.photos.length
    event.people = event.photos.filter(p => p.ml_state === 'person_detected').length
    event.errors = event.photos.filter(p => p.ml_state === 'error').length
    event.pending = event.photos.filter(p => !['person_detected', 'no_person_detected', 'error'].includes(p.ml_state)).length
    event.incomplete = event.received < event.expected
    event.state = event.people ? 'person' : event.errors ? 'error' : event.pending || event.incomplete ? 'pending' : 'no_person'
    event.firstAt = event.photos.reduce((v, p) => !v || p.received_at < v ? p.received_at : v, null)
    event.lastAt = event.photos.reduce((v, p) => !v || p.received_at > v ? p.received_at : v, null)
    event.preview = event.photos.find(p => p.ml_state === 'person_detected') || event.photos.at(-1)
    return event
  }).sort((a, b) => new Date(b.lastAt) - new Date(a.lastAt) || b.id.localeCompare(a.id))
}
export function matchesFilter(event, filter) {
  if (filter === 'all') return true
  if (filter === 'person') return event.people > 0
  if (filter === 'error') return event.errors > 0
  if (filter === 'pending') return event.pending > 0 || event.incomplete
  return event.state === 'no_person'
}
export function photoState(photo) { return ({ person_detected: 'person', no_person_detected: 'no_person', error: 'error' })[photo?.ml_state] || 'pending' }
export function modelName(path) { return path ? String(path).split(/[\\/]/).at(-1) : 'Not reported' }
