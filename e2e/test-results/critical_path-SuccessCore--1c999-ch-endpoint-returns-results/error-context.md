# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: critical_path.spec.ts >> SuccessCore HR — Critical Path >> search endpoint returns results
- Location: critical_path.spec.ts:53:7

# Error details

```
Error: expect(received).toBeTruthy()

Received: false
```

# Test source

```ts
  1   | import { test, expect } from "@playwright/test";
  2   | 
  3   | const BASE_URL = process.env.E2E_BASE_URL || "http://localhost:3000";
  4   | const TEST_EMAIL = process.env.E2E_USER || "admin@acme.corp";
  5   | const TEST_PASSWORD = process.env.E2E_PASS || "Admin123!";
  6   | 
  7   | async function login(page: any) {
  8   |   await page.goto(`${BASE_URL}/login`);
  9   |   await expect(page.locator("input[type='email']")).toBeVisible();
  10  |   await page.fill("input[type='email']", TEST_EMAIL);
  11  |   await page.fill("input[type='password']", TEST_PASSWORD);
  12  |   await page.click("button[type='submit']");
  13  |   await page.waitForURL("**/dashboard/**", { timeout: 15000 });
  14  | }
  15  | 
  16  | test.describe("SuccessCore HR — Critical Path", () => {
  17  | 
  18  |   test("login → dashboard → employees → logout", async ({ page }) => {
  19  |     await page.goto(`${BASE_URL}/login`);
  20  | 
  21  |     await expect(page.locator("input[type='email']")).toBeVisible();
  22  |     await page.fill("input[type='email']", TEST_EMAIL);
  23  |     await page.fill("input[type='password']", TEST_PASSWORD);
  24  | 
  25  |     await page.click("button[type='submit']");
  26  | 
  27  |     await page.waitForURL("**/dashboard/**", { timeout: 15000 });
  28  |     await expect(page.locator("header")).toBeVisible({ timeout: 10000 });
  29  |     await expect(page.locator("text=Dashboard")).toBeVisible();
  30  | 
  31  |     await page.click("text=Empleados");
  32  | 
  33  |     await page.waitForURL("**/employees/**", { timeout: 10000 });
  34  |     await expect(page.locator("table, [data-testid='employee-list']")).toBeVisible({ timeout: 5000 });
  35  | 
  36  |     await page.click("[data-testid='user-avatar']");
  37  |     await page.click("text=Cerrar Sesion");
  38  | 
  39  |     await page.waitForURL("**/login", { timeout: 10000 });
  40  |     await expect(page.locator("input[type='email']")).toBeVisible();
  41  |   });
  42  | 
  43  |   test("health check endpoint", async ({ request }) => {
  44  |     const apiBase = process.env.API_URL || "http://localhost:8080";
  45  |     const resp = await request.get(`${apiBase}/health`);
  46  |     expect(resp.ok()).toBeTruthy();
  47  | 
  48  |     const body = await resp.json();
  49  |     expect(body.status).toBe("ok");
  50  |     expect(body.checks.database.ok).toBe(true);
  51  |   });
  52  | 
  53  |   test("search endpoint returns results", async ({ request }) => {
  54  |     const apiBase = process.env.API_URL || "http://localhost:8080";
  55  |     const resp = await request.get(`${apiBase}/api/v1/search?q=admin`);
> 56  |     expect(resp.ok()).toBeTruthy();
      |                       ^ Error: expect(received).toBeTruthy()
  57  | 
  58  |     const body = await resp.json();
  59  |     expect(Array.isArray(body)).toBe(true);
  60  |   });
  61  | 
  62  |   test("employee creation flow", async ({ page }) => {
  63  |     const testEmployeeEmail = `e2e-${Date.now()}@acme.corp`;
  64  | 
  65  |     await login(page);
  66  | 
  67  |     await page.click("text=Empleados");
  68  |     await page.waitForURL("**/employees/**", { timeout: 10000 });
  69  | 
  70  |     await page.click("text=Agregar, [data-testid='add-employee']");
  71  | 
  72  |     await expect(page.locator("[data-testid='employee-form']")).toBeVisible({ timeout: 5000 });
  73  | 
  74  |     await page.fill("[data-testid='employee-full-name']", "E2E Test User");
  75  |     await page.fill("[data-testid='employee-email']", testEmployeeEmail);
  76  |     await page.fill("[data-testid='employee-department']", "Engineering");
  77  |     await page.selectOption("[data-testid='employee-role']", "employee");
  78  | 
  79  |     await page.click("button[type='submit']");
  80  | 
  81  |     await expect(page.locator(`text=${testEmployeeEmail}`)).toBeVisible({ timeout: 10000 });
  82  | 
  83  |     await page.click(`tr:has-text("${testEmployeeEmail}") [data-testid='delete-employee']`);
  84  |     await page.click("button:has-text('Confirmar')");
  85  | 
  86  |     await expect(page.locator(`text=${testEmployeeEmail}`)).not.toBeVisible({ timeout: 5000 });
  87  |   });
  88  | 
  89  |   test("vacation request flow", async ({ page }) => {
  90  |     await login(page);
  91  | 
  92  |     await page.click("text=Calendario");
  93  |     await page.waitForURL("**/calendar**", { timeout: 10000 });
  94  | 
  95  |     await page.click("[data-testid='request-pto']");
  96  | 
  97  |     await expect(page.locator("[data-testid='pto-form']")).toBeVisible({ timeout: 5000 });
  98  | 
  99  |     const startDate = new Date();
  100 |     startDate.setDate(startDate.getDate() + 7);
  101 |     const endDate = new Date(startDate);
  102 |     endDate.setDate(endDate.getDate() + 2);
  103 | 
  104 |     await page.fill("[data-testid='pto-start-date']", startDate.toISOString().split("T")[0]);
  105 |     await page.fill("[data-testid='pto-end-date']", endDate.toISOString().split("T")[0]);
  106 |     await page.fill("[data-testid='pto-type']", "vacation");
  107 |     await page.fill("[data-testid='pto-notes']", "E2E test vacation request");
  108 | 
  109 |     await page.click("button[type='submit']");
  110 | 
  111 |     await expect(page.locator("text=Pending, text=pendiente")).toBeVisible({ timeout: 5000 });
  112 |   });
  113 | 
  114 |   test("payroll processing flow", async ({ page }) => {
  115 |     await login(page);
  116 | 
  117 |     await page.click("text=Nomina");
  118 |     await page.waitForURL("**/pay**", { timeout: 10000 });
  119 | 
  120 |     await page.click("[data-testid='create-pay-cycle']");
  121 | 
  122 |     await expect(page.locator("[data-testid='pay-cycle-form']")).toBeVisible({ timeout: 5000 });
  123 | 
  124 |     const periodStart = new Date();
  125 |     periodStart.setDate(1);
  126 |     const periodEnd = new Date(periodStart);
  127 |     periodEnd.setMonth(periodEnd.getMonth() + 1);
  128 |     periodEnd.setDate(0);
  129 | 
  130 |     await page.fill("[data-testid='cycle-name']", `E2E Pay Cycle ${Date.now()}`);
  131 |     await page.fill("[data-testid='cycle-period-start']", periodStart.toISOString().split("T")[0]);
  132 |     await page.fill("[data-testid='cycle-period-end']", periodEnd.toISOString().split("T")[0]);
  133 |     await page.selectOption("[data-testid='cycle-currency']", "USD");
  134 | 
  135 |     await page.click("[data-testid='save-cycle']");
  136 | 
  137 |     await expect(page.locator("text=E2E Pay Cycle")).toBeVisible({ timeout: 10000 });
  138 | 
  139 |     await page.click("[data-testid='process-cycle']");
  140 |     await page.click("button:has-text('Confirmar')");
  141 | 
  142 |     await expect(page.locator("text=Procesado, text=Completed")).toBeVisible({ timeout: 15000 });
  143 |   });
  144 | });
  145 | 
```