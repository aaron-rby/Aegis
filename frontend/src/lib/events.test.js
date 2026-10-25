import test from 'node:test'
import assert from 'node:assert/strict'
import { groupEvents, matchesFilter } from './events.js'
const photo = (n, state = 'no_person_detected', burst = 'test-burst-1') => ({ id: `${burst}-${n}`, burst_id: burst, photo_number: n, ml_state: state, received_at: `2026-10-24T12:00:0${n}Z` })
test('five captures become one complete event in frame order', () => {
  const [event] = groupEvents([5, 2, 3, 1, 4].map(n => photo(n)))
  assert.equal(event.received, 5); assert.equal(event.state, 'no_person')
  assert.deepEqual(event.photos.map(p => p.photo_number), [1, 2, 3, 4, 5])
})
test('a missing upload cannot become a complete no-person event', () => {
  const [event] = groupEvents([1, 3, 5].map(n => photo(n)))
  assert.equal(event.incomplete, true); assert.equal(matchesFilter(event, 'no_person'), false)
  assert.equal(matchesFilter(event, 'pending'), true)
})
test('person evidence is retained alongside processing errors', () => {
  const [event] = groupEvents([photo(1, 'person_detected'), photo(2, 'error')])
  assert.equal(event.state, 'person'); assert.equal(event.preview.id, 'test-burst-1-1')
  assert.equal(matchesFilter(event, 'error'), true); assert.equal(matchesFilter(event, 'person'), true)
})
test('legacy unqueued frames remain awaiting analysis', () => {
  const [event] = groupEvents([1, 2, 3, 4, 5].map(n => photo(n, 'legacy_unprocessed')))
  assert.equal(event.pending, 5); assert.equal(event.state, 'pending')
})
test('ungrouped captures are not presented as five-photo bursts', () => {
  const [event] = groupEvents([photo(1, 'no_person_detected', null)])
  assert.equal(event.expected, 1); assert.equal(event.received, 1); assert.equal(event.incomplete, false)
})
test('events are sorted by their latest received frame', () => {
  const events = groupEvents([photo(1), photo(5, 'no_person_detected', 'test-burst-2')])
  assert.equal(events[0].id, 'test-burst-2')
})
