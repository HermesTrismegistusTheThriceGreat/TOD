import { chromium } from 'playwright';

const reportDir = './playwright-reports/2026-01-09_06-53-23';
const TARGET_URL = 'http://localhost:5175';

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  colorScheme: 'dark'
});
const page = await context.newPage();

console.log('=== IronCondorCard Validation (Orchestrator UI) ===\n');

console.log('1. Navigating to', TARGET_URL);
await page.goto(TARGET_URL, { waitUntil: 'networkidle' });
await page.screenshot({ path: `${reportDir}/01-orchestrator-home.png`, fullPage: false });
console.log('   Page title:', await page.title());

// Wait for Vue app to fully mount
await page.waitForTimeout(2000);

// Check for Open Positions section
console.log('\n2. Searching for Open Positions section...');
const openPosHeader = await page.locator('text=Open Positions').first();
const openPosVisible = await openPosHeader.isVisible().catch(() => false);
console.log('   Open Positions visible:', openPosVisible);

// Take screenshot
await page.screenshot({ path: `${reportDir}/02-initial-state.png`, fullPage: false });

// Look for ticker symbols
console.log('\n3. Looking for ticker symbols (SPY, QQQ, IWM)...');
const tickers = ['SPY', 'QQQ', 'IWM'];
let tickersFound = 0;
for (const ticker of tickers) {
  const count = await page.locator('text=' + ticker).count();
  const found = count > 0;
  if (found) tickersFound++;
  console.log('  ', ticker + ':', found ? 'FOUND (' + count + ')' : 'NOT FOUND');
}

// Look for position-card class elements (IronCondorCard uses el-card with position-card class)
console.log('\n4. Analyzing IronCondorCard components...');
const cardAnalysis = await page.evaluate(() => {
  const cards = document.querySelectorAll('.position-card, .el-card');
  const results = [];

  cards.forEach((card, index) => {
    const hasScrollbar = card.scrollHeight > card.clientHeight || card.scrollWidth > card.clientWidth;
    const style = window.getComputedStyle(card);
    const cardBody = card.querySelector('.el-card__body');
    const cardBodyStyle = cardBody ? window.getComputedStyle(cardBody) : null;

    // Check for P/L ring
    const pnlRing = card.querySelector('.pnl-ring');
    const hasPnlRing = !!pnlRing;

    // Check for DTE box
    const dteBox = card.querySelector('.dte-box');
    const hasDteBox = !!dteBox;

    // Check for legs table
    const legsTable = card.querySelector('.legs-table, .el-table');
    const hasLegsTable = !!legsTable;

    // Get ticker from card
    const tickerEl = card.querySelector('.ticker');
    const ticker = tickerEl ? tickerEl.textContent : 'N/A';

    results.push({
      index,
      ticker,
      className: card.className.substring(0, 100),
      hasScrollbar,
      scrollHeight: card.scrollHeight,
      clientHeight: card.clientHeight,
      scrollWidth: card.scrollWidth,
      clientWidth: card.clientWidth,
      overflow: style.overflow,
      overflowY: style.overflowY,
      overflowX: style.overflowX,
      cardBodyOverflow: cardBodyStyle ? cardBodyStyle.overflow : 'N/A',
      hasPnlRing,
      hasDteBox,
      hasLegsTable,
      background: style.backgroundColor
    });
  });

  return results;
});

console.log('   Found', cardAnalysis.length, 'card elements');
cardAnalysis.forEach((card, i) => {
  console.log('\n   Card', i + 1, '(' + card.ticker + '):');
  console.log('     - P/L Ring:', card.hasPnlRing ? 'YES' : 'NO');
  console.log('     - DTE Box:', card.hasDteBox ? 'YES' : 'NO');
  console.log('     - Legs Table:', card.hasLegsTable ? 'YES' : 'NO');
  console.log('     - Has Scrollbar:', card.hasScrollbar ? 'YES (ISSUE!)' : 'NO (GOOD)');
  console.log('     - Overflow:', card.overflow, '/ Y:', card.overflowY, '/ X:', card.overflowX);
  console.log('     - Dimensions:', card.clientWidth + 'x' + card.clientHeight, '(scroll:', card.scrollWidth + 'x' + card.scrollHeight + ')');
  console.log('     - Background:', card.background);
});

