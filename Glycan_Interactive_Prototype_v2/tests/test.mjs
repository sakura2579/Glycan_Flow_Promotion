import assert from 'node:assert/strict';
import fs from 'node:fs';
import {solveForward,capacitiesFromPercent,maxFlow,BASE_EDGES} from '../glycan-solver.mjs';
const oracle=JSON.parse(fs.readFileSync(new URL('../oracle_trust_constr.json',import.meta.url),'utf8'));
const cases={baseline:{},slider_example:{E13:140,E3:75,E2:120},zero_e13:{E13:0}};
let compareCount=0;
for(const [name,percent] of Object.entries(cases)){
  for(const method of ['UQ','CWQ','SU','LCRQ']){
    const calc=solveForward(percent,method);
    const reference=oracle.cases[name][method];
    assert.ok(Math.abs(calc.maxFlow-reference.maxFlow)<1e-7,`${name} ${method} maxflow`);
    for(const terminal of ['A','B','C']){
      assert.ok(Math.abs(calc.profile[terminal]-reference.profile[terminal])<1e-4,`${name} ${method} ${terminal}: ${calc.profile[terminal]} != ${reference.profile[terminal]}`);
    }
    for(const [edge,referenceFlow] of Object.entries(reference.flows)){
      assert.ok(Math.abs(calc.flows[edge]-referenceFlow)<0.025,`${name} ${method} ${edge} ${calc.flows[edge]} != ${referenceFlow}`);
    }
    compareCount++;
  }
}
let scenarios=0, maxIterations=0;
for(const pct of [0,10,35,75,100,150,200])for(const id of ['E2','E3','E7','E11','E13'])for(const method of ['UQ','CWQ','SU','LCRQ']){
  const result=solveForward({[id]:pct},method);
  assert.ok(result.maxFlow>=-1e-8);
  if(pct===0&&id==='E13') assert.ok(Math.abs(result.profile.C)<1e-7);
  maxIterations=Math.max(maxIterations,result.iterations);
  scenarios++;
}
// Repeatable, varied dual edits; simulates arbitrary slider usage.
let seed=1729;
function rnd(){seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;}
for(let i=0;i<400;i++){
  const e1=BASE_EDGES[Math.floor(rnd()*BASE_EDGES.length)][0];
  let e2=BASE_EDGES[Math.floor(rnd()*BASE_EDGES.length)][0];
  if(e1===e2)e2='E13';
  const percent={[e1]:Math.round(rnd()*200),[e2]:Math.round(rnd()*200)};
  const result=solveForward(percent,['UQ','CWQ','SU','LCRQ'][i%4]);
  maxIterations=Math.max(maxIterations,result.iterations);
  scenarios++;
}
console.log(`PASS: ${compareCount} independent-oracle comparisons; ${scenarios} slider combinations; max QP iterations ${maxIterations}`);
