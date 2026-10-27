// The basic bench (pilot): names on the left as tags, objects on the right as boxes, an arrow between them.
// Two names on one object share one box, which is how aliasing becomes visible. No animation; a changed object
// gets an accent outline. Previews arrive as JSON from checker.bench() and are drawn here, never evaluated.
import type { BenchState, Preview } from '../python/protocol';

function scalar(p: Extract<Preview, { kind: 'scalar' }>): string {
  if (p.special) return p.special;
  if (p.value === null) return 'None';
  if (typeof p.value === 'string') return `'${p.value}'`;
  if (typeof p.value === 'boolean') return p.value ? 'True' : 'False';
  return String(p.value);
}

function Inline({ p }: { p: Preview }) {
  if (p.kind === 'scalar') return <code>{scalar(p)}</code>;
  if (p.kind === 'other') return <code>{p.text}</code>;
  return <Show p={p} />;
}

function More({ n, what }: { n: number; what: string }) {
  return n > 0 ? <span className="muted">+{n} more {what}</span> : null;
}

export function Show({ p }: { p: Preview }) {
  switch (p.kind) {
    case 'scalar':
    case 'other':
      return <Inline p={p} />;
    case 'list':
      return (
        <span className="chips">
          <code>[</code>
          {p.items.map((x, i) => (
            <span key={i} className="chip">
              <Inline p={x} />
            </span>
          ))}
          <More n={p.more} what="items" />
          <code>]</code>
        </span>
      );
    case 'dict':
      return (
        <div className="dict">
          {p.items.map((x, i) => (
            <span key={i} style={{ display: 'contents' }}>
              <span>
                <Inline p={x.key} />:
              </span>
              <span>
                <Inline p={x.value} />
              </span>
            </span>
          ))}
          <More n={p.more} what="items" />
        </div>
      );
    case 'dataframe':
      return (
        <div>
          <table>
            <thead>
              <tr>
                <th />
                {p.columns.map((c) => (
                  <th key={c}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {p.rows.map((row, r) => (
                <tr key={r}>
                  <th>
                    <Inline p={p.index[r]} />
                  </th>
                  {row.map((cell, c) => (
                    <td key={c}>
                      <Inline p={cell} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="muted">
            shape ({p.shape[0]}, {p.shape[1]}) <More n={p.more} what="rows" />
          </div>
        </div>
      );
    case 'series':
      return (
        <div>
          <table>
            <tbody>
              {p.items.map((x, i) => (
                <tr key={i}>
                  <th>
                    <Inline p={x.index} />
                  </th>
                  <td>
                    <Inline p={x.value} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="muted">
            length {p.length} <More n={p.more} what="items" />
          </div>
        </div>
      );
    case 'ndarray':
      return (
        <span className="chips">
          <span className="muted">shape ({p.shape.join(', ')})</span>
          {p.values.map((x, i) => (
            <span key={i} className="chip">
              <Inline p={x} />
            </span>
          ))}
          <More n={p.more} what="values" />
        </span>
      );
    case 'model':
      return (
        <code>
          {p.cls} · {p.fitted ? 'fitted' : 'not fitted'}
        </code>
      );
  }
}

export function Bench({
  title,
  state,
  loading,
  error,
}: {
  title: string;
  state: BenchState | null;
  loading?: boolean;
  error?: { type: string; message: string } | null;
}) {
  return (
    <section className="bench" aria-label={title}>
      <h3>{title}</h3>
      {loading || !state ? (
        <p className="muted">Loading Python…</p>
      ) : state.objects.length === 0 ? (
        <p className="muted">Nothing here yet.</p>
      ) : (
        state.objects.map((o) => (
          <div className="bench-row" key={o.key}>
            <div className="tags">
              {state.names
                .filter((n) => n.key === o.key)
                .map((n) => (
                  <span className="tag" key={n.name}>
                    {n.name}
                  </span>
                ))}
            </div>
            <span className="arrow" aria-hidden>
              →
            </span>
            <div className={`obj${o.changed ? ' changed' : ''}`}>
              <div className="obj-type">
                {o.type}
                {o.changed ? ' · changed' : ''}
              </div>
              <Show p={o.preview} />
            </div>
          </div>
        ))
      )}
      {error && (
        <p className="err">
          {error.type}: {error.message}
        </p>
      )}
    </section>
  );
}
