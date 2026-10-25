import React, { useEffect, useState } from 'react'
import { Activity, ArrowUpRight, Camera, CircleAlert, Clock3, Cpu, Plug, RefreshCw, Unplug, Wifi } from 'lucide-react'
import { Badge, InfoRow, SectionHeading } from '../components/MonitorUI.jsx'
import { formatClock } from '../lib/events.js'

export function SensorChart({ samples = [], motion = false, compact = false }) {
  const end = Date.now() / 1000, start = end - 60, key = motion ? 'pir' : 'distance_cm'
  const data = samples.filter(p => p.received_epoch >= start && p.received_epoch <= end + 1)
  const valid = data.filter(p => typeof p[key] === (motion ? 'boolean' : 'number') && (motion || Number.isFinite(p[key])))
  const max = motion ? 1 : Math.max(100, ...valid.map(p => Math.ceil(p[key] / 50) * 50))
  const x = t => 40 + Math.max(0, Math.min(60, t - start)) / 60 * 480
  const y = value => 125 - Number(value) / max * 100
  let path = '', previous
  for (const p of data) {
    if (!valid.includes(p)) { previous = null; continue }
    const px = x(p.received_epoch), py = y(p[key])
    if (!previous || p.received_epoch - previous.received_epoch > 3.5) path += `M${px},${py} `
    else path += motion ? `L${px},${y(previous[key])} L${px},${py} ` : `L${px},${py} `
    previous = p
  }
  return <svg className={`sensor-chart ${compact ? 'sensor-chart--compact' : ''}`} viewBox="0 0 550 160" role="img" aria-label={`${motion ? 'PIR motion' : 'Distance'} received samples, last 60 seconds`}>
    {[0, max / 2, max].map(v => <g key={v}><path className="sensor-chart-grid" d={`M40 ${y(v)}H520`} /><text x="32" y={y(v) + 4} textAnchor="end">{motion ? v === 1 ? 'HIGH' : v === 0 ? 'LOW' : '' : v}</text></g>)}
    {!motion && <path className="sensor-chart-threshold" d={`M40 ${y(80)}H520`} />}
    <path className="sensor-chart-line" d={path} />{valid.length > 0 && <circle cx={x(valid.at(-1).received_epoch)} cy={y(valid.at(-1)[key])} r="3" className="sensor-chart-dot" />}
    {!valid.length && <text x="280" y="78" textAnchor="middle">Waiting for {motion ? 'motion' : 'valid distance'} samples</text>}
    <text x="40" y="150">60s ago</text><text x="520" y="150" textAnchor="end">Now</text>
  </svg>
}
function cameraState(snapshot, live) { return !live ? 'Not reported' : snapshot.camera_state || (typeof snapshot.camera_ready === 'boolean' ? snapshot.camera_ready ? 'Ready' : 'Not ready' : 'Not reported') }

export function HardwareSignals({ hardware, onNavigate }) {
  const { snapshot: s, live } = hardware
  return <section className="panel overview-hardware"><SectionHeading eyebrow="THE PHYSICAL LAYER" title="Hardware signals" action={<Badge state={live ? 'online' : 'offline'}>{live ? 'Online' : 'Offline'}</Badge>} />
    <div className="hardware-overview-grid"><div><dl><InfoRow label="PIR motion">{live ? s.pir ? 'MOTION' : 'CLEAR' : 'Not reported'}</InfoRow><InfoRow label="Ultrasonic distance">{live ? s.distance_cm == null ? 'Invalid / no echo' : `${s.distance_cm.toFixed(1)} cm` : 'Not reported'}</InfoRow><InfoRow label="ESP32-CAM readiness">{cameraState(s, live)}</InfoRow></dl></div><div><SensorChart samples={s.history} compact /><p className="chart-caption">Received distance samples · last 60 seconds</p></div></div>
    <div className="hardware-summary-footer"><span>{s.device_id || 'No connection source'}<small>Last sample: {s.received_at ? formatClock(s.received_at) : 'Not received'}</small></span><button className="text-button" onClick={() => onNavigate('hardware')}>Connect your hardware <ArrowUpRight size={15} /></button></div>
  </section>
}

