const { spawn } = require('child_process');

async function testWidth(url, width, height) {
  const edge = spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', [
    '--headless',
    '--disable-gpu',
    '--remote-debugging-port=9223',
    '--window-size=' + width + ',' + height,
    url
  ]);

  await new Promise(r => setTimeout(r, 2000));

  try {
    const listRes = await fetch('http://127.0.0.1:9223/json');
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
        var innerW = window.innerWidth;
        var scrollW = document.documentElement.scrollWidth;
        var bodyScrollW = document.body.scrollWidth;
        var overflowing = [];
        var elements = document.querySelectorAll('*');
        for (var i = 0; i < elements.length; i++) {
          var el = elements[i];
          var rect = el.getBoundingClientRect();
          if (rect.right > innerW + 1) {
            overflowing.push({
              tag: el.tagName,
              id: el.id,
              className: typeof el.className === 'string' ? el.className : '',
              right: Math.round(rect.right),
              width: Math.round(rect.width),
              excess: Math.round(rect.right - innerW)
            });
          }
        }
        return {
          innerW: innerW,
          scrollW: scrollW,
          bodyScrollW: bodyScrollW,
          hasOverflow: scrollW > innerW,
          overflowingCount: overflowing.length,
          topOverflowing: overflowing.slice(0, 15)
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

    console.log('Result for ' + width + 'x' + height + ':', JSON.stringify(result.result.value, null, 2));
    ws.close();
  } catch (err) {
    console.error('Error:', err);
  } finally {
    edge.kill();
  }
}

async function run() {
  const url = process.argv[2] || 'http://127.0.0.1:8000/dashboard/overview.html';
  console.log('Testing page:', url);
  console.log('\n=== TESTING AT 1366px ===');
  await testWidth(url, 1366, 768);
  console.log('\n=== TESTING AT 1280px ===');
  await testWidth(url, 1280, 768);
  console.log('\n=== TESTING AT 1024px ===');
  await testWidth(url, 1024, 768);
  console.log('\n=== TESTING AT 768px ===');
  await testWidth(url, 768, 1024);
}
run();
