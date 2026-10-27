// Dedicated Web Worker: loads Pyodide and python/checker.py (unchanged, shipped as raw text) and answers
// the typed messages in protocol.ts. Packages load lazily, the first time a request's code imports them.
import checkerSource from '../../python/checker.py?raw';
import type { Request, WorkerIn, WorkerOut } from './protocol';

export const PYODIDE_VERSION = '314.0.7';
const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

// Glue only: JSON in, JSON out, so no Python object ever crosses into JS.
const GLUE = `
import json, sys
sys.path.insert(0, "/home/pyodide")
import checker

def _call(name, payload):
    a = json.loads(payload)
    if name == "check":
        r = checker.check_all(a["setups"], a["reference"], a["answer"], a.get("options"))
    elif name == "validate":
        r = checker.validate(a["setups"], a["reference"], a.get("traps", []), a.get("options"))
    elif name == "parts":
        r = checker.parts(a["line"])
    else:
        raise ValueError("unknown request: " + name)
    return json.dumps(r)
`;

interface PyodideLike {
  FS: { writeFile(path: string, data: string): void };
  runPython(code: string): unknown;
  loadPackagesFromImports(code: string): Promise<void>;
  globals: { get(name: string): (name: string, payload: string) => string };
}

const post = (m: WorkerOut) => (self as unknown as { postMessage(m: WorkerOut): void }).postMessage(m);

let ready: Promise<PyodideLike> | null = null;

function boot(): Promise<PyodideLike> {
  ready ??= (async () => {
    const { loadPyodide } = await import(/* @vite-ignore */ `${PYODIDE_URL}pyodide.mjs`);
    const py: PyodideLike = await loadPyodide({ indexURL: PYODIDE_URL });
    py.FS.writeFile('/home/pyodide/checker.py', checkerSource);
    py.runPython(GLUE);
    return py;
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
    case 'parts':
      return [];
  }
}

// A Python traceback ends with the error line ("ValueError: ..."); that is the part worth showing.
const lastLine = (s: string) => s.trim().split('\n').pop() ?? s;

async function handle(msg: WorkerIn): Promise<void> {
  const { id, ...req } = msg;
  try {
    post({ id, type: 'status', phase: 'loading' });
    const py = await boot();
    // Loads numpy / pandas / scikit-learn only when some code in this request imports them.
    for (const code of snippetsOf(req as Request)) await py.loadPackagesFromImports(code);
    post({ id, type: 'status', phase: 'running' });
    const json = py.globals.get('_call')(req.type, JSON.stringify(req));
    post({ id, type: 'result', result: JSON.parse(json) });
  } catch (e) {
    post({ id, type: 'error', message: lastLine(e instanceof Error ? e.message : String(e)) });
  }
}

self.onmessage = (ev: MessageEvent<WorkerIn>) => {
  void handle(ev.data);
};
