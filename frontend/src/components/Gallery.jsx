import React, { useEffect, useRef, useState } from 'react'
import { AlertTriangle, ArrowLeft, ArrowRight, Check, ChevronLeft, ChevronRight, Copy, ImageOff, Layers3, Maximize2, Minimize2, X } from 'lucide-react'
import { useRelativeTime } from '../hooks/useRelativeTime.js'
import { usePointerGlow } from '../hooks/usePointerGlow.js'
import { SegmentedControl } from './Dashboard.jsx'

export function formatTime(value) {
  if (!value) return 'Unknown time'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat(undefined, {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit',
  }).format(parsed)
}

export function photoLabel(photo) {
  if (photo.ml_state === 'person_detected') return 'Person detected'
  if (photo.ml_state === 'no_person_detected') return 'No person detected'
  if (photo.ml_state === 'error') return 'Analysis error'
  return photo.ml_state === 'processing' ? 'Processing' : 'Pending analysis'
}

function photoTone(photo) {
  if (photo.ml_state === 'person_detected') return 'person'
  if (photo.ml_state === 'no_person_detected') return 'clear'
  if (photo.ml_state === 'error') return 'error'
  return 'pending'
}

export function StatusBadge({ photo }) {
  const confidence = photo.ml_state === 'person_detected' && typeof photo.prediction?.confidence === 'number'
    ? ` · ${Math.round(photo.prediction.confidence * 100)}%` : ''
  return <span className={`status-badge badge-${photoTone(photo)}`}><span className="badge-dot" />{photoLabel(photo)}{confidence}</span>
}

export function FeaturedCapture({ photo, annotated, onOpen, title = 'Latest camera frame' }) {
  const [broken, setBroken] = useState(false)
  const source = annotated && photo.annotated_url ? photo.annotated_url : photo.image_url
  const confidence = photo.ml_state === 'person_detected' && typeof photo.prediction?.confidence === 'number'
    ? `${Math.round(photo.prediction.confidence * 100)}%` : null
  useEffect(() => setBroken(false), [source])

  return <section className="featured-capture glass" aria-label={title}>
    <div className="featured-image">
      {!broken ? <img src={source} alt={`Camera capture ${photo.name}, ${formatTime(photo.received_at)}`} onError={() => setBroken(true)} /> : <span className="image-fallback"><ImageOff size={30} />Image unavailable</span>}
      <span className="featured-image-label">{annotated && photo.annotated_url ? 'ML annotation' : 'Original camera frame'}</span>
    </div>
    <div className="featured-content">
      <span className="eyebrow">CAPTURE FOCUS</span>
      <h2>{title}</h2>
      <StatusBadge photo={photo} />
      <p className="featured-description">Review the full camera frame and its detection result together.</p>
      <dl className="featured-facts">
        <div><dt>Captured</dt><dd>{formatTime(photo.received_at)}</dd></div>
        {photo.burst_id && <div><dt>Burst frame</dt><dd>{photo.photo_number ?? '?'} of 5</dd></div>}
        {confidence && <div><dt>Person confidence</dt><dd>{confidence}</dd></div>}
      </dl>
      <button type="button" className="featured-action" onClick={event => onOpen(photo, event.currentTarget)}>Inspect full image <ArrowRight size={17} /></button>
    </div>
  </section>
}

export function PhotoCard({ photo, annotated, onOpen, index = 0, isNew = false }) {
  const [view, setView] = useState(annotated && photo.annotated_url ? 'annotated' : 'original')
  const [loaded, setLoaded] = useState(false)
  const [broken, setBroken] = useState(false)
  const [newVisible, setNewVisible] = useState(isNew)
  const pointer = usePointerGlow()
  const relative = useRelativeTime(photo.received_at)
  useEffect(() => setView(annotated && photo.annotated_url ? 'annotated' : 'original'), [annotated, photo.annotated_url])
  useEffect(() => {
    if (!isNew) { setNewVisible(false); return }
    setNewVisible(true)
    const timer = window.setTimeout(() => setNewVisible(false), 8000)
    return () => window.clearTimeout(timer)
  }, [isNew])
  const src = view === 'annotated' && photo.annotated_url ? photo.annotated_url : photo.image_url
  return <article className={`glass glass--light photo-card tone-${photoTone(photo)} ${newVisible ? 'is-new' : ''}`} style={{ '--i': Math.min(index, 12) }} {...pointer}>
    <button type="button" className="photo-open" onClick={event => onOpen(photo, event.currentTarget)} aria-label={`Open ${photo.name}`}>
      <div className={`photo-frame ${loaded ? 'is-loaded' : ''}`}>
        {!broken && <img key={src} src={src} alt={`Camera capture ${photo.name}, ${formatTime(photo.received_at)}`} loading="lazy" decoding="async" onLoad={() => { setLoaded(true); setBroken(false) }} onError={() => { setBroken(true); setLoaded(false) }} />}
        {broken && <span className="image-fallback"><ImageOff size={27} />Image unavailable</span>}
        {!loaded && !broken && <span className="image-skeleton" aria-hidden="true" />}
      </div>
      <span className="photo-meta-row">
        <span className="photo-badge-row"><StatusBadge photo={photo} />{newVisible && <span className="new-pill">NEW</span>}</span>
        {photo.burst_id && <span className="burst-chip">B{photo.burst_id.split('-').at(-1)} · {photo.photo_number ?? '?'}/5</span>}
      </span>
      <div className="photo-details"><strong>{formatTime(photo.received_at)}</strong><span>{relative}</span><small title={photo.name}>{photo.name}</small></div>
    </button>
    <div className="card-actions" aria-label={`Image version for ${photo.name}`}>
      <button type="button" className={view === 'original' ? 'active' : ''} onClick={() => { setLoaded(false); setBroken(false); setView('original') }} aria-label={`Show original ${photo.name}`}>Original</button>
      <button type="button" className={view === 'annotated' ? 'active' : ''} disabled={!photo.annotated_url} onClick={() => { setLoaded(false); setBroken(false); setView('annotated') }} aria-label={`Show annotated ${photo.name}`}>Annotated</button>
    </div>
  </article>
}

