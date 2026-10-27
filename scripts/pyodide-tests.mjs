// Runs python/tests/test_checker.py and test_seed.py unchanged inside Pyodide (the pinned npm build, 314.0.7).
// Usage: npm run test:pyodide
import { loadPyodide } from 'pyodide';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const py = await loadPyodide();
console.log('Pyodide', py.version);
await py.loadPackage(['numpy', 'pandas', 'scikit-learn']);
py.mountNodeFS('/repo', root);

console.log(
  py.runPython(
    'import sys, numpy, pandas, sklearn\nf"Python {sys.version.split()[0]}, numpy {numpy.__version__}, pandas {pandas.__version__}, scikit-learn {sklearn.__version__}"',
  ),
);

let output = '';
py.setStdout({ batched: (s) => (output += s + '\n') });
py.setStderr({ batched: (s) => (output += s + '\n') });

function runScript(file, args) {
  output = '';
  py.globals.set('_file', file);
  py.globals.set('_args', args);
  let exit = 0;
  try {
    py.runPython(`
import sys, runpy
sys.argv = [_file] + list(_args)
runpy.run_path(_file, run_name="__main__")
`);
  } catch (e) {
    // test_seed.py ends with sys.exit(...); Pyodide reports that as a PythonError.
    if (!String(e).includes('SystemExit')) throw e;
    exit = /SystemExit: 0\b/.test(String(e)) ? 0 : 1;
  }
  return { text: output, exit };
}

const checker = runScript('/repo/python/tests/test_checker.py', ['/repo/python']);
const seed = runScript('/repo/python/tests/test_seed.py', ['/repo']);
process.stdout.write(checker.text + seed.text);

const m = checker.text.match(/mismatches: (\d+) of (\d+)/);
const s = seed.text.match(/notes: (\d+) problems: (\d+)/);
const checkerOk = m && m[1] === '0' && m[2] === '71';
const seedOk = s && s[1] === '21' && s[2] === '0' && seed.exit === 0;
console.log(`\ntest_checker: ${checkerOk ? 'PASS' : 'FAIL'} (${m ? m[0] : 'no summary line'})`);
console.log(`test_seed:    ${seedOk ? 'PASS' : 'FAIL'} (${s ? s[0] : 'no summary line'})`);
process.exit(checkerOk && seedOk ? 0 : 1);
