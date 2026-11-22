"""Inverseの説明用UIがfixtureの値と一致していることを検証する。"""
from pathlib import Path
from playwright.sync_api import sync_playwright

base=Path(__file__).resolve().parents[1]
html=(base/'index.html').read_text(encoding='utf-8')
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    for width,height in ((1366,768),(390,844)):
        page=browser.new_page(viewport={'width':width,'height':height})
        errors=[]
        page.on('pageerror',lambda err:errors.append(str(err)))
        page.set_content(html)
        page.locator('#capacitySlider').fill('150')
        page.locator('#toInverse').click()
        page.wait_for_timeout(160)
        assert page.locator('#inverseTargetPercentC').inner_text()=='55%'
        assert page.locator('#inverseTotalSupply').inner_text()=='120'
        assert page.locator('#inverseRequiredC').inner_text()=='66'
        assert page.locator('#inverseBaselineE13').inner_text()=='58'
        assert page.locator('#capacityChange').is_hidden()
        assert page.locator('#inverseResultNote').is_hidden()
        page.locator('#autoCorrect').click()
        page.wait_for_timeout(160)
        assert page.locator('#inverseCapBefore').inner_text()=='58'
        assert page.locator('#inverseCapAfter').inner_text()=='66'
        assert page.locator('#inverseDeltaCapacity').inner_text()=='+8（+13.8%）'
        assert page.locator('#inverseResultRequiredC').inner_text()=='66'
        assert page.locator('#inverseResultTotalFlow').inner_text()=='120'
        assert page.locator('#gapHeadline').inner_text()=='0.0'
        assert page.locator('#inverseResultNote').is_visible()
        assert '再計算結果ではありません' in page.locator('#gapDescription').inner_text()
        assert page.locator('#networkState').inner_text()=='補正後の流量'
        assert page.evaluate('document.body.scrollWidth<=window.innerWidth')
        page.locator('#backBefore').click()
        page.wait_for_timeout(150)
        assert page.locator('#capacityChange').is_hidden()
        page.locator('#toForward').click()
        page.wait_for_timeout(150)
        assert page.locator('#capacityPercentage').inner_text()=='150%'
        assert not errors,errors
        page.close()
    browser.close()
print('PASS: inverse explanation, dynamic numbers, restored Forward state, desktop/mobile overflow')
