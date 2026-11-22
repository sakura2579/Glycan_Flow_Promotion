"""Embed the numerics and UI in one double-clickable HTML (no external libraries)."""
from pathlib import Path
import json
P = Path(__file__).resolve().parent
solver=(P/'glycan-solver.mjs').read_text(encoding='utf-8').replace('export const ','const ').replace('export function ','function ')
solver+='\nwindow.GlycanForward={BASE_EDGES,METHODS,INVERSE_TARGET,SUPPLY_CAPACITY,capacitiesFromPercent,maxFlow,objectiveWeights,validateForwardResult,solveForward};\n'
fixture=json.loads((P/'inverse_fixture.json').read_text(encoding='utf-8'))
math_script='<script>\n(()=>{\n'+solver+'\nwindow.GlycanInverseFixture='+json.dumps(fixture,ensure_ascii=False,separators=(',',':'))+';\n})();\n</script>'
ui_script='<script>\n(()=>{\n'+(P/'app-demo.js').read_text(encoding='utf-8')+'\n})();\n</script>'
html=(P/'template.html').read_text(encoding='utf-8').replace('<!-- SOLVER_AND_FIXTURE -->',math_script).replace('<!-- UI_LOGIC -->',ui_script)
(P/'index.html').write_text(html,encoding='utf-8')
print('Built',P/'index.html')
