import React, { useRef, useState } from 'react'
import { Activity, ArrowDownToLine, ArrowRight, ArrowUpRight, Camera, Check, ChevronRight, CircleHelp, Clock3, Cpu, FileImage, Layers3, ScanLine, Server, Settings2, ShieldCheck, Wifi } from 'lucide-react'
import { Badge, CameraImage, EmptyState, InfoRow, Metric, SectionHeading, Skeleton } from '../components/MonitorUI.jsx'
import { formatClock, formatDate, modelName, shortEvent } from '../lib/events.js'
import { useRelativeTime } from '../hooks/useRelativeTime.js'
import { HardwareSignals } from './HardwarePage.jsx'

export function Overview({ events, displayEvents = events, monitor, hardware, onOpen, onNavigate }) {
  const { status, loading, offline } = monitor
  const latest = displayEvents[0]
  const uploadTime = useRelativeTime(status?.last_camera_upload?.received_at)
  const people = events.filter(event => event.people > 0).length
  const pending = (status?.jobs?.queued || 0) + (status?.jobs?.processing || 0)
  const worker = !offline && status?.worker?.running
  if (loading) return <Skeleton count={3} />
  return <>
    <div className="overview-metrics"><Metric icon={Layers3} label="Capture events" value={monitor.updatedAt ? events.length : null} caption="Across your saved archive" /><Metric icon={ScanLine} label="With person detections" value={monitor.updatedAt ? people : null} caption="Events with a positive frame" accent="violet" /><Metric icon={Clock3} label="In the processing queue" value={status ? pending : null} caption="Queued and currently processing" accent="amber" /></div>
    <div className="overview-main">
      <section className="latest-panel"><SectionHeading eyebrow="THE LATEST MOMENT" title="Latest capture event" action={<span className="small-outline-label"><Camera size={13} />ESP32-CAM</span>} />
        {latest ? <div className="latest-panel-body"><button className="latest-photo" onClick={e => onOpen(latest, e.currentTarget)} aria-label="Review latest event"><CameraImage photo={latest.preview} eager /><span className="latest-photo-tag"><span />Saved camera capture</span><span className="latest-photo-action"><ArrowUpRight size={22} /></span></button><div className="latest-bottom"><div><span className="eyebrow">{shortEvent(latest.id)}</span><strong>{formatClock(latest.lastAt)}</strong><Badge state={latest.state} /></div><button className="button button--dark" onClick={e => onOpen(latest, e.currentTarget)}>Review event <ArrowUpRight size={15} /></button></div></div> : <EmptyState title="Ready for your next capture">New captures will appear here automatically. Previously cleared photos remain saved in the system.</EmptyState>}
      </section>
      <div className="overview-aside"><section className="health-panel"><div className="health-panel-top"><span className="eyebrow">PROCESSING HEALTH</span><Activity size={18} /></div><h2>The signals<br />behind the scenes.</h2><p>Service availability, without the guesswork.</p><div className="health-item"><span className="health-icon"><Server size={17} /></span><div><strong>Photo receiver</strong><small>Python backend</small></div><span className={`health-tag ${offline ? 'health-tag--amber' : ''}`}>{offline ? 'Unavailable' : 'Connected'}</span></div><div className="health-item"><span className="health-icon"><Cpu size={17} /></span><div><strong>ML worker</strong><small>YOLO person detection</small></div><span className={`health-tag ${!worker ? 'health-tag--amber' : ''}`}>{offline ? 'Unknown' : worker ? 'Active' : 'No heartbeat'}</span></div><button className="health-link" onClick={() => onNavigate('system')}>View system details <ArrowUpRight size={16} /></button></section>
      <section className="upload-note"><div className="upload-note-icon"><ArrowDownToLine size={20} /></div><span className="eyebrow">LAST CAMERA UPLOAD</span><h3>{status?.last_camera_upload ? uploadTime : 'Nothing received yet'}</h3><p>{status?.last_camera_upload ? formatClock(status.last_camera_upload.received_at) : 'Received uploads will be timestamped here.'}</p><small>Upload history is not a live camera connection.</small></section></div>
    </div>
    <HardwareSignals hardware={hardware} onNavigate={onNavigate} />
    <section className="recent-section"><SectionHeading eyebrow="YOUR EVENT TIMELINE" title="Recent events" action={<button className="text-button" onClick={() => onNavigate('events')}>View all events <ArrowRight size={15} /></button>} />
      <div className="recent-table">{displayEvents.slice(0, 3).map(event => <button className="recent-row" key={event.id} onClick={e => onOpen(event, e.currentTarget)}><div className="recent-thumb"><CameraImage photo={event.preview} /></div><div className="recent-title"><strong>{shortEvent(event.id)}</strong><span>{formatClock(event.lastAt)}</span></div><Badge state={event.state} /><span className={`recent-count ${event.incomplete ? 'recent-count--missing' : ''}`}><Layers3 size={14} />{event.received}/{event.expected} frames</span><ArrowUpRight size={19} className="recent-arrow" /></button>)}{!displayEvents.length && <p className="simple-empty">No events to display. New captures will appear here.</p>}</div>
    </section>
  </>
}

