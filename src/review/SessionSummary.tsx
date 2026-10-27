// Shown when a session ends. Information only: no score, no target, no comparison with earlier days.
import type { Summary } from '../pilot/measures';

export function SessionSummary({ summary, onAgain, onHome }: { summary: Summary; onAgain: () => void; onHome: () => void }) {
  const s = summary;
  return (
    <main className="page narrow stack">
      <h1>Session summary</h1>
      <dl className="summary">
        <dt>Lines attempted</dt>
        <dd>{s.linesAttempted}</dd>
        <dt>Right on the first try</dt>
        <dd>
          {s.firstTryCorrect} of {s.linesAttempted}
        </dd>
        <dt>Median time to first keystroke</dt>
        <dd>{s.medianSecondsToFirstKey === null ? 'no keystrokes recorded' : `${s.medianSecondsToFirstKey} seconds`}</dd>
        <dt>Missed most</dt>
        <dd>{s.missedMost ?? 'nothing missed'}</dd>
        <dt>Stuck presses</dt>
        <dd>
          Didn't know what to use: {s.stuck.verb} · Couldn't write it: {s.stuck.assemble} · Unsure what should change:{' '}
          {s.stuck.effect}
        </dd>
      </dl>
      <div className="row">
        <button className="primary" onClick={onAgain}>
          Start another session
        </button>
        <button onClick={onHome}>Home</button>
      </div>
    </main>
  );
}
