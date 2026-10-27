// One card at a time: intent (or notebook cell), the bench, the effect gate, the one-line input and the feedback.
// All decisions (checking, logging, scheduling, which help follows a miss) come from the engine; this file renders
// them. Nothing about the answer is shown before Check, and there are no rating buttons.
import { useCallback, useEffect, useRef, useState } from 'react';
import { Bench } from '../bench/Bench';
import { usePythonPhase } from '../app/services';
import type { Engine, Card, EffectName, L5Outcome } from '../pilot/engine';
import { effectWords } from '../pilot/engine';
import type { Summary } from '../pilot/measures';
import type { Help } from '../pilot/routing';
import type { BenchResult, BenchState, BlankResult, CheckResult } from '../python/protocol';
import type { StuckReason } from '../data/types';
import { EffectGate, effectLabel } from './EffectGate';
import { LineEditor } from './LineEditor';

type Step =
  | { t: 'busy' }
  | { t: 'gate'; next: 'l5' | 'l4' }
  | { t: 'l5'; banner?: string; mark?: number | null }
  | { t: 'why' }
  | { t: 'prompt'; then: 'l4-verb' | 'l5'; result?: { correct: boolean; words: string[]; picked: EffectName[] } }
  | { t: 'l4'; blank: BlankResult }
  | { t: 'l4result'; result: CheckResult; filled: string }
  | { t: 'result'; out: L5Outcome; answer: string; bench: BenchResult | null; sure: boolean }
  | { t: 'ended'; reveal: string };

const REASONS: { key: StuckReason; label: string }[] = [
  { key: 'verb', label: "I don't know what to use" },
  { key: 'assemble', label: "I know what to use but can't write it" },
  { key: 'effect', label: "I'm not sure what should change" },
];

const isTyping = (t: EventTarget | null) =>
  t instanceof HTMLInputElement || t instanceof HTMLTextAreaElement || (t instanceof HTMLElement && t.isContentEditable);