function ServiceRow({ icon: Icon, title, description, children }) {
  return <div className="service-row"><span className="service-icon"><Icon size={20} /></span><div className="service-description"><h3>{title}</h3><p>{description}</p></div>{children}</div>
}
function ClearQueue({ monitor }) {
  const [confirm, setConfirm] = useState(false), [busy, setBusy] = useState(false), [message, setMessage] = useState('')
  const lock = useRef(false)
  const count = (monitor.status?.jobs?.queued || 0) + (monitor.status?.jobs?.processing || 0)
  async function clear() {
    if (lock.current) return
    lock.current = true; setBusy(true); setMessage('')
    try {
      const response = await fetch('/api/queue/clear', { method: 'POST' })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Could not clear queue.')
      setConfirm(false); setMessage(`${result.cancelled} analysis jobs cancelled. ${result.detail}`)
      await monitor.refresh()
    } catch (error) { setMessage(error.message) }
    finally { lock.current = false; setBusy(false) }
  }
  return <div className="queue-clear"><p>Cancel pending analysis. Keep all photos, completed results and training data.</p>{confirm ? <><p>Cancel queued and currently processing jobs? These frames will remain saved without a new result.</p><div><button className="button event-delete-button" disabled={busy} onClick={clear}>{busy ? 'Clearing...' : 'Confirm clear queue'}</button><button className="text-button" disabled={busy} onClick={() => setConfirm(false)}>Cancel</button></div></> : <button className="button event-delete-button" disabled={monitor.offline || !count || busy} onClick={() => setConfirm(true)}>Clear processing queue</button>}{message && <p role="status">{message}</p>}</div>
}
export function SystemPage({ monitor, onNavigate }) {
  const { status, loading, offline, updatedAt } = monitor
  const heartbeat = useRelativeTime(status?.worker?.heartbeat_at)
  if (loading) return <Skeleton count={2} />
  return <>
    <div className="system-overview"><span className="system-orbit"><Activity size={27} /></span><div><span className="eyebrow">LOCAL SERVICES</span><h2>{offline ? 'Connection needs attention.' : status?.worker?.running ? 'Your processing services are connected.' : 'Receiver connected. Worker needs attention.'}</h2><p>Reported service states are separate from physical sensor and camera health.</p></div><Badge state={offline || !status?.worker?.running ? 'pending' : 'online'}>{offline ? 'Unavailable' : status?.worker?.running ? 'Services connected' : 'Check ML worker'}</Badge></div>
    <div className="system-columns"><section className="panel"><SectionHeading title="Service connections">Current availability reported by the backend.</SectionHeading><ServiceRow icon={Server} title="Backend receiver" description="Receives camera uploads and serves your archive."><Badge state={offline ? 'offline' : 'online'} /></ServiceRow><ServiceRow icon={Cpu} title="ML worker" description={status?.worker?.heartbeat_at ? `Last heartbeat ${heartbeat.toLowerCase()}` : 'No worker heartbeat has been reported.'}><Badge state={offline ? 'offline' : status?.worker?.running ? 'online' : 'pending'}>{offline ? 'Unknown' : status?.worker?.running ? 'Active' : 'No fresh heartbeat'}</Badge></ServiceRow><ServiceRow icon={Camera} title="Camera upload" description={status?.last_camera_upload ? `Last received ${formatClock(status.last_camera_upload.received_at)}` : 'No camera upload has been reported.'}><span className="neutral-label">{status?.last_camera_upload ? 'Upload recorded' : 'Waiting'}</span></ServiceRow></section>
      <section className="panel queue-panel"><SectionHeading title="Processing queue">Camera frames awaiting a result.</SectionHeading><div className="queue-total"><strong>{status ? (status.jobs?.queued || 0) + (status.jobs?.processing || 0) : '—'}</strong><span>active jobs</span></div><dl><InfoRow label="Queued">{status?.jobs?.queued ?? '—'}</InfoRow><InfoRow label="Processing">{status?.jobs?.processing ?? '—'}</InfoRow><InfoRow label="Job errors"><span className={status?.jobs?.errors ? 'error-text' : ''}>{status?.jobs?.errors ?? '—'}</span></InfoRow><InfoRow label="Analysis cancelled">{status?.jobs?.cancelled ?? 0}</InfoRow><InfoRow label="Legacy frames not queued">{status?.jobs?.legacy_unprocessed ?? '—'}</InfoRow></dl><ClearQueue monitor={monitor} /></section></div>
    <section className="panel telemetry-panel"><div className="telemetry-icon"><Wifi size={23} /></div><div><h3>Physical sensor telemetry</h3><p>Connect the main ESP32 in Hardware to read PIR, distance and controller state. Backend availability alone does not confirm sensor or camera health.</p></div><button className="text-button" onClick={() => onNavigate('hardware')}>Open Hardware <ArrowUpRight size={15} /></button></section>
    <details className="technical-details"><summary>Service diagnostics <ChevronRight size={16} /></summary><dl><InfoRow label="Last successful refresh">{formatClock(updatedAt)}</InfoRow><InfoRow label="Worker heartbeat">{formatClock(status?.worker?.heartbeat_at)}</InfoRow><InfoRow label="Worker ID"><code>{status?.worker?.id || 'Not reported'}</code></InfoRow><InfoRow label="Worker model"><code>{status?.worker?.model || 'Not reported'}</code></InfoRow></dl></details>
  </>
}

