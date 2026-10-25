import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Activity, ArrowUpRight, ChevronRight, Clock3, Layers3, LayoutDashboard, Menu, RefreshCw, Settings2, Shield, X } from 'lucide-react'
import { useMonitor } from './hooks/useMonitor.js'
import { useRelativeTime } from './hooks/useRelativeTime.js'
import { FILTERS, PAGE_SIZE, formatDate, groupEvents, matchesFilter } from './lib/events.js'
import { EmptyState, EventCard, Pagination, Skeleton } from './components/MonitorUI.jsx'
import { Overview, SystemPage, ConfigurationPage } from './pages/MonitorPages.jsx'
import EventDetails from './pages/EventDetails.jsx'
import HardwarePage from './pages/HardwarePage.jsx'
import { useHardware } from './hooks/useHardware.js'

const NAV = [['overview', 'Overview', LayoutDashboard], ['events', 'Events', Layers3], ['hardware', 'Hardware', Activity], ['system', 'System', Activity], ['configuration', 'Configuration', Settings2]]
const TITLES = {
  overview: ['Your monitoring, at a glance.', 'A considered view of your camera events and processing health.'],
  events: ['A moment. Every detail.', 'Five frames, one event. Review the evidence without the noise.'],
  system: ['Behind every capture.', 'Connection, processing and service health in one place.'],
  hardware: ['The signals behind the scene.', 'Actual sensor readings, directly from your main ESP32.'],
  configuration: ['Built around your setup.', 'A read-only view of the current monitoring configuration.'],
}
function route() {
  const parts = location.hash.slice(1).split('/')
  let eventId = null
  try { eventId = parts[1] ? decodeURIComponent(parts.slice(1).join('/')) : null } catch { /* Invalid URL returns to the archive. */ }
  return { page: NAV.some(([id]) => id === parts[0]) ? parts[0] : 'overview', eventId }
}

