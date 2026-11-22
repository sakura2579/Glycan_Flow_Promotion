"""Check compact desktop Forward fits without scrolling and stays interactive."""
from pathlib import Path
from playwright.sync_api import sync_playwright
p = Path(__file__).resolve().parents[1]
html = (p / 'index.html').read_text(encoding='utf-8')
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    for width, height in [(1280,720),(1366,768),(1829,864),(1920,1080)]:
        page = browser.new_page(viewport={'width':width,'height':height})
        page.set_content(html)
        page.wait_for_timeout(150)
        extents=page.evaluate('''() => ({scrollHeight:document.documentElement.scrollHeight,
            scrollWidth:document.documentElement.scrollWidth, height:innerHeight,width:innerWidth})''')
        assert extents['scrollHeight'] <= height, (width,height,extents)
        assert extents['scrollWidth'] <= width, (width,height,extents)
        for sel in ['#network','#capacitySlider','#methods','#distribution','#toInverse']:
            r = page.locator(sel).bounding_box()
            assert r is not None and r['y']>=0 and r['y']+r['height']<=height,(width,height,sel,r)
        page.locator('#capacitySlider').fill('150')
        page.wait_for_timeout(100)
        assert page.locator('#capacityPercentage').inner_text() == '150%'
        page.locator('#compareMethods').click()
        assert page.locator('#methodComparison').is_visible()
        assert page.evaluate('document.documentElement.scrollHeight') <= height
        page.locator('#compareMethods').click()
        assert page.locator('#capacityPercentage').inner_text() == '150%'
        page.locator('#toInverse').click()
        page.wait_for_timeout(100)
        assert page.locator('#inverseControl').is_visible()
        page.locator('#toForward').click()
        page.wait_for_timeout(100)
        assert page.locator('#capacityPercentage').inner_text() == '150%'
        page.close()
    phone=browser.new_page(viewport={'width':390,'height':844})
    phone.set_content(html)
    assert phone.evaluate('document.documentElement.scrollWidth')<=390
    phone.locator('#capacitySlider').fill('150')
    phone.wait_for_timeout(100)
    assert phone.locator('#capacityPercentage').inner_text()=='150%'
    browser.close()
print('PASS: 1280x720 / 1366x768 / 1829x864 / 1920x1080 without Forward scrolling, responsive and functional')
