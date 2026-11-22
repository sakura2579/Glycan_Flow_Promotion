/**
 * Browser/Node-compatible, dependency-free demonstrator of the two-stage
 * forward network-flow optimization in the user's supplied Forward paper.
 * Educational toy network and capacities; not biological / not measured TPM.
 * THIS IS A VALIDATION PROTOTYPE AND IS NOT INTEGRATED INTO THE PUBLIC SITE.
 */
export const BASE_EDGES = Object.freeze([
  ['E1','input','core',120],['E2','core','high',46],
  ['E3','core','branch',74],['E4','core','stall',34],
  ['E5','high','branch',44],['E6','high','A',42],
  ['E7','branch','extend',58],['E8','branch','finish',38],
  ['E9','stall','finish',40],['E10','extend','A',26],
  ['E11','extend','B',60],['E12','finish','B',36],
  ['E13','finish','C',58],
]);
export const METHODS = Object.freeze(['UQ','CWQ','SU','LCRQ']);
export const INVERSE_TARGET = Object.freeze({A:0.25,B:0.20,C:0.55});
export const SUPPLY_CAPACITY = 120;
const N=BASE_EDGES.length;
const NON_TERMINALS = ['input','core','high','branch','stall','extend','finish'];
const ID_INDEX=Object.fromEntries(BASE_EDGES.map((e,i)=>[e[0],i]));
const PROFILES = {A:['E6','E10'],B:['E11','E12'],C:['E13']};
const EQ=NON_TERMINALS.map(node=>BASE_EDGES.map(e=>Number(e[1]===node)-Number(e[2]===node)));
function maxabs(v){return Math.max(0,...v.map(Math.abs));}
function dot(a,b){let s=0; for(let i=0;i<a.length;i++)s+=a[i]*b[i];return s;}
function clip(x,low,high){return Math.max(low,Math.min(high,x));}
function matrixSolve(A,b){
  // Small dense Gaussian solver with partial pivoting.
  const n=b.length, aug=A.map((r,i)=>[...r,b[i]]);
  for(let i=0;i<n;i++){
    let k=i;for(let j=i+1;j<n;j++)if(Math.abs(aug[j][i])>Math.abs(aug[k][i])) k=j;
    if(Math.abs(aug[k][i])<1e-14)throw new Error('Linear algebra: singular KKT projection');
    [aug[k],aug[i]]=[aug[i],aug[k]];
    const p=aug[i][i];for(let z=i;z<=n;z++)aug[i][z]/=p;
    for(let j=0;j<n;j++)if(j!==i){const v=aug[j][i];for(let z=i;z<=n;z++)aug[j][z]-=v*aug[i][z];}
  }
  return aug.map(r=>r[n]);
}
export function capacitiesFromPercent(percent={}){
  const bad=Object.keys(percent).filter(key=>!(key in ID_INDEX));
  if(bad.length)throw new Error(`Unknown edges: ${bad.join(',')}`);
  return BASE_EDGES.map(([name,, ,base])=>{
    const val=percent[name] ?? 100;
    if(!Number.isFinite(val)||val<0||val>200)throw new Error(`Invalid slider % for ${name}`);
    return base*(val/100);
  });
}
export function maxFlow(cap){
  // Edmonds-Karp with residual graph; the only source edge has capacity 120.
  if(!Array.isArray(cap)||cap.length!==N||cap.some(v=>!Number.isFinite(v)||v<0)) throw new Error('Bad capacities');
  const nodes=['s',...NON_TERMINALS,'A','B','C','t'];
  const ids=Object.fromEntries(nodes.map((n,i)=>[n,i]));
  const adj=nodes.map(()=>[]),bioArcs=[];
  const addArc=(a,b,c)=>{
    const f={to:ids[b],cap:c,rev:adj[ids[b]].length};
    const r={to:ids[a],cap:0,rev:adj[ids[a]].length};
    adj[ids[a]].push(f); adj[ids[b]].push(r);return f;
  };
  addArc('s','input',SUPPLY_CAPACITY);
  BASE_EDGES.forEach((e,i)=>bioArcs.push({arc:addArc(e[1],e[2],cap[i]),original:cap[i]}));
  for(const terminal of ['A','B','C'])addArc(terminal,'t',SUPPLY_CAPACITY);
  let F=0;
  while(true){
    const prev=new Array(nodes.length).fill(null),q=[ids.s];prev[ids.s]=[-1,-1];
    for(let h=0;h<q.length&&prev[ids.t]===null;h++){
      const u=q[h];for(let j=0;j<adj[u].length;j++){
        const e=adj[u][j];if(e.cap>1e-10&&prev[e.to]===null){prev[e.to]=[u,j];q.push(e.to);}
      }
    }
    if(prev[ids.t]===null)break;
    let push=Infinity;for(let v=ids.t;v!==ids.s;){const [u,j]=prev[v];push=Math.min(push,adj[u][j].cap);v=u;}
    for(let v=ids.t;v!==ids.s;){const [u,j]=prev[v],e=adj[u][j];e.cap-=push;adj[v][e.rev].cap+=push;v=u;}
    F+=push;
  }
  return {value:F, flows:bioArcs.map(x=>x.original-x.arc.cap)};
}
export function objectiveWeights(cap,method){
  if(!METHODS.includes(method))throw new Error(`Unknown method: ${method}`);
  const sum={};
  for(let i=0;i<N;i++)if(cap[i]>1e-12){const from=BASE_EDGES[i][1];sum[from]=(sum[from]||0)+cap[i];}
  return BASE_EDGES.map((e,i)=>{
    if(cap[i]<=1e-12)return 0;
    if(method==='UQ')return 1;
    if(method==='CWQ')return 1/cap[i];
    if(method==='SU')return 1/cap[i]**2;
    return sum[e[1]]/cap[i];
  });
}
export function validateForwardResult(cap,result,{tolerance=1e-4}={}){
  const x=result.flowVector, F=result.maxFlow;
  const errors={
    negative:Math.max(0,...x.map(v=>-v)),
    capacity:Math.max(0,...x.map((v,i)=>v-cap[i])),
    conservation:maxabs(EQ.map((r,i)=>dot(r,x)-(i===0?F:0))),
    profileSum:Math.abs(Object.values(result.profile).reduce((s,v)=>s+v,0)-(F<=1e-10?0:1)),
    optimalTotal:Math.abs(maxFlow(cap).value-F),
  };
  if(Object.values(errors).some(v=>!Number.isFinite(v)||v>tolerance))throw new Error(`Flow invalid: ${JSON.stringify(errors)}`);
  return errors;
}
function profileFromFlows(x,F){
  return Object.fromEntries(Object.entries(PROFILES).map(([term,ids])=>[term,F<=1e-10?0:ids.reduce((s,id)=>s+x[ID_INDEX[id]],0)/F]));
}
/**
 * Convex box-constrained equality QP via split ADMM. Its projection step
 * enforces conservation and fixed maximum-flow value (within numerical error).
 * Returns only after checking primal/dual residuals, or fails closed.
 * The returned distribution is a numerical optimum, NOT a fabricated slider rule.
 */
