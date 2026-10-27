// The one-line input: CodeMirror 6 with Python syntax colour and nothing else. No autocomplete, no snippets, no
// bracket closing: any of those would write part of the line for the learner (ARCHITECTURE.md section 10, 12).
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
import { python } from '@codemirror/lang-python';
import { defaultHighlightStyle, syntaxHighlighting } from '@codemirror/language';
import { Compartment, EditorState, Prec, StateEffect, StateField } from '@codemirror/state';
import { Decoration, EditorView, keymap, type DecorationSet } from '@codemirror/view';
import { useEffect, useRef } from 'react';

const setMark = StateEffect.define<number | null>();

/** Marks one character, used to point at the column a syntax error was found. */
const markField = StateField.define<DecorationSet>({
  create: () => Decoration.none,
  update(deco, tr) {
    deco = deco.map(tr.changes);
    for (const e of tr.effects) {
      if (!e.is(setMark)) continue;
      if (e.value === null || tr.state.doc.length === 0) return Decoration.none;
      const from = Math.min(Math.max(e.value - 1, 0), tr.state.doc.length - 1);
      return Decoration.set([Decoration.mark({ class: 'cm-error-mark' }).range(from, from + 1)]);
    }
    return tr.docChanged ? Decoration.none : deco;
  },
  provide: (f) => EditorView.decorations.from(f),
});

interface Props {
  initial?: string;
  locked: boolean;
  /** 1-based column to mark (from the checker's "col N"), or null. */
  mark?: number | null;
  label: string;
  onFirstKey: () => void;
  onChange: (text: string) => void;
  /** Enter checks as sure, Shift+Enter as unsure. */
  onSubmit: (sure: boolean) => void;
  /** `?` on an empty line means stuck. */
  onStuck?: () => void;
}

export function LineEditor({ initial = '', locked, mark = null, label, onFirstKey, onChange, onSubmit, onStuck }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  const lock = useRef(new Compartment());
  const cb = useRef({ onFirstKey, onChange, onSubmit, onStuck });
  cb.current = { onFirstKey, onChange, onSubmit, onStuck };

  useEffect(() => {
    let typed = false;
    const v = new EditorView({
      parent: host.current!,
      state: EditorState.create({
        doc: initial,
        extensions: [
          python(),
          syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
          history(),
          markField,
          lock.current.of([EditorView.editable.of(!locked), EditorState.readOnly.of(locked)]),
          EditorView.contentAttributes.of({
            'aria-label': label,
            autocapitalize: 'off',
            autocorrect: 'off',
            spellcheck: 'false',
          }),
          // One line only: refuse any change that would add a line break.
          EditorState.transactionFilter.of((tr) => (tr.newDoc.lines > 1 ? [] : tr)),
          Prec.highest(
            keymap.of([
              { key: 'Enter', run: () => (cb.current.onSubmit(true), true) },
              { key: 'Shift-Enter', run: () => (cb.current.onSubmit(false), true) },
              {
                key: '?',
                run: (ev) => {
                  if (ev.state.doc.length > 0 || !cb.current.onStuck) return false;
                  cb.current.onStuck();
                  return true;
                },
              },
            ]),
          ),
          keymap.of([...defaultKeymap, ...historyKeymap]),
          EditorView.updateListener.of((u) => {
            if (!u.docChanged) return;
            if (!typed) {
              typed = true;
              cb.current.onFirstKey();
            }
            cb.current.onChange(u.state.doc.toString());
          }),
        ],
      }),
    });
    view.current = v;
    cb.current.onChange(initial);
    if (!locked) v.focus();
    return () => v.destroy();
    // The editor is created once per mount; the parent remounts it (by key) for each new line.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const v = view.current;
    if (!v) return;
    v.dispatch({
      effects: lock.current.reconfigure([EditorView.editable.of(!locked), EditorState.readOnly.of(locked)]),
    });
    if (!locked) v.focus();
  }, [locked]);

  useEffect(() => {
    view.current?.dispatch({ effects: setMark.of(mark) });
  }, [mark]);

  return <div ref={host} className={`line${locked ? ' locked' : ''}`} />;
}