// Check for any scrollbar issues in detail
console.log('\n5. Detailed scrollbar analysis...');
const scrollbarAnalysis = await page.evaluate(() => {
  const issues = [];

  // Check all elements within position cards
  const cards = document.querySelectorAll('.position-card');
  cards.forEach((card, cardIndex) => {
    card.querySelectorAll('*').forEach((el) => {
      const hasVerticalScroll = el.scrollHeight > el.clientHeight + 2;
      const hasHorizontalScroll = el.scrollWidth > el.clientWidth + 2;
      const style = window.getComputedStyle(el);

      // Only flag if element is scrollable AND has overflow content
      if ((hasVerticalScroll || hasHorizontalScroll) &&
          (style.overflow === 'auto' || style.overflow === 'scroll' ||
           style.overflowY === 'auto' || style.overflowY === 'scroll' ||
           style.overflowX === 'auto' || style.overflowX === 'scroll')) {
        issues.push({
          cardIndex,
          tag: el.tagName,
          className: el.className.toString().substring(0, 60),
          scrollHeight: el.scrollHeight,
          clientHeight: el.clientHeight,
          overflow: style.overflow
        });
      }
    });
  });

  return issues;
});

if (scrollbarAnalysis.length === 0) {
  console.log('   NO scrollbar issues detected on IronCondorCards');
} else {
  console.log('   SCROLLBAR ISSUES FOUND:');
  scrollbarAnalysis.forEach(issue => {
    console.log('     - Card', issue.cardIndex + 1, ':', issue.tag, '(' + issue.className + ')');
    console.log('       Height:', issue.clientHeight, 'vs scroll:', issue.scrollHeight);
  });
}

// Check dark theme
console.log('\n6. Checking dark theme styling...');
const themeInfo = await page.evaluate(() => {
  const card = document.querySelector('.position-card');
  if (!card) return { error: 'No card found' };

  const style = window.getComputedStyle(card);
  return {
    backgroundColor: style.backgroundColor,
    borderColor: style.borderColor,
    color: style.color,
    isDark: style.backgroundColor.includes('30, 36, 51') ||
            style.backgroundColor.includes('rgb(30') ||
            style.backgroundColor.includes('#1e2433')
  };
});
console.log('   Card styling:', JSON.stringify(themeInfo, null, 2));

// Take screenshot of Open Positions area
console.log('\n7. Taking screenshots of cards...');
await page.screenshot({ path: `${reportDir}/03-cards-visible.png`, fullPage: false });

// Try to get a screenshot of just the Open Positions section
const openPosSection = await page.locator('.open-positions').first();
if (await openPosSection.isVisible().catch(() => false)) {
  await openPosSection.screenshot({ path: `${reportDir}/04-open-positions-section.png` });
  console.log('   Captured Open Positions section screenshot');
}

// Take full page screenshot
await page.screenshot({ path: `${reportDir}/05-full-page.png`, fullPage: true });
console.log('   Captured full page screenshot');

// Summary
console.log('\n=== VALIDATION SUMMARY ===');
console.log('URL:', TARGET_URL);
console.log('Tickers found:', tickersFound, '/ 3');
console.log('Cards found:', cardAnalysis.length);
console.log('Scrollbar issues:', scrollbarAnalysis.length);
console.log('Dark theme applied:', themeInfo.isDark || themeInfo.backgroundColor?.includes('30, 36'));

const success = tickersFound >= 2 && cardAnalysis.length >= 2 && scrollbarAnalysis.length === 0;
console.log('\nOVERALL STATUS:', success ? 'SUCCESS' : 'NEEDS ATTENTION');

await browser.close();
console.log('\nScreenshots saved to:', reportDir);
