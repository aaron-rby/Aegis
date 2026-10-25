import React, { useEffect, useRef, useState } from 'react'
import { ArrowLeft, ArrowRight, Check, ChevronDown, ChevronLeft, ChevronRight, Copy, Expand, ImageOff, Layers3, Minimize, ScanLine } from 'lucide-react'
import { Badge, CameraImage, InfoRow } from '../components/MonitorUI.jsx'
import { formatClock, photoState, shortEvent } from '../lib/events.js'

export default function EventDetails({ event, onBack }) {
  const [selected, setSelected] = useState(event.preview.photo_number || 1)
  const [annotated, setAnnotated] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)
  const [copyFailed, setCopyFailed] = useState(false)
  const copiedTimer = useRef(null)
  const viewerRef = useRef(null)
  const expandButton = useRef(null)
  useEffect(() => {
    setSelected(event.preview.photo_number || 1); setAnnotated(false); setExpanded(false)
  }, [event.id])
  useEffect(() => () => clearTimeout(copiedTimer.current), [])
  const photo = event.burstId ? event.photos.find(item => item.photo_number === selected) : event.photos[0]
  function move(direction) { setSelected(value => Math.max(1, Math.min(event.expected, value + direction))); setAnnotated(false) }
  useEffect(() => {
    function onKey(e) {
      if (e.target.closest('input,textarea,select')) return
      if (e.key === 'ArrowLeft') { e.preventDefault(); move(-1) }
      if (e.key === 'ArrowRight') { e.preventDefault(); move(1) }
      if (e.key === 'Escape' && expanded) { setExpanded(false); expandButton.current?.focus() }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [event.expected, expanded])
  useEffect(() => {
    if (!expanded) return
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    viewerRef.current?.querySelector('button')?.focus()
    function trap(e) {
      if (e.key !== 'Tab') return
      const controls = [...viewerRef.current.querySelectorAll('button:not(:disabled)')].filter(el => el.getClientRects().length)
      const first = controls[0], last = controls.at(-1)
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
    }
    window.addEventListener('keydown', trap)
    return () => { document.body.style.overflow = overflow; window.removeEventListener('keydown', trap) }
  }, [expanded])
  async function copyId() {
    try { await navigator.clipboard.writeText(event.id); setCopied(true); setCopyFailed(false); copiedTimer.current = setTimeout(() => setCopied(false), 2000) }
    catch { setCopyFailed(true) }
  }
  const confidence = photo?.ml_state === 'person_detected' && typeof photo?.prediction?.confidence === 'number' ? photo.prediction.confidence : null
  return <>
    <div className="detail-heading"><button className="text-button" onClick={onBack}><ArrowLeft size={16} />Back to events</button><span><Layers3 size={14} />{shortEvent(event.id)}<span className="detail-heading-divider">/</span>{event.received} of {event.expected} frames received</span></div>
    <div className="detail-layout"><section ref={viewerRef} className={`capture-viewer ${expanded ? 'capture-viewer--expanded' : ''}`} {...(expanded ? { role: 'dialog', 'aria-modal': true, 'aria-label': 'Expanded camera frame' } : {})}>
      <div className="viewer-toolbar"><div><span className="viewer-dot" />CAPTURE INSPECTOR</div><div className="viewer-controls"><span>Frame {selected} / {event.expected}</span><button ref={expandButton} className="icon-button" aria-label={expanded ? 'Exit expanded image' : 'Expand image'} onClick={() => setExpanded(value => !value)}>{expanded ? <Minimize size={17} /> : <Expand size={17} />}</button></div></div>
      <div className="viewer-image-stage">{photo ? <CameraImage photo={photo} annotated={annotated} eager /> : <div className="missing-frame"><ImageOff size={34} /><h3>Frame {selected} was not received.</h3><p>This slot stays visible so incomplete bursts are easy to spot.</p></div>}<span className="viewer-image-label">{annotated && photo?.annotated_url ? 'ML ANNOTATION' : 'ORIGINAL FRAME'}</span></div>
      <div className="viewer-bottom"><button className="icon-button" disabled={selected === 1} onClick={() => move(-1)} aria-label="Previous frame"><ChevronLeft size={19} /></button><div className="image-toggle" role="group" aria-label="Image version"><button aria-pressed={!annotated} className={!annotated ? 'selected' : ''} onClick={() => setAnnotated(false)}>Original</button><button aria-pressed={annotated} disabled={!photo?.annotated_url} className={annotated ? 'selected' : ''} onClick={() => setAnnotated(true)}>Annotated</button></div><button className="icon-button" disabled={selected === event.expected} onClick={() => move(1)} aria-label="Next frame"><ChevronRight size={19} /></button></div>
      <div className="frame-strip" role="group" aria-label="Event frames">{Array.from({ length: event.expected }, (_, i) => {
        const number = i + 1, item = event.burstId ? event.photos.find(p => p.photo_number === number) : event.photos[0]
        const state = item?.ml_state === 'processing' ? 'processing' : photoState(item)
        return <button key={number} className={`frame-thumb ${selected === number ? 'selected' : ''} ${!item ? 'frame-thumb--missing' : ''}`} aria-pressed={selected === number} onClick={() => setSelected(number)}><span className="frame-thumb-image">{item ? <CameraImage photo={item} /> : <ImageOff size={19} />}</span><span className="frame-caption"><span className="frame-number">Frame {String(number).padStart(2, '0')}</span><Badge state={state}>{!item ? 'Missing frame' : undefined}</Badge></span></button>
      })}</div><p className="viewer-hint">Use ← and → to move between frames. {expanded ? 'Escape exits the expanded view.' : 'Original frames preserve the complete camera evidence.'}</p>
    </section>
    <aside className="capture-info"><div className="capture-info-heading"><span className="eyebrow">FRAME {String(selected).padStart(2, '0')} / ANALYSIS</span><ScanLine size={19} /></div><h2>{photo ? 'The frame, explained.' : 'An incomplete moment.'}</h2><Badge state={photo ? photoState(photo) : 'pending'}>{!photo ? 'Missing frame' : photo.ml_state === 'processing' ? 'Processing' : undefined}</Badge>
      <dl><InfoRow label="Captured">{formatClock(photo?.received_at || event.firstAt)}</InfoRow><InfoRow label="Event frames">{event.received} / {event.expected} received</InfoRow><InfoRow label="Processing">{!photo ? 'Not received' : photo.ml_state === 'legacy_unprocessed' ? 'Legacy · not queued' : photo.ml_state.replaceAll('_', ' ')}</InfoRow><InfoRow label="Image version">{annotated && photo?.annotated_url ? 'Annotated' : 'Original'}</InfoRow></dl>
      {confidence !== null && <div className="confidence-block"><div><span>Detection confidence</span><strong>{(confidence * 100).toFixed(1)}%</strong></div><div className="confidence-track"><span style={{ width: `${Math.max(0, Math.min(100, confidence * 100))}%` }} /></div><p>Score for this detection, not overall model accuracy.</p></div>}
      {photo?.error && <div className="frame-error" role="status"><strong>Processing error</strong><p>{photo.error}</p></div>}
      <div className="evidence-note"><ScanLine size={17} /><p>Person detection does not establish identity or authorization. Review the original image alongside the result.</p></div>
      <details className="technical-details"><summary>Technical details <ChevronDown size={15} /></summary><dl><InfoRow label="Event ID"><span className="copyable"><code>{event.id}</code><button className="icon-button" onClick={copyId} aria-label="Copy event ID">{copied ? <Check size={13} /> : <Copy size={13} />}</button></span></InfoRow>{copyFailed && <p role="status">Copy unavailable. Select the ID to copy it manually.</p>}<InfoRow label="Filename"><code>{photo?.name || 'Not received'}</code></InfoRow><InfoRow label="Photo ID"><code>{photo?.id || 'Not received'}</code></InfoRow><InfoRow label="Authorization">Not evaluated</InfoRow></dl></details>
    </aside></div>
  </>
}
