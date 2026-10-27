// The weekly cold challenge: unseen instances of practised patterns, written from scratch. No effect gate, no help,
// no retry, no bench or diagram, nothing sent to the schedule. The checker still says what went wrong.
import { useRef, useState } from 'react';
import type { ColdChallenge } from '../pilot/cold';
import type { ColdScore } from '../pilot/measures';
import type { CheckResult } from '../python/protocol';
import { LineEditor } from './LineEditor';

export function ColdRun({ challenge, onDone }: { challenge: ColdChallenge; onDone: (s: ColdScore) => void }) {
  const [item, setItem] = useState(challenge.current);
  const [text, setText] = useState('');
  const [result, setResult] = useState<CheckResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [key, setKey] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const shownAt = useRef(performance.now());
  const firstKey = useRef<number | null>(null);

  if (!item) return <main className="page narrow"><p>Nothing to ask this week.</p><button onClick={() => challenge.finish().then(onDone)}>Home</button></main>;

  const submit = async () => {
    if (busy || result) return;
    setBusy(true);
    setError(null);
    try {
      const r = await challenge.submit(text.trim(), {
        msToFirstKey: firstKey.current === null ? null : Math.round(firstKey.current - shownAt.current),
        msToAnswer: Math.round(performance.now() - shownAt.current),
      });
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const next = async () => {
    if (challenge.advance()) {
      setItem(challenge.current);
      setText('');
      setResult(null);
      setKey((k) => k + 1);
      shownAt.current = performance.now();
      firstKey.current = null;
    } else {
      onDone(await challenge.finish());
    }
  };

  const intent = item.instance.intents[item.intentIndex];
  return (
    <main className="page narrow stack">
      <div className="cards-left">
        Cold challenge · {challenge.cardsLeft + 1} left
      </div>
      <pre className="cell" aria-label="Notebook cell">
        {item.instance.setups[0]}
        {'\n'}
        <span className="comment"># {intent}</span>
      </pre>
      <LineEditor
        key={key}
        locked={busy || result !== null}
        label="The line to write under the comment"
        onFirstKey={() => (firstKey.current ??= performance.now())}
        onChange={setText}
        onSubmit={() => void submit()}
      />
      <div className="row">
        <button className="primary" disabled={busy || result !== null} onClick={() => void submit()}>
          Check <kbd>Enter</kbd>
        </button>
      </div>
      {error && <p className="err" role="alert">{error}</p>}
      {result && (
        <div className="feedback stack">
          <p className={`verdict ${result.correct ? 'good' : 'bad'}`}>{result.correct ? 'Correct.' : 'Not quite.'}</p>
          {!result.correct && result.messages.map((m) => <p key={m}>{m}</p>)}
          {(result.style ?? []).map((s) => <p key={s} className="advice">{s}</p>)}
          <button className="primary" onClick={() => void next()}>
            {challenge.cardsLeft > 0 ? 'Next' : 'Finish'}
          </button>
        </div>
      )}
    </main>
  );
}