export default function App() {
  const monitor = useMonitor()
  const hardware = useHardware()
  const events = useMemo(() => groupEvents(monitor.photos), [monitor.photos])
  const [current, setCurrent] = useState(route)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [filter, setFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [newEvents, setNewEvents] = useState(false)
  const [order, setOrder] = useState([])
  const openerRef = useRef(null), scrollRef = useRef(0), headingRef = useRef(null), navRef = useRef(null), menuRef = useRef(null)
  const previousRoute = useRef(current)
  const lastRelative = useRelativeTime(monitor.updatedAt)

  useEffect(() => {
    const handler = () => { setCurrent(route()); setMobileOpen(false) }
    window.addEventListener('hashchange', handler)
    return () => window.removeEventListener('hashchange', handler)
  }, [])
  useEffect(() => {
    const previous = previousRoute.current
    previousRoute.current = current
    if (previous.eventId && !current.eventId && current.page === 'events') {
      requestAnimationFrame(() => {
        window.scrollTo(0, scrollRef.current)
        const target = [...document.querySelectorAll('[data-event-id]')].find(el => el.dataset.eventId === previous.eventId)
        ;(target || headingRef.current)?.focus({ preventScroll: true })
      })
    } else if (previous.page !== current.page || previous.eventId !== current.eventId) {
      window.scrollTo(0, 0); headingRef.current?.focus({ preventScroll: true })
    }
  }, [current])
  useEffect(() => {
    if (!events.length) return
    if (!order.length) setOrder(events.map(event => event.id))
    else if (events.some(event => !order.includes(event.id))) {
      if (current.page === 'events' && !current.eventId && page === 1) {
        setOrder(events.map(event => event.id))
        setNewEvents(false)
      } else setNewEvents(true)
    }
  }, [events, order, current.page, current.eventId, page])
  useEffect(() => {
    if (!mobileOpen) return
    const before = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    navRef.current?.querySelector('button')?.focus()
    function onKey(e) {
      if (e.key === 'Escape') { setMobileOpen(false); menuRef.current?.focus() }
      if (e.key === 'Tab') {
        const controls = [...navRef.current.querySelectorAll('button')].filter(el => el.getClientRects().length)
        const first = controls[0], last = controls.at(-1)
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
      }
    }
    window.addEventListener('keydown', onKey)
    return () => { document.body.style.overflow = before; window.removeEventListener('keydown', onKey) }
  }, [mobileOpen])

  function navigate(next) { location.hash = next; setMobileOpen(false) }
  function openEvent(event, opener) { openerRef.current = opener; scrollRef.current = window.scrollY; location.hash = `events/${encodeURIComponent(event.id)}` }
  const orderedEvents = useMemo(() => {
    const lookup = new Map(events.map(event => [event.id, event]))
    return order.map(id => lookup.get(id)).filter(Boolean)
  }, [events, order])
  const filtered = orderedEvents.filter(event => matchesFilter(event, filter))
  const pages = Math.ceil(filtered.length / PAGE_SIZE), safePage = Math.min(page, Math.max(1, pages))
  const selected = current.eventId ? events.find(event => event.id === current.eventId) : null
  const title = current.eventId ? 'Event details' : NAV.find(([id]) => id === current.page)?.[1]
  const changeFilter = value => { setFilter(value); setPage(1) }
  const applyNew = () => { setOrder(events.map(event => event.id)); setNewEvents(false); setPage(1) }

  return <div className="sentinel-app">
    <a className="skip-link" href="#main-content" onClick={e => { e.preventDefault(); document.getElementById('main-content').focus() }}>Skip to content</a>
    {mobileOpen && <div className="nav-backdrop" onClick={() => setMobileOpen(false)} />}
    <aside ref={navRef} className={`sidebar ${mobileOpen ? 'sidebar--open' : ''}`} aria-label="Main navigation" {...(mobileOpen ? { role: 'dialog', 'aria-modal': true } : {})}>
      <div className="brand"><span className="brand-symbol"><Shield size={24} strokeWidth={1.8} /></span><div><strong>Sentinel<span>AI</span></strong><small>INTRUSION MONITORING</small></div><button className="mobile-close icon-button" onClick={() => { setMobileOpen(false); menuRef.current?.focus() }} aria-label="Close navigation"><X size={19} /></button></div>
      <div className="workspace-label"><span className="workspace-mark">S</span><div>Project workspace<small>ESP32-CAM · Local deployment</small></div></div>
      <span className="nav-label">WORKSPACE</span>
      <nav>{NAV.map(([id, label, Icon]) => <button key={id} className={`nav-item ${current.page === id ? 'active' : ''}`} aria-current={current.page === id ? 'page' : undefined} onClick={() => navigate(id)}><Icon size={19} /><span>{label}</span>{id === 'events' && events.length > 0 && <small>{events.length}</small>}{current.page === id && <ChevronRight className="nav-chevron" size={15} />}</button>)}</nav>
      <div className="sidebar-bottom"><div className="sidebar-guide"><div className="guide-icon"><Layers3 size={18} /></div><strong>Every frame matters.</strong><p>One event. Five perspectives.<br />Review the complete picture.</p><button onClick={() => navigate('events')}>Explore events <ArrowUpRight size={14} /></button></div><button className="sidebar-health" onClick={() => navigate('system')}><span className={`connection-dot ${monitor.offline ? 'dot--amber' : monitor.loading ? 'dot--muted' : ''}`} /><div>{monitor.loading ? 'Connecting to backend' : monitor.offline ? 'Connection unavailable' : 'Backend connected'}<small>{monitor.offline ? 'Check local services' : 'Local monitoring workspace'}</small></div><ChevronRight size={15} /></button><div className="sidebar-footnote">SENTINEL AI <span>01 / LOCAL</span></div></div>
    </aside>
    <div className="workspace">
      <header className="topbar"><div className="breadcrumb"><button ref={menuRef} className="icon-button menu-button" aria-label="Open navigation" aria-expanded={mobileOpen} onClick={() => setMobileOpen(true)}><Menu size={20} /></button><span className="breadcrumb-project">Workspace</span><ChevronRight size={13} /><strong>{title}</strong></div><div className="topbar-right"><span className="local-tag"><span />Local workspace</span><div className="topbar-separator" /><span className="topbar-date">{formatDate(new Date())}</span><button className={`icon-button ${monitor.refreshing ? 'is-refreshing' : ''}`} aria-label="Refresh monitoring data" title="Refresh monitoring data" onClick={monitor.refresh} disabled={monitor.refreshing}><RefreshCw size={16} /></button></div></header>
      <main id="main-content" tabIndex={-1}>
        <div className="page-heading"><div><div className="page-eyebrow"><span />{current.eventId ? 'CAPTURE INSPECTOR' : title?.toUpperCase()}</div><h1 ref={headingRef} tabIndex={-1}>{current.eventId ? 'One event. The full picture.' : TITLES[current.page][0]}</h1><p>{current.eventId ? 'Inspect each frame and its analysis, together.' : TITLES[current.page][1]}</p></div><div className="page-heading-status"><span className={`connection-dot ${monitor.offline ? 'dot--amber' : monitor.loading ? 'dot--muted' : ''}`} /><span>{monitor.loading ? 'Connecting…' : monitor.offline ? 'Connection interrupted' : 'Connected to backend'}<small>{monitor.updatedAt ? `Updated ${lastRelative.toLowerCase()}` : 'Waiting for first response'}</small></span></div></div>
        {(monitor.offline || monitor.archiveError) && <div className="connection-banner" role="status"><Clock3 size={17} /><div><strong>{monitor.offline ? 'The backend could not be reached.' : 'The capture archive could not be refreshed.'}</strong><span>{monitor.updatedAt ? 'Previously loaded information is still available and may be out of date.' : 'Start the backend to load your saved events.'}</span></div><button onClick={monitor.refresh}>Try again <RefreshCw size={13} /></button></div>}
        {current.eventId ? selected ? <EventDetails event={selected} onBack={() => navigate('events')} /> : monitor.loading ? <Skeleton count={1} /> : <EmptyState title="Event unavailable" error action="Back to events" onAction={() => navigate('events')}>This event could not be loaded. Check the backend connection and try again.</EmptyState> : <>
          {current.page === 'overview' && <Overview events={events} monitor={monitor} hardware={hardware} onOpen={openEvent} onNavigate={navigate} />}
          {current.page === 'hardware' && <HardwarePage hardware={hardware} />}
          {current.page === 'events' && <>
            <div className="archive-toolbar"><div className="filter-tabs" role="group" aria-label="Filter events">{FILTERS.map(([value, label]) => <button key={value} className={filter === value ? 'selected' : ''} aria-pressed={filter === value} onClick={() => changeFilter(value)}>{value === 'all' && <Layers3 size={14} />}{label}{filter === value && <span>{filtered.length}</span>}</button>)}</div><span className="archive-grouping"><Layers3 size={14} />Grouped by trigger</span></div>
            <div className="archive-caption"><p>{filter === 'pending' ? 'Events with frames awaiting analysis or missing uploads.' : filter === 'no_person' ? 'Complete events where every frame returned no person detected.' : 'Each event holds up to five camera frames.'}</p>{newEvents && <button className="new-events-button" onClick={applyNew}>New events available <ArrowUpRight size={14} /></button>}</div>
            {monitor.loading ? <Skeleton /> : !filtered.length ? <EmptyState title={filter === 'all' ? 'Your first event starts here.' : 'No events match this view.'} error={monitor.archiveError} action={filter === 'all' ? 'Refresh archive' : 'Show all events'} onAction={filter === 'all' ? monitor.refresh : () => changeFilter('all')}>{filter === 'all' ? 'Received camera captures will appear here, grouped into five-frame events.' : 'Choose another filter to explore your camera archive.'}</EmptyState> : <div className="events-grid">{filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE).map((event, i) => <EventCard key={event.id} event={event} index={i} onOpen={openEvent} />)}</div>}
            <Pagination page={safePage} pages={pages} total={filtered.length} onChange={next => { setPage(next); window.scrollTo({ top: 0, behavior: 'smooth' }) }} />
          </>}
          {current.page === 'system' && <SystemPage monitor={monitor} onNavigate={navigate} />}
          {current.page === 'configuration' && <ConfigurationPage monitor={monitor} />}
        </>}
        <footer className="workspace-footer"><span><Shield size={13} />Sensor-triggered. Visually reviewed.</span><p>Person detection does not establish identity or authorization.</p><span className="footer-right">ESP32-CAM / YOLO</span></footer>
      </main>
    </div>
  </div>
}