export function BurstCard({ burst, previews = [], onOpen, index = 0 }) {
  const received = new Set(String(burst.photo_numbers || '').split(',').map(Number))
  const finished = new Set(String(burst.finished_numbers || '').split(',').map(Number))
  const incomplete = burst.received < 5
  const processing = !incomplete && burst.finished < 5
  const status = incomplete ? `Received ${burst.received}/5` : processing ? `Processing ${burst.finished}/5` : 'Complete 5/5'
  const relative = useRelativeTime(burst.first_received)
  const progress = Math.min(5, burst.received) / 5
  return <button type="button" className={`glass glass--light burst-card ${incomplete ? 'is-incomplete' : 'is-complete'}`} onClick={() => onOpen(burst)} style={{ '--i': Math.min(index, 12) }} aria-label={`${burst.burst_id}, ${status}`}>
    <div className="burst-main"><span className="burst-icon"><Layers3 size={20} /></span><div><span className="burst-title">CAPTURE SEQUENCE</span><strong>{burst.burst_id}</strong><small>{formatTime(burst.first_received)} · {relative}</small></div><span className={`burst-status ${incomplete ? 'partial' : processing ? 'processing' : 'complete'}`}>{incomplete ? <AlertTriangle size={14} /> : <Check size={14} />}{status}</span><span className="progress-ring" aria-label={`${burst.received} of 5 received`}><svg viewBox="0 0 44 44" aria-hidden="true"><circle className="ring-track" cx="22" cy="22" r="17" /><circle className="ring-fill" cx="22" cy="22" r="17" strokeDasharray={`${progress * 106.8} 106.8`} /></svg><b>{burst.received}<small>/5</small></b></span></div>
    <div className="burst-slots">{Array.from({ length: 5 }, (_, index) => {
      const number = index + 1
      const present = received.has(number)
      const photo = previews.find(item => Number(item.photo_number) === number)
      const label = photo?.ml_state === 'person_detected' ? 'Person' : photo?.ml_state === 'no_person_detected' ? 'No person' : photo?.ml_state === 'error' ? 'Error' : present ? 'Pending' : 'MISSING'
      return <span key={number} className={`burst-slot ${present ? finished.has(number) ? 'finished' : 'received' : 'missing'} ${photo?.ml_state || ''}`} title={present ? `Frame ${number}: ${label}` : `Frame ${number} missing: the camera upload was never received`}>
        {photo && <img src={photo.annotated_url || photo.image_url} alt="" loading="lazy" decoding="async" />}
        <span className="slot-number">{number}</span><span className="slot-state">{label}</span><span className="slot-dot" />
      </span>
    })}</div><span className="burst-action">Inspect frames <ArrowRight size={16} /></span>
  </button>
}

