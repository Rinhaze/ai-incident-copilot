import { expect, test } from '@playwright/test'

test('샘플 장애를 선택하고 상태를 변경한다', async ({ page, request }) => {
  const run = crypto.randomUUID()
  const response = await request.post(`${process.env.E2E_API_URL}/api/logs/batch`, { data: { logs: [0, 1, 2].map((index) => ({
    external_id: `e2e-${run}-${index}`,
    service: '결제',
    severity: index === 2 ? 'critical' : 'error',
    message: `결제 /orders/${100 + index} 실패`,
    timestamp: `2025-01-01T00:00:${String(index * 10).padStart(2, '0')}Z`,
  })) } })
  expect(response.ok()).toBeTruthy()
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'AI Incident Copilot' })).toBeVisible()
  await expect(page.getByText('규칙 요약')).toBeVisible()
  await expect(page.getByText('critical 원본 로그가 포함되어 최고 심각도로 분류했습니다.')).toBeVisible()
  await page.getByRole('button', { name: '확인 시작' }).click()
  await expect(page.getByRole('button', { name: '해결 처리' })).toBeVisible()
  if (process.env.CAPTURE_DEMO === 'true') {
    await page.screenshot({ path: '../docs/images/dashboard.png', fullPage: true })
  }
  await page.goto('about:blank')
  await page.close()
})
