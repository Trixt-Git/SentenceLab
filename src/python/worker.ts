// Dedicated Web Worker: loads Pyodide and python/checker.py (unchanged, shipped as raw text) and answers
// the typed messages in protocol.ts. Packages load lazily, the first time a request's code imports them.
import checkerSource from '../../python/checker.py?raw';
import glueSource from './glue.py?raw';
import type { Request, WorkerIn, WorkerOut } from './protocol';

export const PYODIDE_VERSION = '314.0.7';
const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

interface PyodideLike {
  FS: { writeFile(path: string, data: string): void };
  runPython(code: string): unknown;
  loadPackagesFromImports(code: string): Promise<void>;
}

type Call = (name: string, payload: string) => string;

const post = (m: WorkerOut) => (self as unknown as { postMessage(m: WorkerOut): void }).postMessage(m);

let ready: Promise<{ py: PyodideLike; call: Call }> | null = null;

function boot() {
  ready ??= (async () => {
    const { loadPyodide } = await import(/* @vite-ignore */ `${PYODIDE_URL}pyodide.mjs`);
    const py: PyodideLike = await loadPyodide({ indexURL: PYODIDE_URL });
    py.FS.writeFile('/home/pyodide/checker.py', checkerSource);
    py.FS.writeFile('/home/pyodide/glue.py', glueSource);
    const call = py.runPython('import glue\nglue.call') as Call;
    return { py, call };
  })();
  return ready;
}

// Each snippet is scanned on its own: one with a syntax error must not hide the imports in the others.
function snippetsOf(req: Request): string[] {
  switch (req.type) {
    case 'check':
      return [...req.setups, req.reference, req.answer];
    case 'validate':
      return [...req.setups, req.reference, ...req.traps];
    case 'bench':
      return [req.setup, req.line];
    case 'effects':
      return [req.setup, req.reference];
    case 'parts':
    case 'blank':
      return [];
  }
}

// A Python traceback ends with the error line ("ValueError: ..."); that is the part worth showing.
const lastLine = (s: string) => s.trim().split('\n').pop() ?? s;

async function handle(msg: WorkerIn): Promise<void> {
  const { id, ...req } = msg;
  try {
    post({ id, type: 'status', phase: 'loading' });
    const { py, call } = await boot();
    // Loads numpy / pandas / scikit-learn only when some code in this request imports them.
    for (const code of snippetsOf(req as Request)) await py.loadPackagesFromImports(code);
    post({ id, type: 'status', phase: 'running' });
    const json = call(req.type, JSON.stringify(req));
    post({ id, type: 'result', result: JSON.parse(json) });
  } catch (e) {
    post({ id, type: 'error', message: lastLine(e instanceof Error ? e.message : String(e)) });
  }
}

self.onmessage = (ev: MessageEvent<WorkerIn>) => {
  void handle(ev.data);
};
