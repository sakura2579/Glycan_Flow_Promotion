import fs from 'node:fs';
import assert from 'node:assert/strict';
import {BASE_EDGES, maxFlow, SUPPLY_CAPACITY} from '../glycan-solver.mjs';
const fixture=JSON.parse(fs.readFileSync(new URL('../inverse_fixture.json', import.meta.url),'utf8'));
const ids=BASE_EDGES.map(x=>x[0]);
const caps=ids.map(id=>fixture.correctedCapacity[id]);
const actual=maxFlow(caps).value;
assert(Math.abs(actual-120)<1e-8,'corrected maximum flow must remain 120');
const flows=fixture.inverseFlows;
for(const id of ids){assert(flows[id]>-1e-7 && flows[id]<=fixture.correctedCapacity[id]+1e-7, `capacity violation ${id}`)}
for(const node of ['core','high','branch','stall','extend','finish']){
 const into=BASE_EDGES.filter(e=>e[2]===node).reduce((s,e)=>s+flows[e[0]],0);
 const out=BASE_EDGES.filter(e=>e[1]===node).reduce((s,e)=>s+flows[e[0]],0);
 assert(Math.abs(into-out)<1e-8,`conservation violation ${node}`);
}
assert(Math.abs(flows.E1-SUPPLY_CAPACITY)<1e-8);
for(const k of ['A','B','C']){
 const terminalFlow=BASE_EDGES.filter(e=>e[2]===k).reduce((s,e)=>s+flows[e[0]],0);
 assert(Math.abs(terminalFlow/120-fixture.target[k])<1e-8,`target violation ${k}`);
}
const changed=ids.filter(id=>Math.abs(fixture.baselineCapacity[id]-fixture.correctedCapacity[id])>1e-6);
assert.deepEqual(changed,['E13']);
assert(Math.abs(fixture.correctedCapacity.E13-66)<1e-8);
console.log('PASS: inverse fixed fixture | constraints | unchanged maximum flow | observed profile | E13 only');
