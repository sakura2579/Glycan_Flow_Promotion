"""Produce machine-readable demo values and human-readable validation summary."""
import json
from pathlib import Path
from model import build_model, solve_stage2, solve_inverse, closest_baseline, METHODS, OBSERVED_PROFILE, SUPPLY, BASE_EDGES, TERMINALS

here=Path(__file__).resolve().parent
base=build_model()
forward={m:solve_stage2(base,m) for m in METHODS}
modified=build_model({'E13':1.4,'E3':.75,'E2':1.2})
forward_changed={m:solve_stage2(modified,m) for m in METHODS}
closest=closest_baseline(base,OBSERVED_PROFILE)
inverse=solve_inverse(base,OBSERVED_PROFILE)
corrected=build_model()
for edge_id,_,_,_ in BASE_EDGES:
 for u,v,data in corrected.graph.edges(data=True):
  if data.get('id')==edge_id: data['capacity']=inverse['capacity_after'][edge_id]
corrected.capacities[:]=[corrected.graph[u][v]['capacity'] for u,v in corrected.edges]
post_forward={m:solve_stage2(corrected,m) for m in METHODS}

def pct(d):return ', '.join(f'{t}={d[t]*100:.3f}%' for t in TERMINALS)

changes=sorted([(e,orig,inverse['capacity_after'][e],inverse['capacity_after'][e]-orig) for e,_,_,orig in BASE_EDGES],key=lambda t:-abs(t[3]))
report=['# Glycan Flow – 数理計算の検証結果','',
'対象：先輩の公開デモと同じ10ノード・13反応エッジからなる**説明用ネットワーク**。',
'容量は**架空のデモ値**です。RNA由来TPMや実測糖鎖量ではありません。',
'目的関数は2本のIEEM2026論文・ユーザー共有Forward Pythonコードに準拠して実装。',
'数値解法はSciPy SLSQPであり、論文のCVXPY/CLARABEL/OSQPとの数値一致は今後の照合事項。','',
'## Forward（基準容量）','',f'- 最大流量 F* = {forward["UQ"]["max_flow"]:.6f}',
]+[f'- {m}: {pct(forward[m]["profile"])}' for m in METHODS]+['',
'## Forward（スライダー変更例 E13 140%、E3 75%、E2 120%）','',
]+[f'- {m}: {pct(forward_changed[m]["profile"])} （F*={forward_changed[m]["max_flow"]:.4f}）' for m in METHODS]+['',
'## Inverse（固定した説明用の観測分布）','',
'- 観測として扱う固定分布 q: '+pct(OBSERVED_PROFILE),
'- 基準容量で最も観測に近い最大フロー解: '+pct(closest['profile']),
'- 補正容量によるInverse解: '+pct(inverse['profile']),
'- 補正前・補正後の最大流量：'+f'{forward["UQ"]["max_flow"]:.6f} → {inverse["max_flow"]:.6f}',
'- 変更量の大きいエッジ（上位5件）：']+[f'  - {e}: {orig:.6f} → {aft:.6f} (差 {delta:+.6f})' for e,orig,aft,delta in changes[:5]]+['',
'## Inverse補正後の容量を使ってForwardの4手法を実行','',
'**重要：Inverseが保証するのは観測分布を再現する最大フロー解の存在であり、',
'すべてのForward配分手法が観測分布を再現することではありません。**',
]+[f'- {m}: {pct(post_forward[m]["profile"])}' for m in METHODS]+['',
'## 制約の確認','',
'- Forward各手法：非負、容量制約、各中間点の流量保存、総流量が最大フローと一致',
'- Inverse：固定観測分布の再現、容量変更の最小化、同じ最大フロー値の維持',
'- 本ネットワークでsource側のカット容量120が固定され、補正後も最大流量は120を超えない',
'- すべての検査は tests/test_model.py にも自動化','',
'## 今後のWeb実装での使い方','',
'1. 同じ小規模ネットワークの見た目を残す。',
'2. Forwardはエッジ容量変更時に最大フローと4配分法を再計算。',
'3. Inverseは説明用の固定目標と事前検証された容量ベクトル・流量を表示。',
'4. ブラウザ用実装との回帰比較に demo_results.json を使用。',
'5. この成果物は**まだ公開サイトを改変せず**、検証用に独立している。',
]
(here/'VALIDATION_REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
(here/'demo_results.json').write_text(json.dumps({'metadata':{'kind':'synthetic_educational_example','source':'predecessor-demo-topology; supplied IEEM2026 manuscripts','supply':SUPPLY},'observed_profile':OBSERVED_PROFILE,'forward':forward,'forward_slider_example':forward_changed,'closest_baseline':closest,'inverse':{k:v for k,v in inverse.items() if k!='corrected_graph'},'forward_after_inverse':post_forward},ensure_ascii=False,indent=2),encoding='utf-8')
print('\n'.join(report))