export function ConfigurationPage({ monitor }) {
  const { status } = monitor
  return <>
    <div className="configuration-banner"><Settings2 size={20} /><div><strong>Your setup, clearly documented.</strong><p>Configuration is read-only. The current API does not provide settings controls.</p></div><span className="neutral-label">Read only</span></div>
    <section className="settings-section"><div className="settings-description"><span className="eyebrow">01 / CAPTURE</span><h2>Camera workflow</h2><p>Sensor-triggered photography, grouped into one reviewable event.</p></div><div className="panel settings-values"><dl><InfoRow label="Camera">ESP32-CAM</InfoRow><InfoRow label="Event grouping">Camera burst identifier</InfoRow><InfoRow label="Expected frames">5 per burst</InfoRow><InfoRow label="Image versions">Original and ML annotation</InfoRow><InfoRow label="Capture mode">Event photographs · not a live stream</InfoRow></dl></div></section>
    <section className="settings-section"><div className="settings-description"><span className="eyebrow">02 / ANALYSIS</span><h2>Person detection</h2><p>The laptop worker analyzes uploaded frames. Predictions are evidence to review.</p></div><div className="panel settings-values"><dl><InfoRow label="Configured model"><code>{modelName(status?.configured_model)}</code></InfoRow><InfoRow label="Reported worker model"><code>{modelName(status?.worker?.model)}</code></InfoRow><InfoRow label="Detection target">Person</InfoRow><InfoRow label="Confidence threshold">Not exposed by the API</InfoRow><InfoRow label="Identity / authorization">Not evaluated by this application</InfoRow></dl></div></section>
    <section className="settings-section"><div className="settings-description"><span className="eyebrow">03 / WORKSPACE</span><h2>Interface behavior</h2><p>Designed for focused evidence review with quiet background updates.</p></div><div className="panel settings-values"><dl><InfoRow label="Events per page">6</InfoRow><InfoRow label="Background refresh">Every 5 seconds while visible</InfoRow><InfoRow label="Display">Dark navigation · light workspace</InfoRow><InfoRow label="Motion">Follows your system preference</InfoRow></dl></div></section>
  </>
}
