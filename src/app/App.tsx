// Home, Review, summary, capture and the cold challenge. A route is a tiny state machine; there is no URL routing.
import { useEffect, useState } from 'react';
import { Review } from '../review/Review';
import { ColdRun } from '../review/ColdRun';
import { SessionSummary } from '../review/SessionSummary';
import { ColdChallenge, coldOffer } from '../pilot/cold';
import { Engine } from '../pilot/engine';
import type { ColdScore, Summary } from '../pilot/measures';
import { Capture } from './Capture';
import { boot, python, store } from './services';

type Route =
  | { r: 'home'; notice?: string }
  | { r: 'review'; engine: Engine }
  | { r: 'summary'; summary: Summary }
  | { r: 'capture' }
  | { r: 'cold'; challenge: ColdChallenge }
  | { r: 'cold-done'; score: ColdScore };

const deps = () => ({ store, python, now: () => new Date(), rng: Math.random });

export function App() {
  const [route, setRoute] = useState<Route>({ r: 'home' });
  const [ready, setReady] = useState(false);
  const [offer, setOffer] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    boot().then(
      () => setReady(true),
      (e) => setError(String(e)),
    );
  }, []);

  useEffect(() => {
    if (ready && route.r === 'home') void coldOffer(store, new Date()).then(setOffer);
  }, [ready, route.r]);

  const home = () => setRoute({ r: 'home' });

  const startSession = async () => {
    python.restart(); // a clean interpreter at the start of every session (section 8)
    const engine = await Engine.create(deps());
    if (engine.cardsLeft === 0) return setRoute({ r: 'home', notice: 'Nothing to study right now. Come back later.' });
    setRoute({ r: 'review', engine });
  };

  const startCold = async () => {
    python.restart();
    setRoute({ r: 'cold', challenge: await ColdChallenge.create(deps()) });
  };

  switch (route.r) {
    case 'review':
      return <Review engine={route.engine} onFinish={(summary) => setRoute({ r: 'summary', summary })} />;
    case 'summary':
      return <SessionSummary summary={route.summary} onAgain={() => void startSession()} onHome={home} />;
    case 'capture':
      return <Capture onHome={home} />;
    case 'cold':
      return <ColdRun challenge={route.challenge} onDone={(score) => setRoute({ r: 'cold-done', score })} />;
    case 'cold-done':
      return (
        <main className="page narrow stack">
          <h1>Cold challenge</h1>
          <p>
            {route.score.correct} of {route.score.total} right, with no help.
          </p>
          <button className="primary" onClick={home}>
            Home
          </button>
        </main>
      );
    default:
      return (
        <main className="page narrow stack">
          <h1>Sentence Lab</h1>
          {error && <p className="err" role="alert">{error}</p>}
          {route.notice && <p role="status">{route.notice}</p>}
          <div className="stack">
            <button className="primary" disabled={!ready} onClick={() => void startSession()}>
              Start session
            </button>
            <div>
              <button disabled={!ready} onClick={() => setRoute({ r: 'capture' })}>
                Capture a freeze
              </button>
            </div>
            {offer && (
              <div>
                <button onClick={() => void startCold()}>Take this week's cold challenge</button>
                <p className="muted">Optional. New lines, no help.</p>
              </div>
            )}
          </div>
        </main>
      );
  }
}
