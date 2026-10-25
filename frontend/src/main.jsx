import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import '@fontsource-variable/inter'
import './styles/sentinel.css'
import './styles/hardware.css'
import './styles/overview-alignment.css'

createRoot(document.getElementById('root')).render(<App />)
