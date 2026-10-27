import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Harness } from './app/Harness';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Harness />
  </StrictMode>,
);
