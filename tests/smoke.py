"""Smoke test for Key Signature Trainer. Usage: python3 tests/smoke.py [--shots DIR]"""
import sys, os, threading, http.server, functools
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = sys.argv[sys.argv.index('--shots') + 1] if '--shots' in sys.argv else None
fails = []
def ok(cond, msg):
    print(('PASS ' if cond else 'FAIL ') + msg)
    if not cond: fails.append(msg)

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
handler.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{srv.server_address[1]}/index.html'

LOGIC = r"""() => {
  const {keyMap, genLine, genFind, genSingle, letterOf, S} = window.KS;
  const errs = []; let notes = 0, reasons = {};
  const ranges = ['staff','ledger1','ledger2'];
  for (let t = 0; t < 4000; t++) {
    S.range = ranges[t % 3];
    const clef = t % 2 ? 'treble' : 'bass', f = (t % 8) - 4;
    const ctx = {clef, f};
    const useKS = t % 4 !== 0;
    const line = genLine(ctx, useKS);
    const km = useKS ? keyMap(f) : keyMap(0);
    if (line.length !== 8) errs.push('len');
    let st = {}, m = null;
    for (const n of line) {
      if (n.m !== m) { st = {}; m = n.m; }
      const L = letterOf(n.step);
      const alt = n.acc != null ? n.acc : (L in st ? st[L] : km[L]);   // "all octaves" reading
      if (n.acc != null) st[L] = n.acc;
      if (alt !== n.val) errs.push('octave-rule-dependent ' + JSON.stringify(line));
      if (![1,0,-1].includes(n.val)) errs.push('bad val');
      if (n.acc != null && !n.courtesy && n.acc === km[L] && n.reason === 'explicit') errs.push('redundant acc');
      reasons[n.reason] = (reasons[n.reason] || 0) + 1; notes++;
    }
    if (f !== 0) {
      const fl = genFind(ctx);
      const tg = fl.filter(n => n.val !== 0).length;
      if (fl.length !== 8 || tg < 3 || tg > 5) errs.push('find ' + tg);
      const s = genSingle(ctx, null);
      if (s.length !== 1) errs.push('single');
    }
  }
  S.range = 'ledger1';
  return {errs: errs.slice(0, 5), nerr: errs.length, notes, reasons};
}"""

