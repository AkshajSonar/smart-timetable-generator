import './index.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { GeneratePage } from './pages/GeneratePage'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <GeneratePage />
  </StrictMode>,
)
