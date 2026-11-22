"""UI smoke test (optional dependency: pip install playwright; chromium installed)."""
from pathlib import Path
from playwright.sync_api import sync_playwright

P=Path(__file__).resolve().parents[1]
HTML=(P/'index.html').read_text(encoding='utf8')
with sync_playwright() as playwright:
    browser=playwright.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1360,'height':950})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content(HTML)
    page.wait_for_timeout(350)
    assert 'pt' in page.locator('#gapNumber').inner_text()
    initial=page.locator('#gapNumber').inner_text()
    page.locator('[aria-label="反応 E13 を選択"]').click()
    page.locator('#capacitySlider').fill('160')
    page.wait_for_timeout(350)
    assert page.locator('#capacityPercentage').inner_text()=='160%'
    page.locator('button[data-method="SU"]').click()
    page.wait_for_timeout(350)
    manual=page.locator('#gapNumber').inner_text()
    page.locator('#toInverse').click()
    page.wait_for_timeout(350)
    assert page.locator('#gapNumber').inner_text()==manual
    page.locator('#autoCorrect').click()
    page.wait_for_timeout(350)
    assert page.locator('#gapNumber').inner_text()=='0.0 pt'
    assert page.locator('#capacityChange').is_visible()
    page.locator('#toForward').click()
    page.wait_for_timeout(350)
    assert page.locator('#capacityPercentage').inner_text()=='160%'
    # Full shutdown of supply at E1 should have zero production and no misleading error score.
    page.locator('[aria-label="反応 E1 を選択"]').click()
    page.locator('#capacitySlider').fill('0')
    page.wait_for_timeout(350)
    assert page.locator('#totalFlow').inner_text()=='0.0'
    assert page.locator('#gapNumber').inner_text()=='—'
    assert not errors,errors
    small=browser.new_page(viewport={'width':390,'height':844})
    small.set_content(HTML)
    small.wait_for_timeout(350)
    dim=small.locator('body').evaluate('(e)=>({w:e.clientWidth,sw:e.scrollWidth})')
    assert dim['w']==dim['sw'],dim
    browser.close()
print('PASS: Forward, target gap, method switch, Inverse, return state, zero flow, mobile width')
