import { test, expect } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL || "http://localhost:3000";
const TEST_EMAIL = process.env.E2E_USER || "admin@acme.corp";
const TEST_PASSWORD = process.env.E2E_PASS || "Admin123!";

async function login(page: any) {
  await page.goto(`${BASE_URL}/login`);
  await expect(page.locator("input[type='email']")).toBeVisible();
  await page.fill("input[type='email']", TEST_EMAIL);
  await page.fill("input[type='password']", TEST_PASSWORD);
  await page.click("button[type='submit']");
  await page.waitForURL("**/dashboard/**", { timeout: 15000 });
}

test.describe("SuccessCore HR — Critical Path", () => {

  test("login → dashboard → employees → logout", async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);

    await expect(page.locator("input[type='email']")).toBeVisible();
    await page.fill("input[type='email']", TEST_EMAIL);
    await page.fill("input[type='password']", TEST_PASSWORD);

    await page.click("button[type='submit']");

    await page.waitForURL("**/dashboard/**", { timeout: 15000 });
    await expect(page.locator("header")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("text=Dashboard")).toBeVisible();

    await page.click("text=Empleados");

    await page.waitForURL("**/employees/**", { timeout: 10000 });
    await expect(page.locator("table, [data-testid='employee-list']")).toBeVisible({ timeout: 5000 });

    await page.click("[data-testid='user-avatar']");
    await page.click("text=Cerrar Sesion");

    await page.waitForURL("**/login", { timeout: 10000 });
    await expect(page.locator("input[type='email']")).toBeVisible();
  });

  test("health check endpoint", async ({ request }) => {
    const apiBase = process.env.API_URL || "http://localhost:8080";
    const resp = await request.get(`${apiBase}/health`);
    expect(resp.ok()).toBeTruthy();

    const body = await resp.json();
    expect(body.status).toBe("ok");
    expect(body.checks.database.ok).toBe(true);
  });

  test("search endpoint returns results", async ({ request }) => {
    const apiBase = process.env.API_URL || "http://localhost:8080";
    const resp = await request.get(`${apiBase}/api/v1/search?q=admin`);
    expect(resp.ok()).toBeTruthy();

    const body = await resp.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test("employee creation flow", async ({ page }) => {
    const testEmployeeEmail = `e2e-${Date.now()}@acme.corp`;

    await login(page);

    await page.click("text=Empleados");
    await page.waitForURL("**/employees/**", { timeout: 10000 });

    await page.click("text=Agregar, [data-testid='add-employee']");

    await expect(page.locator("[data-testid='employee-form']")).toBeVisible({ timeout: 5000 });

    await page.fill("[data-testid='employee-full-name']", "E2E Test User");
    await page.fill("[data-testid='employee-email']", testEmployeeEmail);
    await page.fill("[data-testid='employee-department']", "Engineering");
    await page.selectOption("[data-testid='employee-role']", "employee");

    await page.click("button[type='submit']");

    await expect(page.locator(`text=${testEmployeeEmail}`)).toBeVisible({ timeout: 10000 });

    await page.click(`tr:has-text("${testEmployeeEmail}") [data-testid='delete-employee']`);
    await page.click("button:has-text('Confirmar')");

    await expect(page.locator(`text=${testEmployeeEmail}`)).not.toBeVisible({ timeout: 5000 });
  });

  test("vacation request flow", async ({ page }) => {
    await login(page);

    await page.click("text=Calendario");
    await page.waitForURL("**/calendar**", { timeout: 10000 });

    await page.click("[data-testid='request-pto']");

    await expect(page.locator("[data-testid='pto-form']")).toBeVisible({ timeout: 5000 });

    const startDate = new Date();
    startDate.setDate(startDate.getDate() + 7);
    const endDate = new Date(startDate);
    endDate.setDate(endDate.getDate() + 2);

    await page.fill("[data-testid='pto-start-date']", startDate.toISOString().split("T")[0]);
    await page.fill("[data-testid='pto-end-date']", endDate.toISOString().split("T")[0]);
    await page.fill("[data-testid='pto-type']", "vacation");
    await page.fill("[data-testid='pto-notes']", "E2E test vacation request");

    await page.click("button[type='submit']");

    await expect(page.locator("text=Pending, text=pendiente")).toBeVisible({ timeout: 5000 });
  });

  test("payroll processing flow", async ({ page }) => {
    await login(page);

    await page.click("text=Nomina");
    await page.waitForURL("**/pay**", { timeout: 10000 });

    await page.click("[data-testid='create-pay-cycle']");

    await expect(page.locator("[data-testid='pay-cycle-form']")).toBeVisible({ timeout: 5000 });

    const periodStart = new Date();
    periodStart.setDate(1);
    const periodEnd = new Date(periodStart);
    periodEnd.setMonth(periodEnd.getMonth() + 1);
    periodEnd.setDate(0);

    await page.fill("[data-testid='cycle-name']", `E2E Pay Cycle ${Date.now()}`);
    await page.fill("[data-testid='cycle-period-start']", periodStart.toISOString().split("T")[0]);
    await page.fill("[data-testid='cycle-period-end']", periodEnd.toISOString().split("T")[0]);
    await page.selectOption("[data-testid='cycle-currency']", "USD");

    await page.click("[data-testid='save-cycle']");

    await expect(page.locator("text=E2E Pay Cycle")).toBeVisible({ timeout: 10000 });

    await page.click("[data-testid='process-cycle']");
    await page.click("button:has-text('Confirmar')");

    await expect(page.locator("text=Procesado, text=Completed")).toBeVisible({ timeout: 15000 });
  });
});
