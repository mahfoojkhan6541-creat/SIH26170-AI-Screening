const { spawn } = require('child_process');

async function testPage(url, width, height) {
  const tmpDir = require('os').tmpdir() + '\\edge_test_' + Date.now();
  const edge = spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', [
    '--headless',
    '--disable-gpu',
    '--user-data-dir=' + tmpDir,
    '--remote-debugging-port=9224',
    '--window-size=' + width + ',' + height,
    url
  ]);

  await new Promise(r => setTimeout(r, 2000));

  try {
    const listRes = await fetch('http://127.0.0.1:9224/json');
    const tabs = await listRes.json();
    const pageTab = tabs.find(t => t.url.includes('dashboard'));
    if (!pageTab) {
      console.log('No tab found');
      return;
    }

    const ws = new WebSocket(pageTab.webSocketDebuggerUrl);
    await new Promise(r => ws.onopen = r);

    const evalScript = `
      (function() {
        var hdr = document.querySelector('.app-workspace-header');
        var briefing = document.querySelector('.mission-briefing-strip');
        var kpiGrid = document.querySelector('.kpi-grid') || document.querySelector('.metrics-bar-grid');
        var firstChart = document.querySelector('.overview-hero-grid') || document.querySelector('.lot-screening-card') || document.querySelector('.diag-main-grid');
        
        var hdrRect = hdr ? hdr.getBoundingClientRect() : null;
        var briefingRect = briefing ? briefing.getBoundingClientRect() : null;
        var kpiRect = kpiGrid ? kpiGrid.getBoundingClientRect() : null;
        var chartRect = firstChart ? firstChart.getBoundingClientRect() : null;

        var topRow = document.querySelector('.header-top-row');
        var subRow = document.querySelector('.header-sub-row');
        var topRect = topRow ? topRow.getBoundingClientRect() : null;
        var subRect = subRow ? subRow.getBoundingClientRect() : null;
        var pills = document.querySelector('.dataset-switcher');
        var telem = document.querySelector('.run-telemetry-strip');

        return {
          viewportWidth: window.innerWidth,
          viewportHeight: window.innerHeight,
          headerHeight: hdrRect ? Math.round(hdrRect.height) : 0,
          topRowHeight: topRect ? Math.round(topRect.height) : 0,
          subRowHeight: subRect ? Math.round(subRect.height) : 0,
          pillsHeight: pills ? Math.round(pills.getBoundingClientRect().height) : 0,
          pillsWidth: pills ? Math.round(pills.getBoundingClientRect().width) : 0,
          pillButtons: pills ? Array.from(pills.querySelectorAll('button')).map(b => ({ id: b.id, top: Math.round(b.getBoundingClientRect().top), left: Math.round(b.getBoundingClientRect().left), width: Math.round(b.getBoundingClientRect().width) })) : [],
          telemHeight: telem ? Math.round(telem.getBoundingClientRect().height) : 0,
          pillsTop: pills ? Math.round(pills.getBoundingClientRect().top) : 0,
          telemTop: telem ? Math.round(telem.getBoundingClientRect().top) : 0,
          briefingHeight: briefingRect ? Math.round(briefingRect.height) : 0,
          kpiTop: kpiRect ? Math.round(kpiRect.top) : 0,
          kpiBottom: kpiRect ? Math.round(kpiRect.bottom) : 0,
          chartTop: chartRect ? Math.round(chartRect.top) : 0,
          chartVisibleHeightAboveFold: chartRect ? Math.round(Math.max(0, window.innerHeight - chartRect.top)) : 0,
          hasHorizontalOverflow: document.documentElement.scrollWidth > window.innerWidth
        };
      })()
    `;

    const result = await new Promise(resolve => {
      ws.onmessage = msg => {
        const data = JSON.parse(msg.data);
        if (data.id === 1) resolve(data.result);
      };
      ws.send(JSON.stringify({
        id: 1,
        method: 'Runtime.evaluate',
        params: { expression: evalScript, returnByValue: true }
      }));
    });

    console.log('Metrics for ' + width + 'x' + height + ':', JSON.stringify(result.result.value, null, 2));
    ws.close();
  } catch (err) {
    console.error('Error:', err);
  } finally {
    edge.kill();
  }
}

async function run() {
  const url = process.argv[2] || 'http://127.0.0.1:8000/dashboard/overview.html';
  console.log('Testing header & viewport space for:', url);
  console.log('\n--- 1366x768 (Standard Laptop) ---');
  await testPage(url, 1366, 768);
  console.log('\n--- 1280x768 (Compact Laptop) ---');
  await testPage(url, 1280, 768);
}

run();
