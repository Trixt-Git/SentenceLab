// Four large toggles: what should this line change? Used as the effect gate (before typing) and as the effect
// prompt (after a miss). "Nothing changes" clears the others, and picking any other clears "Nothing changes".
import { useEffect } from 'react';
import type { EffectName } from '../pilot/engine';

const CHOICES: { key: EffectName; label: string }[] = [
  { key: 'rebinds', label: 'Rebinds a name' },
  { key: 'mutates', label: 'Mutates an object' },
  { key: 'sends_out', label: 'Sends out' },
  { key: 'nothing', label: 'Nothing changes' },
];

export const effectLabel = (e: string) => CHOICES.find((c) => c.key === e)?.label ?? e;

export function toggle(current: EffectName[], key: EffectName): EffectName[] {
  if (key === 'nothing') return current.includes('nothing') ? [] : ['nothing'];
  const without = current.filter((x) => x !== 'nothing');
  return without.includes(key) ? without.filter((x) => x !== key) : [...without, key];
}

interface Props {
  question: string;
  value: EffectName[];
  onChange: (v: EffectName[]) => void;
  onConfirm: () => void;
  /** Keys 1–4 toggle and Enter confirms, while the gate is the thing waiting for the learner. */
  active: boolean;
}

export function EffectGate({ question, value, onChange, onConfirm, active }: Props) {
  useEffect(() => {
    if (!active) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      const i = Number(e.key) - 1;
      if (i >= 0 && i < CHOICES.length) {
        e.preventDefault();
        onChange(toggle(value, CHOICES[i].key));
      } else if (e.key === 'Enter' && value.length > 0) {
        e.preventDefault();
        onConfirm();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [active, value, onChange, onConfirm]);

  return (
    <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
      <legend style={{ fontWeight: 600 }}>{question}</legend>
      <div className="gate" role="group" aria-label={question}>
        {CHOICES.map((c, i) => (
          <button key={c.key} type="button" aria-pressed={value.includes(c.key)} onClick={() => onChange(toggle(value, c.key))}>
            <kbd>{i + 1}</kbd> {c.label}
          </button>
        ))}
      </div>
      <button type="button" className="primary" disabled={value.length === 0} onClick={onConfirm}>
        Confirm <kbd>Enter</kbd>
      </button>
    </fieldset>
  );
}
