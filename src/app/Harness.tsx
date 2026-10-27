// Phase 1 developer harness. It is not a study screen: it only exercises the Python worker
// (check, validate, parts, timeout and restart, lazy package loading) so Phase 1 can be checked by hand.
import { useMemo, useRef, useState } from 'react';
import { PythonClient } from '../python/client';

interface SeedNote {
  id: string;
  setups: string[];
  reference: string;
  traps: string[];
  options?: { ignore_order?: boolean };
}

const decks = import.meta.glob<{ notes: SeedNote[] }>('../../content/decks/*.json', {
  eager: true,
  import: 'default',
});
const notes = Object.values(decks).flatMap((d) => d.notes);

export function Harness() {
  const [phase, setPhase] = useState('idle');
  const [restarts, setRestarts] = useState(0);
  const client = useRef<PythonClient | null>(null);
  client.current ??= new PythonClient({
    onPhase: setPhase,
    onRestart: () => setRestarts((n) => n + 1),
  });

  const [noteId, setNoteId] = useState(notes[0]?.id ?? '');
  const note = useMemo(() => notes.find((n) => n.id === noteId), [noteId]);
  const [answer, setAnswer] = useState('');
  const [out, setOut] = useState('');

  const run = async (label: string, job: () => Promise<unknown>) => {
    setOut(`${label}…`);
    try {
      setOut(JSON.stringify(await job(), null, 2));
    } catch (e) {
      setOut(`${label} failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  return (
    <main style={{ maxWidth: 760, margin: '2rem auto', padding: '0 1rem', font: '16px system-ui' }}>
      <h1>Sentence Lab · Phase 1 harness</h1>
      <p>
        Python: <strong>{phase === 'loading' ? 'Loading Python…' : phase}</strong> · worker restarts: {restarts}
      </p>
      <label>
        Note{' '}
        <select value={noteId} onChange={(e) => setNoteId(e.target.value)}>
          {notes.map((n) => (
            <option key={n.id}>{n.id}</option>
          ))}
        </select>
      </label>
      <textarea
        aria-label="Your line"
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        rows={2}
        spellCheck={false}
        autoComplete="off"
        style={{ display: 'block', width: '100%', margin: '1rem 0', font: '18px ui-monospace, monospace' }}
      />
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button
          disabled={!note}
          onClick={() =>
            note &&
            run('check', () =>
              client.current!.check({ setups: note.setups, reference: note.reference, answer, options: note.options }),
            )
          }
        >
          Check
        </button>
        <button
          disabled={!note}
          onClick={() =>
            note &&
            run('validate', () =>
              client.current!.validate({
                setups: note.setups,
                reference: note.reference,
                traps: note.traps,
                options: note.options,
              }),
            )
          }
        >
          Validate note
        </button>
        <button disabled={!answer} onClick={() => run('parts', () => client.current!.parts(answer))}>
          Parts
        </button>
        <button
          disabled={!note}
          onClick={() => {
            setAnswer('while True: pass');
            if (note)
              void run('check', () =>
                client.current!.check({ setups: note.setups, reference: note.reference, answer: 'while True: pass' }),
              );
          }}
        >
          Run an endless line
        </button>
        <button onClick={() => client.current!.restart()}>Restart worker</button>
      </div>
      <pre aria-live="polite" style={{ whiteSpace: 'pre-wrap' }}>
        {out}
      </pre>
    </main>
  );
}
