import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Import order matters: design-system-v2.css carries the @layer order
// declaration and must be parsed first. Everything after it slots into a
// named layer, so source order stops deciding precedence.
import './design-system-v2.css'
import './styles/tokens.css'
import './styles/material.css'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)