export function PhotoViewer({ photo, photos = [], onClose, onNavigate, initialAnnotated }) {
  const [view, setView] = useState(initialAnnotated && photo.annotated_url ? 'annotated' : 'original')
  const [copied, setCopied] = useState(false)
  const [focusImage, setFocusImage] = useState(false)
  const panel = useRef(null)
  const closeRef = useRef(null)
  const index = photos.findIndex(item => item.id === photo.id)
  const hasPrevious = index > 0
  const hasNext = index >= 0 && index < photos.length - 1
  const source = view === 'annotated' && photo.annotated_url ? photo.annotated_url : photo.image_url
  useEffect(() => { setView(initialAnnotated && photo.annotated_url ? 'annotated' : 'original'); setCopied(false) }, [photo.id, initialAnnotated, photo.annotated_url])
  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    closeRef.current?.focus()
    return () => { document.body.style.overflow = previousOverflow }
  }, [])
  useEffect(() => {
    for (const neighbour of [photos[index - 1], photos[index + 1]]) if (neighbour) { const image = new Image(); image.src = neighbour.image_url }
  }, [photos, index])
  useEffect(() => {
    function onKey(event) {
      if (event.key === 'Escape') { event.preventDefault(); onClose() }
      if (event.key === 'ArrowLeft' && hasPrevious) { event.preventDefault(); onNavigate(index - 1) }
      if (event.key === 'ArrowRight' && hasNext) { event.preventDefault(); onNavigate(index + 1) }
      if (event.key === 'Tab') {
        const focusable = [...panel.current.querySelectorAll('button:not(:disabled)')].filter(button => button.getClientRects().length > 0)
        const first = focusable[0], last = focusable.at(-1)
        if (!panel.current.contains(document.activeElement)) { event.preventDefault(); first.focus() }
        else if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, onNavigate, index, hasPrevious, hasNext])
  async function copyId() { try { await navigator.clipboard.writeText(photo.id); setCopied(true); window.setTimeout(() => setCopied(false), 1800) } catch { setCopied(false) } }
  const confidence = photo.ml_state === 'person_detected' && typeof photo.prediction?.confidence === 'number' ? Math.round(photo.prediction.confidence * 100) : null
  return <div className="viewer-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
    <section ref={panel} className={`glass glass--strong viewer ${focusImage ? 'viewer--focus' : ''}`} role="dialog" aria-modal="true" aria-label={`Capture ${photo.name}`}>
      <div className="viewer-image-pane"><div className="viewer-top"><span className="eyebrow">CAPTURE INSPECTOR</span><div className="viewer-top-actions"><button type="button" className="viewer-focus-button" onClick={() => setFocusImage(value => !value)} aria-pressed={focusImage} aria-label={focusImage ? 'Show image details' : 'Enlarge image'} title={focusImage ? 'Show details' : 'Enlarge image'}>{focusImage ? <Minimize2 size={17} /> : <Maximize2 size={17} />}<span>{focusImage ? 'Show details' : 'Enlarge image'}</span></button><button ref={closeRef} className="icon-button" onClick={onClose} aria-label="Close full image" title="Close"><X size={20} /></button></div></div><img key={source} className="viewer-image" src={source} alt={`Full camera capture ${photo.name}, ${formatTime(photo.received_at)}`} /><div className="viewer-image-controls"><button className="icon-button" disabled={!hasPrevious} onClick={() => onNavigate(index - 1)} aria-label="Previous image" title="Previous image"><ArrowLeft size={19} /></button><SegmentedControl options={[{ value: 'original', label: 'Original' }, { value: 'annotated', label: 'Annotated', disabled: !photo.annotated_url }]} value={view} onChange={setView} label="Image version" /><button className="icon-button" disabled={!hasNext} onClick={() => onNavigate(index + 1)} aria-label="Next image" title="Next image"><ArrowRight size={19} /></button></div></div>
      <aside className="viewer-info"><span className="eyebrow">IMAGE INTELLIGENCE</span><h2>Capture details</h2><StatusBadge photo={photo} /><div className="metadata"><span>CAPTURED</span><strong>{formatTime(photo.received_at)}</strong><span>PHOTO ID</span><div className="copy-row"><code>{photo.id}</code><button className="icon-button" onClick={copyId} aria-label="Copy photo ID" title="Copy photo ID">{copied ? <Check size={16} /> : <Copy size={16} />}</button></div>{photo.burst_id && <><span>BURST</span><code>{photo.burst_id}</code></>}<span>ML STATE</span><strong>{photoLabel(photo)}</strong></div>{confidence !== null && <div className="confidence"><div><span>PERSON CONFIDENCE</span><b>{confidence}%</b></div><span className="confidence-track"><span style={{ width: `${confidence}%` }} /></span></div>}{photo.error && <p className="viewer-error">{photo.error}</p>}<p className="viewer-note">No person detected is a model result, not proof the scene is empty.</p></aside>
    </section>
  </div>
}

export function Pagination({ page, pages, onPage }) {
  if (pages <= 1) return null
  return <nav className="pagination" aria-label="Gallery pages"><button disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label="Previous page"><ChevronLeft size={16} />Previous</button><span><b>{page}</b><span> / {pages}</span></span><button disabled={page >= pages} onClick={() => onPage(page + 1)} aria-label="Next page">Next<ChevronRight size={16} /></button></nav>
}
