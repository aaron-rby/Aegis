import assert from 'node:assert/strict'
import test from 'node:test'
import { parseHiddenEvents, hideEventIds, restoreEventIds, visibleEventCards } from './hiddenEvents.js'
test('invalid browser state is safe and duplicates are removed',()=>{assert.deepEqual(parseHiddenEvents('bad'),[]);assert.deepEqual(parseHiddenEvents('{"a":1}'),[]);assert.deepEqual(parseHiddenEvents('["a","a",null,3]'),['a'])})
test('hiding affects display only and undo restores only that batch',()=>{const events=[{id:'a',photos:[1]},{id:'b',photos:[2]},{id:'c',photos:[3]}];const original=structuredClone(events);const hidden=hideEventIds(['a'],['b','b']);assert.deepEqual(visibleEventCards(events,hidden).map(e=>e.id),['c']);assert.deepEqual(events,original);assert.deepEqual(restoreEventIds(hidden,['b']),['a'])})
test('new incoming events remain visible and all hidden can be restored',()=>{const hidden=hideEventIds([],['a','b']);assert.deepEqual(visibleEventCards([{id:'a'},{id:'b'},{id:'new'}],hidden),[{id:'new'}]);assert.equal(visibleEventCards([{id:'a'},{id:'b'}],[]).length,2)})