export function solveForward(percent={},method='CWQ',options={}){
  if(!METHODS.includes(method))throw new Error(`Unknown method: ${method}`);
  const cap=capacitiesFromPercent(percent);
  const {value:F,flows:feasible}=maxFlow(cap);
  if(F<=1e-10){const zeros=new Array(N).fill(0);const output={method,maxFlow:0,flowVector:zeros,flows:Object.fromEntries(BASE_EDGES.map((e,i)=>[e[0],0])),profile:{A:0,B:0,C:0},iterations:0};validateForwardResult(cap,output);return output;}
  const raw=objectiveWeights(cap,method);
  const scale=Math.max(...raw,1e-12),w=raw.map(v=>v/scale);
  // Keep augmented penalty moderately high for numerical stability.
  const rho=options.rho ?? 0.25;
  const limit=options.maxIterations ?? 20000;
  const eps=options.epsilon ?? 1e-7;
  const d=w.map(v=>1/(2*v+rho));
  const gram=EQ.map(ai=>EQ.map(aj=>ai.reduce((s,v,k)=>s+v*d[k]*aj[k],0)));
  const b=[F,...new Array(EQ.length-1).fill(0)];
  let x=[...feasible],z=[...feasible],u=new Array(N).fill(0);
  let iterations=0,primal=Infinity,dual=Infinity;
  for(let iteration=0;iteration<limit;iteration++){
    iterations=iteration+1;
    const rhs=z.map((v,i)=>rho*(v-u[i]));
    const dRhs=rhs.map((v,i)=>v*d[i]);
    const lam=matrixSolve(gram,EQ.map((r,i)=>dot(r,dRhs)-b[i]));
    x=dRhs.map((v,i)=>v-d[i]*EQ.reduce((s,r,j)=>s+r[i]*lam[j],0));
    const prev=z;
    z=x.map((v,i)=>clip(v+u[i],0,cap[i]));
    u=u.map((v,i)=>v+x[i]-z[i]);
    primal=maxabs(x.map((v,i)=>v-z[i]));
    dual=maxabs(z.map((v,i)=>rho*(v-prev[i])));
    if(primal<=eps&&dual<=eps)break;
  }
  if(primal>Math.max(eps*5,5e-7)||dual>Math.max(eps*5,5e-7)){
    throw new Error(`Forward QP did not converge for ${method}: ${JSON.stringify({primal,dual,iterations,F})}`);
  }
  const result={method,maxFlow:F,flowVector:x,flows:Object.fromEntries(BASE_EDGES.map((e,i)=>[e[0],x[i]])),profile:profileFromFlows(x,F),iterations,primalResidual:primal,dualResidual:dual,objective:dot(raw,x.map(v=>v*v))};
  validateForwardResult(cap,result);
  return result;
}
