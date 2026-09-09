import './index.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { KeycloakProvider } from './components/KeycloakProvider'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <KeycloakProvider>
      <App />
    </KeycloakProvider>
  </StrictMode>,
)
