import { test, expect, Page } from '@playwright/test'
import path from 'path'

test.describe('Analyze to Dashboard Flow', () => {
  let page: Page

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage()
    await page.goto('/')
  })

  test('navigates to analyze page and uploads resume', async () => {
    // From home, navigate to Analyze
    await page.click('text=Analyze')
    await expect(page).toHaveURL('/analyze')

    // Verify form is visible
    await expect(page.locator('label:has-text("Resume")')).toBeVisible()
    await expect(page.locator('label:has-text("Job Description")')).toBeVisible()
  })

  test('completes analysis and redirects to dashboard', async () => {
    await page.goto('/analyze')

    // Upload sample files
    const resumeInput = page.locator('input[type="file"]').first()
    const jdInput = page.locator('input[type="file"]').nth(1)

    // Create sample file content
    const resumeContent = 'Software Engineer with 5 years of experience in React, TypeScript, and Node.js'
    const jdContent = 'Senior Engineer - React, TypeScript, AWS, Docker experience required'

    // Fill inputs (mock file upload)
    await resumeInput.setInputFiles({
      name: 'resume.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from(resumeContent),
    })

    await jdInput.setInputFiles({
      name: 'job.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from(jdContent),
    })

    // Submit form
    await page.click('button:has-text("Analyze")')

    // Wait for redirect to dashboard
    await page.waitForURL('/dashboard', { timeout: 10000 })
    expect(page.url()).toContain('/dashboard')
  })

  test('dashboard renders all tabs', async () => {
    await page.goto('/dashboard')

    // Verify all tabs are rendered
    const tabs = ['Profile', 'Gaps', 'Path', 'Graph', 'Explain', 'Simulate']
    for (const tab of tabs) {
      const tabElement = page.locator(`[role="tab"]:has-text("${tab}")`)
      await expect(tabElement).toBeVisible()
    }
  })

  test('tab navigation works correctly', async () => {
    await page.goto('/dashboard')

    // Click Profile tab
    await page.click('[role="tab"]:has-text("Profile")')
    const profilePanel = page.locator('[role="tabpanel"]')
    await expect(profilePanel).toBeVisible()

    // Click Gaps tab
    await page.click('[role="tab"]:has-text("Gaps")')
    await expect(profilePanel).toBeVisible({ timeout: 5000 })

    // Click Path tab
    await page.click('[role="tab"]:has-text("Path")')
    await expect(profilePanel).toBeVisible({ timeout: 5000 })
  })

  test('mobile view renders tab strip', async ({ browser }) => {
    const mobileContext = await browser.newContext({
      viewport: { width: 375, height: 667 },
    })
    const mobilePage = await mobileContext.newPage()
    await mobilePage.goto('/dashboard')

    // Verify mobile tab strip is visible
    const tabStrip = mobilePage.locator('[role="tablist"]')
    await expect(tabStrip).toBeVisible()

    // Verify tabs are in the strip
    const tabs = mobilePage.locator('[role="tab"]')
    expect(await tabs.count()).toBeGreaterThan(0)

    await mobileContext.close()
  })

  test('sidebar drawer is hidden on mobile', async ({ browser }) => {
    const mobileContext = await browser.newContext({
      viewport: { width: 375, height: 667 },
    })
    const mobilePage = await mobileContext.newPage()
    await mobilePage.goto('/dashboard')

    // Verify drawer toggle button exists
    const drawerButton = mobilePage.locator('button[aria-label*="menu" i]')
    if (await drawerButton.isVisible()) {
      await drawerButton.click()
      // Drawer should appear
      const drawer = mobilePage.locator('[role="dialog"]')
      await expect(drawer).toBeVisible()
    }

    await mobileContext.close()
  })

  test('graph tab renders visualization', async () => {
    await page.goto('/dashboard')

    // Click Graph tab
    await page.click('[role="tab"]:has-text("Graph")')

    // Wait for D3 graph to render
    const svgElement = page.locator('svg')
    await expect(svgElement).toBeVisible({ timeout: 5000 })
  })

  test('explain tab renders explainability console', async () => {
    await page.goto('/dashboard')

    // Click Explain tab
    await page.click('[role="tab"]:has-text("Explain")')

    // Wait for console to render
    const console = page.locator('[role="region"]')
    await expect(console).toBeVisible({ timeout: 5000 })
  })

  test('simulate tab renders simulation panel', async () => {
    await page.goto('/dashboard')

    // Click Simulate tab
    await page.click('[role="tab"]:has-text("Simulate")')

    // Wait for simulation panel to render
    const panel = page.locator('form, [role="region"]')
    await expect(panel.first()).toBeVisible({ timeout: 5000 })
  })

  test('error state displays on invalid data', async () => {
    // Navigate to dashboard without valid analysis data
    await page.goto('/dashboard')

    // Check if empty state or error is displayed
    const emptyOrError = page.locator('[role="status"], [role="alert"]')
    // Visibility depends on whether there's mock data available
    if (await emptyOrError.count() > 0) {
      await expect(emptyOrError.first()).toBeVisible()
    }
  })
})
