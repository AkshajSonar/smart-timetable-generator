import { useEffect, useState, ReactNode } from 'react';
import Keycloak from 'keycloak-js';
import { setBearerToken } from '../api/client';

const keycloak = new Keycloak({
  url: 'http://localhost:8080',
  realm: 'timetable',
  clientId: 'timetable-web'
});

interface KeycloakProviderProps {
  children: ReactNode;
}

export function KeycloakProvider({ children }: KeycloakProviderProps) {
  const [authenticated, setAuthenticated] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    // Only initialize once
    if (keycloak.didInitialize) return;

    keycloak
      .init({
        onLoad: 'login-required',
        pkceMethod: 'S256',
        checkLoginIframe: false,
      })
      .then((auth) => {
        setAuthenticated(auth);
        if (auth && keycloak.token) {
          setBearerToken(keycloak.token);
        }
        setLoading(false);

        // Schedule token refresh
        const refreshInterval = setInterval(() => {
          keycloak
            .updateToken(70)
            .then((refreshed) => {
              if (refreshed && keycloak.token) {
                setBearerToken(keycloak.token);
              }
            })
            .catch(() => {
              keycloak.login();
            });
        }, 60000); // Check every minute

        return () => clearInterval(refreshInterval);
      })
      .catch((err) => {
        console.error('Failed to initialize Keycloak', err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-white">Authenticating...</div>
      </div>
    );
  }

  if (!authenticated) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-white text-center">
          <p className="mb-4">Unable to authenticate.</p>
          <button
            onClick={() => keycloak.login()}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Retry Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="absolute top-4 right-4 text-sm text-slate-400">
        Logged in as: {keycloak.tokenParsed?.preferred_username || 'User'}
        <button
          onClick={() => keycloak.logout()}
          className="ml-4 hover:text-white underline"
        >
          Logout
        </button>
      </div>
      {children}
    </>
  );
}
