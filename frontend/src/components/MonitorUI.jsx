import React, { useEffect, useState } from 'react'
import { ArrowUpRight, Check, ChevronLeft, ChevronRight, CircleAlert, Clock3, ImageOff, Layers3, LoaderCircle, ScanLine, ShieldCheck } from 'lucide-react'
import { formatDate, shortEvent } from '../lib/events.js'
const STATES = { cancelled: ['Analysis cancelled', Clock3], person: ['Person detected', ScanLine], no_person: ['No person detected', Check], pending: ['Needs analysis', Clock3], processing: ['Processing', LoaderCircle], error: ['Analysis error', CircleAlert], online: ['Connected', Check], offline: ['Unavailable', CircleAlert], unknown: ['Not configured', ShieldCheck] }
export function Badge({ state = 'pending', children }) {
  const [label, Icon] = STATES[state] || STATES.pending
  return <span className={`badge badge--${state}`}><Icon size={12} aria-hidden="true" />{children || label}</span>
}
export function CameraImage({ photo, annotated = false, className = '', eager = false }) {
  const src = annotated && photo?.annotated_url ? photo.annotated_url : photo?.image_url
  const [state, setState] = useState('loading')
  useEffect(() => setState('loading'), [src])
  return <div className={`camera-image ${className} ${state === 'loading' ? 'image-loading' : ''}`}>
    {src && state !== 'error' && <img key={src} src={src} alt={`Camera frame ${photo.photo_number || ''}, ${formatDate(photo.received_at)}`} loading={eager ? 'eager' : 'lazy'} decoding="async" onLoad={() => setState('ready')} onError={() => setState('error')} />}
    {(!src || state === 'error') && <div className="image-unavailable"><ImageOff size={25} /><span>{src ? 'Image unavailable' : 'No capture yet'}</span></div>}
  </div>
}
export function EventCard({ event, index, onOpen }) {
  return <article className="event-card" style={{ '--order': index }}><button className="event-card-link" data-event-id={event.id} onClick={e => onOpen(event, e.currentTarget)} aria-label={`Review ${shortEvent(event.id)}, ${formatDate(event.firstAt)}, ${event.received} frames`}>
    <div className="event-card-image"><CameraImage photo={event.preview} /><span className="image-sequence"><Layers3 size={12} />{event.received}/{event.expected} frames</span><span className="image-open"><ArrowUpRight size={19} /></span></div>
    <div className="event-card-body"><div className="event-card-heading"><span className="event-number">{shortEvent(event.id)}</span><time>{new Intl.DateTimeFormat('en-IN', { hour: '2-digit', minute: '2-digit' }).format(new Date(event.lastAt))}</time></div><Badge state={event.state} /><div className="event-card-footer"><span>{formatDate(event.lastAt)}{event.incomplete && ' · Incomplete'}</span><span>Review event <ArrowUpRight size={13} /></span></div></div>
  </button></article>
}
export function EmptyState({ title, children, error = false, action, onAction }) {
  const Icon = error ? CircleAlert : Layers3
  return <div className="empty-state"><div className="empty-icon"><Icon size={27} /></div><h3>{title}</h3><p>{children}</p>{action && <button className="button button--primary" onClick={onAction}>{action}<ArrowUpRight size={15} /></button>}</div>
}
export function Skeleton({ count = 6 }) { return <div className="events-grid" aria-label="Loading events" aria-busy="true">{Array.from({ length: count }, (_, i) => <div key={i} className="skeleton-card"><div /><span /><span /></div>)}</div> }
export function Metric({ icon: Icon, label, value, caption, accent = 'blue' }) { return <div className={`metric metric--${accent}`}><div className="metric-top"><span>{label}</span><Icon size={17} /></div><strong>{value ?? '—'}</strong><p>{caption}</p></div> }
export function Pagination({ page, pages, total, onChange }) {
  if (!total) return null
  return <div className="pagination"><span>{total} event{total === 1 ? '' : 's'}<span className="pagination-detail"> · Six per page</span></span><nav aria-label="Event pages"><button className="icon-button" disabled={page <= 1} onClick={() => onChange(page - 1)} aria-label="Previous page"><ChevronLeft size={17} /></button><span>Page <b>{page}</b> of {pages || 1}</span><button className="icon-button" disabled={page >= pages} onClick={() => onChange(page + 1)} aria-label="Next page"><ChevronRight size={17} /></button></nav></div>
}
export function SectionHeading({ eyebrow, title, children, action }) { return <div className="section-heading"><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h2>{title}</h2>{children && <p>{children}</p>}</div>{action}</div> }
export function InfoRow({ label, children }) { return <div className="info-row"><dt>{label}</dt><dd>{children}</dd></div> }