export function Review({ engine, onFinish }: { engine: Engine; onFinish: (s: Summary) => void }) {
  const phase = usePythonPhase();
  const [card, setCard] = useState<Card | null>(null);
  const [step, setStep] = useState<Step>({ t: 'busy' });
  const [before, setBefore] = useState<BenchState | null>(null);
  const [text, setText] = useState('');
  const [editorInitial, setEditorInitial] = useState('');
  const [editorKey, setEditorKey] = useState(0);
  const [picked, setPicked] = useState<EffectName[]>([]);
  const [confirmed, setConfirmed] = useState<EffectName[] | null>(null);
  const [fill, setFill] = useState('');
  const [revealed, setRevealed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const shownAt = useRef(0);
  const firstKey = useRef<number | null>(null);
  const started = useRef(false);

  const timing = () => ({
    msToFirstKey: firstKey.current === null ? null : Math.round(firstKey.current - shownAt.current),
    msToAnswer: Math.round(performance.now() - shownAt.current),
  });

  const guard = async (job: () => Promise<void>) => {
    try {
      setError(null);
      await job();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStep({ t: 'busy' });
    }
  };

  const loadNext = useCallback(
    () =>
      guard(async () => {
        setStep({ t: 'busy' });
        setBefore(null);
        const c = await engine.nextCard();
        if (!c) return onFinish(engine.summary());
        setCard(c);
        setPicked([]);
        setConfirmed(null);
        setText('');
        setEditorInitial('');
        setFill('');
        setRevealed(false);
        setEditorKey((k) => k + 1);
        shownAt.current = performance.now();
        firstKey.current = null;
        setStep(c.gate ? { t: 'gate', next: 'l5' } : { t: 'l5' });
        engine.benchBefore(c).then(setBefore, (e) => setError(String(e)));
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [engine, onFinish],
  );

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void loadNext();
  }, [loadNext]);

  const confirmGate = () => {
    if (!card || picked.length === 0) return;
    setConfirmed(picked);
    setStep((s) => (s.t === 'gate' ? (s.next === 'l4' ? s : { t: 'l5' }) : s));
  };

  const submit = (sure: boolean) =>
    guard(async () => {
      if (!card || step.t !== 'l5') return;
      const answer = text.trim();
      const t = timing();
      setStep({ t: 'busy' });
      const out = await engine.submitL5(card, { answer, effectPicked: confirmed, sure, ...t });
      // A line that timed out would hang the bench too, and a syntax error has nothing to run.
      const showBench =
        !out.noteError &&
        !out.result.timedOut &&
        out.result.blame !== 'assemble' &&
        (out.result.correct ? !card.fluent : true) &&
        answer !== '';
      const bench = showBench ? await engine.benchFor(card, answer, out.result.setup_index).catch(() => null) : null;
      setStep({ t: 'result', out, answer, bench, sure });
    });

  const explain = () =>
    guard(async () => {
      if (!card || step.t !== 'result' || step.bench) return;
      const bench = await engine.benchFor(card, step.answer, step.out.result.setup_index).catch(() => null);
      setStep({ ...step, bench });
    });

  const startFix = (r: Extract<Step, { t: 'result' }>) => {
    const m = /col (\d+)/.exec(r.out.result.messages[0] ?? '');
    setEditorInitial(r.answer);
    setText(r.answer);
    setEditorKey((k) => k + 1);
    setStep({ t: 'l5', banner: r.out.result.messages[0], mark: m ? Number(m[1]) : null });
  };

  const openL4 = (part: Parameters<Engine['openL4']>[1]) =>
    guard(async () => {
      if (!card) return;
      setStep({ t: 'busy' });
      const blank = await engine.openL4(card, part);
      setFill('');
      if (!blank) return setStep({ t: 'ended', reveal: '' });
      setStep({ t: 'l4', blank });
    });

  const followHelp = (help: Help) => {
    if (help.kind === 'l4') return openL4(help.part);
    if (help.kind === 'effect-prompt') {
      setPicked([]);
      return setStep({ t: 'prompt', then: help.then });
    }
    if (help.kind === 'verb-hint') return;
    return loadNext();
  };

  const chooseWhy = (reason: StuckReason) =>
    guard(async () => {
      if (!card) return;
      const res = await engine.stuck(card, reason, timing());
      if (res.reveal) return setStep({ t: 'ended', reveal: res.reveal });
      if (res.help.kind === 'verb-hint') {
        const banner = await engine.verbHint(card);
        setEditorInitial('');
        setText('');
        setEditorKey((k) => k + 1);
        return setStep({ t: 'l5', banner });
      }
      return followHelp(res.help);
    });

  const answerPrompt = () =>
    guard(async () => {
      if (!card || step.t !== 'prompt') return;
      const res = await engine.effectPrompt(card, picked);
      setStep({ ...step, result: { correct: res.effectCorrect, words: res.words, picked } });
    });

  const afterPrompt = () => {
    if (step.t !== 'prompt') return;
    if (step.then === 'l4-verb') return openL4('verb');
    setEditorInitial('');
    setText('');
    setEditorKey((k) => k + 1);
    setStep({ t: 'l5' });
  };

  const submitL4 = () =>
    guard(async () => {
      if (!card || step.t !== 'l4') return;
      const { result, filled } = await engine.submitL4(card, step.blank, fill, timing(), confirmed);
      setStep({ t: 'l4result', result, filled });
    });

  // Keys: Space continues, E explains, 1–3 answer the stuck question. 1–4 and Enter on the gate live in EffectGate.
  const keys = useRef<(e: KeyboardEvent) => void>(() => undefined);
  keys.current = (e) => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (step.t === 'why' && ['1', '2', '3'].includes(e.key)) {
      e.preventDefault();
      void chooseWhy(REASONS[Number(e.key) - 1].key);
    } else if (e.key === ' ' && !isTyping(e.target) && !(e.target instanceof HTMLButtonElement)) {
      if (step.t === 'result' && !step.out.noteError) {
        if (step.out.help.kind === 'done' || step.out.help.kind === 'end') {
          e.preventDefault();
          void loadNext();
        }
      } else if (step.t === 'l4result' || step.t === 'ended') {
        e.preventDefault();
        void loadNext();
      } else if (step.t === 'prompt' && step.result) {
        e.preventDefault();
        afterPrompt();
      }
    } else if ((e.key === 'e' || e.key === 'E') && !isTyping(e.target) && step.t === 'result' && !step.bench) {
      e.preventDefault();
      void explain();
    } else if (e.key === '?' && !isTyping(e.target) && (step.t === 'l5' || step.t === 'gate')) {
      e.preventDefault();
      setStep({ t: 'why' });
    }
  };
  useEffect(() => {
    const on = (e: KeyboardEvent) => keys.current(e);
    window.addEventListener('keydown', on);
    return () => window.removeEventListener('keydown', on);
  }, []);

  if (!card) {
    return (
      <main className="page">
        {error ? <p className="err">{error}</p> : <p className="muted">{phase === 'loading' ? 'Loading Python…' : 'Getting your cards…'}</p>}
      </main>
    );
  }

  const intent = card.instance.intents[card.intentIndex];
  const result = step.t === 'result' ? step : null;
  const shownBench = result?.bench;
  const loading = phase === 'loading';
  const typingStep = step.t === 'l5' || step.t === 'gate' || step.t === 'busy';
  const locked = step.t !== 'l5';

  return (
    <main className="page review">
      <aside aria-label="The bench" className="bench-pair">
        <Bench
          title={shownBench ? 'Before your line' : 'Before'}
          state={shownBench ? shownBench.before : before}
          loading={loading && !before}
        />
        {shownBench && <Bench title="After your line" state={shownBench.after} error={shownBench.error} />}
      </aside>

      <section aria-label="Card" className="stack">
        <div className="cards-left" aria-live="polite">
          {engine.cardsLeft + 1} {engine.cardsLeft + 1 === 1 ? 'card' : 'cards'} left
        </div>

        {card.format === 'notebook' ? (
          <pre className="cell" aria-label="Notebook cell">
            {card.instance.setups[0]}
            {'\n'}
            <span className="comment"># {intent}</span>
          </pre>
        ) : (
          <h2 className="intent">{intent}</h2>
        )}

        {error && <p className="err" role="alert">{error}</p>}

        {(step.t === 'gate' && step.next === 'l5') && (
          <EffectGate
            question="What should this line change?"
            value={picked}
            onChange={setPicked}
            onConfirm={confirmGate}
            active
          />
        )}

        {typingStep && (
          <>
            {step.t === 'l5' && step.banner && <p className="advice" role="status">{step.banner}</p>}
            <LineEditor
              key={editorKey}
              initial={editorInitial}
              locked={locked}
              mark={step.t === 'l5' ? step.mark : null}
              label={card.format === 'notebook' ? 'The line to write under the comment' : 'Your line of Python'}
              onFirstKey={() => (firstKey.current ??= performance.now())}
              onChange={setText}
              onSubmit={submit}
              onStuck={() => setStep({ t: 'why' })}
            />
            <div className="row">
              <button className="primary" disabled={locked} onClick={() => submit(true)}>
                Check <kbd>Enter</kbd>
              </button>
              <button disabled={locked} onClick={() => submit(false)}>
                Check, unsure <kbd>Shift+Enter</kbd>
              </button>
              <button onClick={() => setStep({ t: 'why' })} disabled={step.t === 'busy'}>
                I'm stuck <kbd>?</kbd>
              </button>
            </div>
          </>
        )}

        {step.t === 'why' && (
          <div role="group" aria-label="What is the trouble?" className="stack">
            <p style={{ fontWeight: 600, margin: 0 }}>What's the trouble?</p>
            {REASONS.map((r, i) => (
              <div key={r.key}>
                <button onClick={() => chooseWhy(r.key)}>
                  <kbd>{i + 1}</kbd> {r.label}
                </button>
              </div>
            ))}
          </div>
        )}

        {step.t === 'prompt' && (
          <div className="stack">
            {!step.result ? (
              <EffectGate
                question="What should this line change?"
                value={picked}
                onChange={setPicked}
                onConfirm={answerPrompt}
                active
              />
            ) : (
              <>
                <p className="verdict">{step.result.correct ? 'Yes.' : 'Not quite.'}</p>
                <p>
                  The line {step.result.words.join(' and ')}.
                  {!step.result.correct && ` You picked: ${step.result.picked.map(effectLabel).join(', ')}.`}
                </p>
                <p className="rule">{card.pattern.rule}</p>
                <button className="primary" onClick={afterPrompt}>
                  {step.then === 'l4-verb' ? 'Fill the blank' : 'Try writing it'} <kbd>Space</kbd>
                </button>
              </>
            )}
          </div>
        )}

        {step.t === 'l4' && (
          <L4View
            card={card}
            blank={step.blank}
            fill={fill}
            setFill={setFill}
            picked={picked}
            setPicked={setPicked}
            confirmed={confirmed}
            confirm={() => setConfirmed(picked)}
            submit={submitL4}
            onFirstKey={() => (firstKey.current ??= performance.now())}
          />
        )}

        {step.t === 'l4result' && (
          <div className="feedback stack">
            <p className={`verdict ${step.result.correct ? 'good' : 'bad'}`}>{step.result.correct ? 'Correct.' : 'Not yet.'}</p>
            {!step.result.correct && step.result.messages.map((m) => <p key={m}>{m}</p>)}
            <p className="rule">{card.pattern.rule}</p>
            <p className="muted">You'll see this one again a few cards from now, written from scratch.</p>
            <button className="primary" onClick={() => loadNext()}>
              Next <kbd>Space</kbd>
            </button>
          </div>
        )}

        {step.t === 'ended' && (
          <div className="feedback stack">
            {step.reveal && (
              <>
                <p>The line was:</p>
                <pre className="reference">{step.reveal}</pre>
                <p className="rule">{card.pattern.rule}</p>
              </>
            )}
            <button className="primary" onClick={() => loadNext()}>
              Next <kbd>Space</kbd>
            </button>
          </div>
        )}

        {result && (
          <ResultView
            card={card}
            r={result}
            revealed={revealed}
            reveal={() => setRevealed(true)}
            next={() => loadNext()}
            explain={explain}
            fix={() => startFix(result)}
            follow={followHelp}
          />
        )}
      </section>
    </main>
  );
}

