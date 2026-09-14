import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'
describe('incident list', () => {
  beforeEach(() => vi.restoreAllMocks())
  it('shows empty state', async () => { vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [] })); render(<App />); expect(await screen.findByText('표시할 장애가 없습니다.')).toBeInTheDocument() })
  it('searches and displays incidents', async () => { const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [{id:'1',service:'orders',severity:'error',title:'주문 오류',status:'open',opened_at:'2025-01-01T00:00:00Z',updated_at:'2025-01-01T00:00:00Z',resolved_at:null}] }); vi.stubGlobal('fetch', fetchMock); const user = userEvent.setup(); render(<App />); await screen.findByText('주문 오류'); await user.type(screen.getByLabelText('서비스'), 'orders'); await user.click(screen.getByRole('button', {name:'검색'})); expect(fetchMock).toHaveBeenLastCalledWith(expect.stringContaining('service=orders'), expect.anything()) })
  it('shows an API error', async () => { vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({ error: { message:'서버 오류' }}) })); render(<App />); expect(await screen.findByRole('alert')).toHaveTextContent('서버 오류') })
})
