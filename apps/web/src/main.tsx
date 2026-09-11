import './index.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { KeycloakProvider } from './components/KeycloakProvider'
import { TenantProvider } from './lib/TenantContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <KeycloakProvider>
      <TenantProvider>
        <App />
      </TenantProvider>
    </KeycloakProvider>
  </StrictMode>,
)