with sync_playwright() as p:
    b = p.chromium.launch(channel='chromium')
    pg = b.new_page(viewport={'width': 1366, 'height': 768})
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.on('console', lambda m: m.type == 'error' and errors.append(m.text))
    pg.goto(URL); pg.wait_for_selector('.mode')
    r = pg.evaluate(LOGIC)
    print('reasons:', r['reasons'])
    ok(r['nerr'] == 0, f"generator: {r['notes']} notes, never depends on octave rule ({r['errs']})")
    for need in ['keysig', 'plain', 'explicit', 'carry', 'reset', 'courtesy']:
        ok(r['reasons'].get(need, 0) > 0, f'reason "{need}" occurs')
    if SHOTS: os.makedirs(SHOTS, exist_ok=True); pg.screenshot(path=f'{SHOTS}/0-home.png')

    # Mode 1: answer right, then wrong
    pg.click('.mode[data-m="1"]')
    for k in range(6):
        n = pg.evaluate("() => { const n = KS.G.notes[0]; return [KS.letterOf(n.step), n.val]; }")
        pg.click(f'.key[data-l="{n[0]}"]'); pg.click(f'.key[data-a="{n[1]}"]')
        pg.wait_for_timeout(900)
    ok(pg.inner_text('#sRight') == '6', 'mode 1: six right answers counted')
    n = pg.evaluate("() => { const n = KS.G.notes[0]; return [KS.letterOf(n.step), n.val]; }")
    wrongL = 'A' if n[0] != 'A' else 'B'
    pg.click(f'.key[data-l="{wrongL}"]'); pg.click('.key[data-a="0"]')
    ok(pg.is_visible('#contBtn') and 'You said' in pg.inner_text('#fbMsg'), 'mode 1: wrong answer shows reason')
    if SHOTS: pg.screenshot(path=f'{SHOTS}/1-mode1-wrong.png')
    pg.keyboard.press('Enter'); pg.wait_for_timeout(100)
    ok(not pg.is_visible('#contBtn'), 'mode 1: Enter continues')

    # Modes 2/3: walk a line, one deliberate miss
    for mode in (2, 3):
        pg.click('#homeBtn'); pg.click(f'.mode[data-m="{mode}"]')
        for i in range(8):
            n = pg.evaluate("() => { const G = KS.G, n = G.notes[G.cur]; return [KS.letterOf(n.step), n.val, n.reason]; }")
            if i == 3:
                pg.click('.key[data-a="1" ]' if n[1] != 1 else '.key[data-a="-1"]'); pg.click(f'.key[data-l="{n[0]}"]')
                if SHOTS: pg.screenshot(path=f'{SHOTS}/{mode}-mode{mode}-wrong.png')
                pg.click('#contBtn')
            else:
                pg.keyboard.press(n[0].lower()); pg.keyboard.press({-1: '1', 0: '2', 1: '3'}[n[1]])
                pg.wait_for_timeout(700)
        ok('7 of 8' in pg.inner_text('#fbMsg'), f'mode {mode}: line complete 7 of 8')
        if SHOTS: pg.screenshot(path=f'{SHOTS}/{mode}-mode{mode}-done.png')
        pg.keyboard.press('Enter')

    # Mode 4
    pg.click('#homeBtn'); pg.click('.mode[data-m="4"]')
    tg = pg.evaluate("() => KS.G.notes.map((n,i) => n.val !== 0 ? i : -1).filter(i => i >= 0)")
    for i in tg: pg.click(f'.tap[data-i="{i}"]')
    if SHOTS: pg.screenshot(path=f'{SHOTS}/4-find-picked.png')
    pg.click('#checkBtn')
    ok('All found' in pg.inner_text('#fbMsg'), 'mode 4: correct set accepted')
    pg.click('#checkBtn')
    pg.click('.tap[data-i="0"]'); pg.click('#checkBtn')
    if SHOTS: pg.screenshot(path=f'{SHOTS}/4-find-checked.png')

    # Class display at viewboard size, rotate instruments
    pg.set_viewport_size({'width': 1920, 'height': 1080})
    pg.click('#homeBtn'); pg.click('#settings summary'); pg.click('#classChip')
    pg.select_option('#instSel', 'rotate')
    pg.click('.mode[data-m="3"]')
    pg.click('#revealBtn')
    ok(pg.is_visible('#contBtn'), 'class display: Reveal shows answer')
    if SHOTS: pg.screenshot(path=f'{SHOTS}/5-class-reveal.png')
    pg.click('#homeBtn'); pg.click('.mode[data-m="1"]')
    if SHOTS: pg.screenshot(path=f'{SHOTS}/5-class-mode1.png')

    # Bass clef + phone width
    pg.click('#homeBtn'); pg.click('#classChip'); pg.select_option('#instSel', 'trombone')
    pg.set_viewport_size({'width': 390, 'height': 844})
    pg.click('.mode[data-m="3"]')
    if SHOTS: pg.screenshot(path=f'{SHOTS}/6-phone-bass.png', full_page=True)
    pg.reload(); pg.wait_for_selector('.mode')
    ok(pg.input_value('#instSel') == 'trombone', 'settings persist after reload')
    # ?inst= from the Dojo
    for name, want in [('Alto Saxophone', 'altosax'), ('Bass Clarinet', 'bassclar'), ('Euphonium', 'euph'), ('Percussion', 'mallets'), ('French Horn', 'horn')]:
        pg.goto(URL + '?inst=' + name.replace(' ', '%20')); pg.wait_for_selector('.mode')
        ok(pg.input_value('#instSel') == want, f'?inst={name} picks {want}')
    ok(not errors, f'no console errors {errors[:3]}')
    b.close()
srv.shutdown()
print(f'\n{len(fails)} failure(s)')
sys.exit(1 if fails else 0)
