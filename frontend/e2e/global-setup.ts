import { spawn, spawnSync, type ChildProcess } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import { mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'

async function ready(url: string, instance?: string) {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(url)
      if (response.ok && (!instance || (await response.json()).instance === instance)) return
    } catch {}
    await new Promise((done) => setTimeout(done, 100))
  }
  throw new Error(`${url} 서버가 준비되지 않았습니다.`)
}

function stopTree(child: ChildProcess) {
  if (!child.pid) return
  if (process.platform === 'win32') {
    spawnSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true })
  } else {
    try { process.kill(child.pid, 'SIGKILL') } catch {}
  }
}

export default async function () {
  const root = process.env.E2E_ROOT!
  const state = process.env.E2E_STATE!
  mkdirSync(state, { recursive: true })
  const python = process.env.E2E_PYTHON ?? resolve(root, 'backend', '.venv', 'Scripts', 'python.exe')
  const database = resolve(state, `incidents-${randomUUID()}.db`)
  const databaseUrl = `sqlite:///${database.replaceAll('\\', '/')}`
  const instance = randomUUID()
  const backend = spawn(python, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000', '--timeout-graceful-shutdown', '1'], {
    cwd: resolve(root, 'backend'), env: { ...process.env, DATABASE_URL: databaseUrl, APP_INSTANCE_ID: instance, CODEX_SUMMARY_ENABLED: 'false', SSE_HEARTBEAT_SECONDS: '1' }, detached: false, stdio: 'ignore', windowsHide: true,
  })
  const frontend = spawn(process.execPath, [resolve(root, 'frontend', 'node_modules', 'vite', 'bin', 'vite.js'), '--host', '127.0.0.1', '--port', '5173', '--strictPort'], {
    cwd: resolve(root, 'frontend'), env: { ...process.env, API_PROXY_TARGET: process.env.E2E_API_URL! }, detached: false, stdio: 'ignore', windowsHide: true,
  })
  const stateFile = resolve(state, 'servers.json')
  writeFileSync(stateFile, JSON.stringify({ backend: backend.pid, frontend: frontend.pid, database }))
  try {
    await Promise.all([ready(`${process.env.E2E_API_URL}/health`, instance), ready('http://127.0.0.1:5173')])
  } catch (error) {
    stopTree(frontend)
    stopTree(backend)
    rmSync(database, { force: true })
    rmSync(stateFile, { force: true })
    throw error
  }
}
