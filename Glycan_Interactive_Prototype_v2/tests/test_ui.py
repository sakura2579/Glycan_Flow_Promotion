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
    assert 'E13' in page.locator('#firstTipTitle').inner_text()
    assert page.locator('#selectedEdgeLabel').inner_text().startswith('反応 E13')
    # The recommended first step must improve the real calculated gap.
    page.locator('#capacitySlider').fill('150')
    page.wait_for_timeout(350)
    improved=float(page.locator('#gapHeadline').inner_text())
    assert improved < float(initial.replace(' pt','')), (initial,improved)
    assert '近づきました' in page.locator('#changeFeedback').inner_text(), page.locator('#changeFeedback').inner_text()
    assert '4手法を同じ初期容量' in page.locator('#methodPrompt').inner_text()
    # Comparison always uses baseline, and must not modify edited slider or method.
    page.locator('#compareMethods').click()
    page.wait_for_timeout(200)
    assert page.locator('#methodComparison').is_visible()
    assert page.locator('.compare-item').count()==4
    assert page.locator('#capacityPercentage').inner_text()=='150%'
    assert page.locator('button[data-method="CWQ"]').get_attribute('aria-pressed')=='true'
    a=page.locator('.compare-values').all_inner_texts()
    assert all('A ' in v and 'B ' in v and 'C ' in v for v in a),a
    page.locator('#compareMethods').click()
    assert not page.locator('#methodComparison').is_visible()
    assert page.locator('#capacityPercentage').inner_text()=='150%'
    assert '100%（基準）' in page.locator('.range-ticks').inner_text()
    page.locator('button[data-method="SU"]').click()
    page.wait_for_timeout(350)
    assert '現在の容量で再計算' in page.locator('#methodPrompt').inner_text()
    page.locator('#reset').click()
    page.wait_for_timeout(350)
    assert page.locator('#capacityPercentage').inner_text()=='100%'
    assert '初期状態に戻しました' in page.locator('#changeFeedback').inner_text()
    # Moving the same slider in the other direction must produce non-encouraging feedback.
    page.locator('#capacitySlider').fill('50')
    page.wait_for_timeout(350)
    assert '遠ざかりました' in page.locator('#changeFeedback').inner_text()
    page.locator('#reset').click()
    page.wait_for_timeout(200)
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
print('PASS: guided first action, progress feedback, method help, Forward, Inverse, return state, zero flow, mobile width')
