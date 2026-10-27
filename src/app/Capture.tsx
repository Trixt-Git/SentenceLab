// Quick capture: what were you trying to do, and optionally the line you tried. It goes to the inbox and nothing
// else happens. Turning an item into a card is authoring work for the full build.
import { useEffect, useState } from 'react';
import type { InboxItem } from '../data/types';
import { store } from './services';

export function Capture({ onHome }: { onHome: () => void }) {
  const [intent, setIntent] = useState('');
  const [attempt, setAttempt] = useState('');
  const [items, setItems] = useState<InboxItem[]>([]);
  const [saved, setSaved] = useState(false);

  const load = () => store.inbox().then((all) => setItems([...all].reverse()));
  useEffect(() => {
    void load();
  }, []);

  const save = async () => {
    if (!intent.trim()) return;
    await store.addInbox({
      at: Date.now(),
      intent: intent.trim(),
      ...(attempt.trim() ? { attempt: attempt.trim() } : {}),
      status: 'new',
    });
    setIntent('');
    setAttempt('');
    setSaved(true);
    await load();
  };

  return (
    <main className="page narrow stack">
      <h1>Capture a freeze</h1>
      <p className="muted">Two things only. It goes to the inbox; nothing else happens.</p>
      <label className="stack">
        <span>What were you trying to do?</span>
        <textarea
          rows={2}
          value={intent}
          onChange={(e) => {
            setIntent(e.target.value);
            setSaved(false);
          }}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border)', borderRadius: 8, background: 'var(--bg)' }}
        />
      </label>
      <label className="stack">
        <span>
          The line you tried <span className="muted">(optional)</span>
        </span>
        <input
          className="fill"
          value={attempt}
          autoComplete="off"
          spellCheck={false}
          onChange={(e) => setAttempt(e.target.value)}
        />
      </label>
      <div className="row">
        <button className="primary" disabled={!intent.trim()} onClick={() => void save()}>
          Save to inbox
        </button>
        <button onClick={onHome}>Home</button>
        {saved && <span role="status">Saved.</span>}
      </div>
      {items.length > 0 && (
        <section aria-label="Inbox">
          <h2>Inbox</h2>
          <ul>
            {items.map((i) => (
              <li key={i.id}>
                {i.intent}
                {i.attempt && (
                  <>
                    {' '}
                    <code>{i.attempt}</code>
                  </>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