function ResultView({
  card,
  r,
  revealed,
  reveal,
  next,
  explain,
  fix,
  follow,
}: {
  card: Card;
  r: Extract<Step, { t: 'result' }>;
  revealed: boolean;
  reveal: () => void;
  next: () => void;
  explain: () => void;
  fix: () => void;
  follow: (h: Help) => void;
}) {
  const { out } = r;
  const res = out.result;

  if (out.noteError) {
    return (
      <div className="feedback stack">
        <p className="verdict bad">This card has a problem. It isn't your miss, so nothing was recorded.</p>
        {res.messages.map((m) => <p key={m}>{m}</p>)}
        <button className="primary" onClick={next}>Skip this card</button>
      </div>
    );
  }

  // A correct line is graded on its own effects (it may reach the result another way); a miss on the reference's.
  const pickHint =
    out.effectCorrect === false
      ? res.correct && res.effects
        ? `Effect pick: your line ${res.effects.yours.map((e) => effectLabel(e).toLowerCase()).join(' and ')}.`
        : `Effect pick: this line ${effectWords(card.refEffects).join(' and ')}.`
      : null;

  if (res.correct) {
    return (
      <div className="feedback stack">
        <p className="verdict good">Correct.</p>
        {(res.style ?? []).map((s) => <p key={s} className="advice">{s}</p>)}
        {pickHint && <p>{pickHint}</p>}
        {out.reveal && (
          <>
            <p>The reference line:</p>
            <pre className="reference">{out.reveal}</pre>
          </>
        )}
        <div className="row">
          <button className="primary" onClick={next}>Next <kbd>Space</kbd></button>
          {card.fluent && !r.bench && <button onClick={explain}>Explain <kbd>E</kbd></button>}
        </div>
      </div>
    );
  }

  const messages = res.messages.map((m) => <p key={m}>{m}</p>);
  const rule = <p className="rule" key="rule">{card.pattern.rule}</p>;
  return (
    <div className="feedback stack">
      <p className="verdict bad">Not quite.</p>
      {/* A sure-but-wrong answer gets the rule first (section 5). */}
      {r.sure ? [rule, messages] : [messages, rule]}
      {pickHint && <p>{pickHint}</p>}
      {(out.reveal || revealed) && (
        <>
          <p>The reference line:</p>
          <pre className="reference">{card.instance.reference}</pre>
        </>
      )}
      <div className="row">
        <HelpButton help={out.help} follow={follow} fix={fix} next={next} />
        {!out.reveal && !revealed && <button onClick={reveal}>Show reference</button>}
      </div>
      {!out.reveal && !revealed && <p className="muted">Showing the reference counts as a miss.</p>}
    </div>
  );
}

