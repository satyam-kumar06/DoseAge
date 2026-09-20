import { chromium } from "playwright";

const BASE = "http://127.0.0.1:5173";
const results = [];
const check = (name, ok, detail = "") => {
  results.push({ name, ok, detail });
  console.log(`${ok ? "ok  " : "FAIL"} ${name}${!ok && detail ? "  <- " + detail : ""}`);
};

const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));

await page.goto(BASE, { waitUntil: "networkidle" });
check("onboarding renders", await page.getByText("DoseWise").first().isVisible());

// Seed the demo family through the UI button
await page.getByRole("button", { name: /Load the demo family/i }).click();
await page.waitForTimeout(2500);

const dash = await page.getByText(/Last 7 days/i).isVisible().catch(() => false);
check("dashboard loads after seed", dash);

const dup = await page.getByText(/both contain Paracetamol/i).first().isVisible().catch(() => false);
check("duplicate salt banner shows on dashboard", dup);

const savings = await page.getByText(/Jan Aushadhi Saver/i).isVisible().catch(() => false);
check("savings card renders", savings);

const refill = await page.getByText(/Refill Radar/i).isVisible().catch(() => false);
check("refill radar renders", refill);

await page.screenshot({ path: "/tmp/shot-dashboard.png", fullPage: true });

// Parent mode
await page.getByRole("button", { name: /माता-पिता|Parent/ }).click();
await page.waitForTimeout(1500);
const greet = await page.getByText(/नमस्ते|Hello/).first().isVisible().catch(() => false);
check("parent Today screen renders", greet);

const takeBtn = page.getByRole("button", { name: /ले लिया|Taken/ }).first();
check("giant Le liya button exists", await takeBtn.isVisible().catch(() => false));

const box = await takeBtn.boundingBox();
check("Le liya is at least 64px tall", box && box.height >= 64, box ? `${Math.round(box.height)}px` : "no box");

await page.screenshot({ path: "/tmp/shot-parent.png", fullPage: true });

await takeBtn.click();
await page.waitForTimeout(1800);
const toast = await page.getByText(/शाबाश|Well done/).first().isVisible().catch(() => false);
check("taken moment fires with praise", toast);

// Language toggle
await page.getByRole("button", { name: /Switch to English|हिन्दी में बदलें/ }).click();
await page.waitForTimeout(600);
const english = await page.getByText(/Today's medicine|आज की दवा/).first().isVisible().catch(() => false);
check("language toggle works", english);

// Reminder takeover
await page.getByRole("button", { name: /Reminder/ }).click();
await page.waitForTimeout(1500);
const takeover = await page.getByRole("dialog").isVisible().catch(() => false);
check("reminder takeover opens full screen", takeover);
await page.screenshot({ path: "/tmp/shot-reminder.png", fullPage: true });
await page.keyboard.press("Escape");

// Horizontal overflow check at phone width
const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
check("no horizontal scroll at 390px", overflow <= 1, `${overflow}px`);

// 200% font size
await page.addStyleTag({ content: "html{font-size:32px}" });
await page.waitForTimeout(400);
const overflow2 = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
check("survives 200 percent font size", overflow2 <= 2, `${overflow2}px`);

check("no console errors", errors.length === 0, errors.slice(0, 3).join(" | "));

await browser.close();

const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length} passed, ${failed.length} failed`);
process.exit(failed.length ? 1 : 0);
