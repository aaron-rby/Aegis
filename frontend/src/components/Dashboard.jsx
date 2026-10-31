import React from 'react'
import { Activity, Camera, Image, Layers3, RefreshCw, Server, ShieldCheck, TriangleAlert, WifiOff } from 'lucide-react'
import { useCountUp } from '../hooks/useCountUp.js'
import { useRelativeTime } from '../hooks/useRelativeTime.js'

export function StatCard({ icon: Icon, label, value, caption, tone = 'brand', numeric = false }) {
  const animated = useCountUp(numeric ? value : null)
  return <article className={`glass stat-card tone-${tone}`}>
    <div className="stat-icon"><Icon size={20} strokeWidth={1.9} /></div>
    <div className="stat-copy"><span className="stat-name">{label}</span><strong>{numeric ? animated ?? '—' : value ?? '—'}</strong><small>{caption}</small></div>
  </article>
}

function SystemRow({ icon: Icon, name, value, tone }) {
  return <div className="system-row"><Icon size={15} aria-hidden="true" /><span>{name}</span><span className={`system-dot dot-${tone}`} /><small>{value}</small></div>
}

export function Sidebar({ section, onSection, offline, workerOnline, status }) {
  const uploadTime = useRelativeTime(status?.last_camera_upload?.received_at)
  return <aside className="glass sidebar">
    <div className="brand"><span className="brand-mark"><ShieldCheck size={22} strokeWidth={2} /></span><div className="brand-words"><strong>AEGIS</strong><span>COMMAND CENTER</span></div></div>
    <div className="nav-label">WORKSPACE</div>
    <nav className="side-nav" aria-label="Main navigation">
      <button className={section === 'photos' ? 'active' : ''} onClick={() => onSection('photos')} aria-label="Photo gallery" title="Photo gallery"><Image size={18} /><span>Photo gallery</span></button>
      <button className={section === 'bursts' ? 'active' : ''} onClick={() => onSection('bursts')} aria-label="Capture bursts" title="Capture bursts"><Layers3 size={18} /><span>Capture bursts</span></button>
    </nav>
    <div className="sidebar-system"><div className="system-heading"><Activity size={15} /><strong>System</strong></div>
      <SystemRow icon={Server} name="Backend" tone={offline ? 'danger' : 'success'} value={offline ? 'Offline' : 'Online'} />
      <SystemRow icon={Activity} name="ML worker" tone={offline ? 'muted' : workerOnline ? 'success' : 'warning'} value={offline ? 'Unknown' : workerOnline ? 'Online' : 'Stale'} />
      <SystemRow icon={Camera} name="Camera" tone={status?.last_camera_upload ? 'brand' : 'muted'} value={uploadTime} />
    </div>
  </aside>
}

export function MobileNav({ section, onSection }) {
  return <nav className="glass mobile-nav" aria-label="Mobile navigation">
    <button className={section === 'photos' ? 'active' : ''} onClick={() => onSection('photos')}><Image size={19} /><span>Gallery</span></button>
    <button className={section === 'bursts' ? 'active' : ''} onClick={() => onSection('bursts')}><Layers3 size={19} /><span>Bursts</span></button>
  </nav>
}

export function SegmentedControl({ options, value, onChange, label }) {
  const index = Math.max(0, options.findIndex(option => option.value === value))
  return <div className="segmented" role="group" aria-label={label} style={{ '--segments': options.length, '--index': index }}>
    <span className="segmented-thumb" aria-hidden="true" />
    {options.map(option => <button type="button" key={option.value} className={value === option.value ? 'selected' : ''} onClick={() => onChange(option.value)} disabled={option.disabled} aria-pressed={value === option.value}>{option.label}</button>)}
  </div>
}

export function StatusBanner({ offline, workerOnline, heartbeatAt, lastSuccessAt, onRetry }) {
  const lastSuccess = useRelativeTime(lastSuccessAt)
  const heartbeat = useRelativeTime(heartbeatAt)
  if (!offline && workerOnline) return null
  return <div className={`glass status-banner ${offline ? 'banner-danger' : 'banner-warning'}`} role="status" aria-live="polite">
    {offline ? <WifiOff size={19} /> : <TriangleAlert size={19} />}
    <div><strong>{offline ? 'Backend connection lost' : 'ML worker heartbeat is stale'}</strong><p>{offline ? `Showing saved results. Last connected ${lastSuccess}.` : `New photos may be waiting. Last worker heartbeat ${heartbeat}.`}</p></div>
    <button type="button" onClick={onRetry} aria-label="Retry connection" title="Retry connection"><RefreshCw size={17} /></button>
  </div>
}

export function Skeleton({ count = 6 }) {
  return <div className="photo-grid" aria-label="Loading photos">{Array.from({ length: count }, (_, i) => <div className="glass glass--light skeleton-card" key={i}><div className="skeleton-image" /><div className="skeleton-line" /><div className="skeleton-line short" /></div>)}</div>
}

export function EmptyState({ title, message, action, onAction, error = false }) {
  return <div className="glass empty-state">{error ? <TriangleAlert size={32} /> : <Image size={32} />}<h3>{title}</h3><p>{message}</p>{onAction && <button type="button" className="action-button" onClick={onAction}>{action}</button>}</div>
}

export function Header({ section, selectedBurst, filter, filters, onFilter, photosTotal, updatedAt, scrolled, onRefresh }) {
  const updated = useRelativeTime(updatedAt)
  return <header className={`glass topbar ${scrolled ? 'is-scrolled' : ''}`}>
    <div className="topbar-title"><span className="topbar-eyebrow">LIVE MONITORING</span><h1>{section === 'bursts' ? 'Capture bursts' : selectedBurst ? 'Burst details' : 'Camera gallery'}</h1><p>Every frame. Every signal. One clear view.</p></div>
    <div className="topbar-tools"><span className="updated"><span className="live-dot" />{updatedAt ? `Updated ${updated}` : 'Connecting…'}</span>{section === 'photos' && <SegmentedControl options={filters} value={filter} onChange={onFilter} label="Filter photos" />}<span className="result-chip">{photosTotal} results</span><button type="button" className="icon-button refresh-button" title="Refresh now" aria-label="Refresh now" onClick={onRefresh}><RefreshCw size={17} /></button></div>
  </header>
}