function HelpButton({ help, follow, fix, next }: { help: Help; follow: (h: Help) => void; fix: () => void; next: () => void }) {
  switch (help.kind) {
    case 'fix':
      return <button className="primary" onClick={fix}>Fix it</button>;
    case 'l4':
      return <button className="primary" onClick={() => follow(help)}>Fill the blank</button>;
    case 'effect-prompt':
      return <button className="primary" onClick={() => follow(help)}>Think about the effect</button>;
    default:
      return <button className="primary" onClick={next}>Next <kbd>Space</kbd></button>;
  }
}

function L4View({
  card,
  blank,
  fill,
  setFill,
  picked,
  setPicked,
  confirmed,
  confirm,
  submit,
  onFirstKey,
}: {
  card: Card;
  blank: BlankResult;
  fill: string;
  setFill: (s: string) => void;
  picked: EffectName[];
  setPicked: (p: EffectName[]) => void;
  confirmed: EffectName[] | null;
  confirm: () => void;
  submit: () => void;
  onFirstKey: () => void;
}) {
  const [pre, post] = blank.blanked.split('____');
  const gated = card.gate && confirmed === null;
  return (
    <div className="stack">
      <p className="muted">One part is missing. Type it.</p>
      {gated && (
        <EffectGate question="What should this line change?" value={picked} onChange={setPicked} onConfirm={confirm} active />
      )}
      <pre className="blanked" aria-label="The line with one part blanked">
        {pre}
        <mark>____</mark>
        {post}
      </pre>
      <input
        className="fill"
        aria-label="The missing part"
        value={fill}
        disabled={gated}
        autoFocus={!gated}
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="off"
        spellCheck={false}
        onChange={(e) => {
          onFirstKey();
          setFill(e.target.value);
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            submit();
          }
        }}
      />
      <button className="primary" disabled={gated || fill.trim() === ''} onClick={submit}>
        Check <kbd>Enter</kbd>
      </button>
    </div>
  );
}
