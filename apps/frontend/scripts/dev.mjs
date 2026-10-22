// `npm run dev`: the API (uvicorn --reload) and Vite together; Ctrl+C stops both.
import { spawn, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const API_URL = 'http://127.0.0.1:8000/api/health'
const backend = fileURLToPath(new URL('../../backend/', import.meta.url))
const frontend = fileURLToPath(new URL('../', import.meta.url))
const isWindows = process.platform === 'win32'
const python = backend + (isWindows ? '.venv/Scripts/python.exe' : '.venv/bin/python')

const children = []

async function apiIsRunning() {
  try {
    return (await fetch(API_URL)).ok
  } catch {
    return false
  }
}

function start(name, command, args, cwd) {
  const child = spawn(command, args, { cwd, stdio: 'inherit' })
  child.on('exit', (code) => {
    console.log(`\n[dev] ${name} se ha parado (código ${code}); cierro el resto.`)
    stopAll(code ?? 1)
  })
  children.push(child)
}

function stopAll(code = 0) {
  for (const child of children) {
    if (child.exitCode !== null) continue
    // uvicorn --reload runs the server in a child process: kill the whole tree.
    if (isWindows) spawnSync('taskkill', ['/pid', String(child.pid), '/T', '/F'], { stdio: 'ignore' })
    else child.kill('SIGTERM')
  }
  process.exit(code)
}

process.on('SIGINT', () => stopAll(0))
process.on('SIGTERM', () => stopAll(0))
process.on('SIGBREAK', () => stopAll(0))

if (await apiIsRunning()) {
  console.log('[dev] Ya hay una API en el puerto 8000: la reutilizo.')
} else if (!existsSync(python)) {
  console.error(`[dev] No encuentro el venv del backend (${python}).`)
  console.error('[dev] Créalo con: cd apps/backend && python -m venv .venv && pip install -e ".[dev]"')
  process.exit(1)
} else {
  const uvicorn = ['-m', 'uvicorn', 'cadence_ia.main:create_app', '--factory', '--reload', '--port', '8000']
  start('La API', python, uvicorn, backend)
  // Start Vite once the API answers, so the first page load doesn't fail.
  for (let i = 0; i < 60 && !(await apiIsRunning()); i++) await new Promise((r) => setTimeout(r, 500))
}

start('Vite', process.execPath, [frontend + 'node_modules/vite/bin/vite.js'], frontend)