export default function HardwarePage({ hardware }) {
  const { snapshot: s, live, ports, refreshPorts, action, busy, portsBusy, error } = hardware
  const [port, setPort] = useState(''), [baud, setBaud] = useState(115200)
  useEffect(() => { refreshPorts() }, [refreshPorts])
  const connected = Boolean(s.serial?.connected)
  const effectivePort = connected ? s.serial.port : port
  return <>
    <section className="panel hardware-connect"><SectionHeading eyebrow="USB SERIAL · READ ONLY" title="Connect the main ESP32" action={<Badge state={live ? 'online' : 'offline'}>{live ? 'Online · fresh samples' : connected ? 'Offline · waiting for samples' : 'Offline'}</Badge>}>Read the existing controller logs. No trigger commands are sent.</SectionHeading>
      <div className="hardware-controls"><label>USB COM port<select value={effectivePort || ''} disabled={busy || connected} onChange={e => setPort(e.target.value)}><option value="">Select your ESP32 port</option>{ports.map(p => <option value={p.port} key={p.port}>{p.port} · {p.description}</option>)}{connected && !ports.some(p => p.port === effectivePort) && <option value={effectivePort}>{effectivePort}</option>}</select></label><label>Baud rate<select value={connected ? s.serial.baudrate : baud} disabled={busy || connected} onChange={e => setBaud(Number(e.target.value))}>{[115200, 9600, 57600, 230400, 460800, 921600].map(n => <option key={n}>{n}</option>)}</select></label><button className="button hardware-secondary" disabled={portsBusy || busy} onClick={refreshPorts}><RefreshCw size={14} />{portsBusy ? 'Refreshing…' : 'Refresh ports'}</button><button className="button button--primary" disabled={busy || connected || !port} onClick={() => action('connect', { port, baudrate: baud })}><Plug size={14} />Connect USB</button><button className="button hardware-secondary" disabled={busy || !connected} onClick={() => action('disconnect')}><Unplug size={14} />Disconnect</button></div>
      <div className="hardware-instruction"><CircleAlert size={17} /><p>Close Arduino <strong>Serial Monitor and Serial Plotter</strong> before connecting. Opening a port alone does not mean readings are arriving. Disconnect here before reopening Serial Monitor.</p></div>
      {(error || s.fetchError || s.serial?.error) && <div className="frame-error" role="status">{error || s.fetchError || s.serial.error}</div>}
      <div className="hardware-session" role="status"><span>{connected ? `${s.serial.port} · ${s.serial.baudrate} baud · ${s.serial.samples_received || 0} sensor samples` : ports.length ? 'Choose the main ESP32 port to start reading.' : 'No ports detected. Connect a USB data cable and refresh.'}</span><span>{s.device_id || 'Source not reported'}</span></div>
    </section>
    <div className="hardware-readings">{[
      ['PIR motion', live ? s.pir ? 'MOTION' : 'CLEAR' : '—', 'Actual infrared motion signal', Activity],
      ['Distance', live ? s.distance_cm == null ? 'NO ECHO' : `${s.distance_cm.toFixed(1)} cm` : '—', live && s.distance_cm == null ? 'Invalid distance, not zero centimetres' : 'Received ultrasonic measurement', Wifi],
      ['Agreement', live && s.agreement != null ? `${s.agreement}/${s.agreement_required}` : '—', 'Consecutive matching samples', Cpu],
      ['Controller', live ? s.controller_state || 'Not reported' : '—', 'Explicitly reported state', Clock3],
    ].map(([label, value, note, Icon]) => <div className="panel hardware-reading" key={label}><span>{label}<Icon size={16} /></span><strong>{value}</strong><small>{note}</small></div>)}</div>
    <div className="hardware-charts"><section className="panel"><SectionHeading title="Distance over time">Last 60 seconds · centimetres · dashed line marks 80 cm</SectionHeading><SensorChart samples={s.history} /></section><section className="panel"><SectionHeading title="Motion activity">Last 60 seconds · received PIR state</SectionHeading><SensorChart samples={s.history} motion /></section></div>
    <section className="panel hardware-reported"><SectionHeading title="What the board actually reports">Camera and buzzer states are never inferred from a trigger pulse.</SectionHeading><dl><InfoRow label="Connection source">{s.device_id || 'Not reported'}</InfoRow><InfoRow label="Last sample">{s.received_at ? `${formatClock(s.received_at)}${live ? '' : ' · stale / offline'}` : 'Not received'}</InfoRow><InfoRow label="Camera readiness">{cameraState(s, live)}</InfoRow><InfoRow label="Buzzer state">{live && typeof s.buzzer_active === 'boolean' ? s.buzzer_active ? 'Active' : 'Inactive' : 'Not reported'}</InfoRow></dl></section>
    <section className="panel hardware-wiring"><SectionHeading eyebrow="MATCH YOUR FIRMWARE" title="Direct-trigger wiring reference">Alternative firmware branches use different pins. Follow the matching sketch and guide.</SectionHeading><dl>{[['PIR output', 'Main ESP32 GPIO13'], ['Ultrasonic TRIG', 'Main GPIO5'], ['Ultrasonic ECHO', 'Voltage-divider tap → main GPIO18'], ['Camera trigger', 'Main GPIO19 → ESP32-CAM GPIO13'], ['Common ground', 'Main ESP32 GND ↔ camera GND ↔ sensor grounds'], ['Trigger pull-down', 'Trigger node → resistor → GND. A branch to ground, never in series between the GPIOs.']].map(([label, value]) => <InfoRow key={label} label={label}>{value}</InfoRow>)}</dl><div className="hardware-instruction"><CircleAlert size={17} /><p>Never connect a 5 V ECHO output directly to an ESP32 GPIO. GPIO19 activity does not confirm camera capture or upload. Some USB adapters reset the board when a serial port opens.</p></div></section>
  </>
}
