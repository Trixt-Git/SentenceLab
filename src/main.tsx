import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './app/App';
import { Harness } from './app/Harness';
import './styles/tokens.css';

// `#harness` opens the Phase 1 developer page (check, validate, parts, timeout and restart by hand).
const dev = window.location.hash === '#harness';

createRoot(document.getElementById('root')!).render(<StrictMode>{dev ? <Harness /> : <App />}</StrictMode>);
