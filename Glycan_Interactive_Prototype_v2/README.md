# Glycan Flow Simulator ― 操作型プロトタイプ v2

**先輩の公開サイトや `main` ブランチは変更していません。** 先輩のサイトと同じ簡単なネットワーク構造を使用した、独立した検証用Webアプリです。

## まず試す（GitHub初心者向け）

1. ZIPを解凍する。
2. `Glycan_Interactive_Prototype_v2` フォルダを開く。
3. **`index.html` をダブルクリック**する。インストールやサーバー起動は不要。
4. 線をクリック → スライダーを動かす → 4つの計算方法を選ぶ → 目標との差を見る。
5. 「Inverseで自動補正してみる」を押す → 「反応容量を自動補正する」を押す → 手動結果・目標・自動補正結果を比較する。

**目標は説明用の架空の固定分布（A=25%, B=20%, C=55%）です。実測値ではありません。**

## 実装したこと

- 先輩のデモに相当する10ノード・13反応エッジ、終端糖鎖A/B/Cを表示。
- 黄色は操作中のエッジ。エッジの線幅は計算された流量。Inverse後に赤くなるのは容量が補正されたE13。
- Forward: 0–200%スライダー、最大フローの再計算、UQ/CWQ/SU/LCRQの二次最適化と生成割合のリアルタイム更新。
- 結果: 固定目標と手動結果の並列棒グラフ、「目標とのズレ」をパーセンテージポイント単位で表示。
- Inverse: 手動結果のスナップショットを保持し、Python数理モデルで**事前計算・検証した**補正例（E13: 58→66、最大流量120、目標分布再現）を1クリックで表示。
- Forwardに戻ると、手動で操作していたスライダー・手法の状態を復元。
- レスポンシブ表示、キーボードによる線選択、計算失敗時のエラー表示。

## 科学的な注意事項

**この画面の数値は、ヒトRNAのTPMや糖鎖の実測値ではありません。** また、表示する目標分布は人工的に設定したものです。実際の論文に掲載された結果と混同させないため、画面にも注記しています。

- Forwardは、(1)最大流量を決める → (2)その総流量を固定し4種類の二次目的で配分するという、論文の構造に沿っています。
- 目標に近づけることは**利用者の遊び方**です。4手法そのものは目標との誤差を最小化していません。
- Inverseが保証するのは、補正容量の下で**目標を再現する最大フロー解が存在すること**です。補正した容量で再びUQ等を行っても同じ目標を再現するとは限りません。
- 自動補正は **手動操作した容量を入力として最適化していません**。基準容量を入力に事前検証した補正例を表示します。画面でそのことを明記しています。
- 目標との差は `0.5 * (|p_A-q_A|+|p_B-q_B|+|p_C-q_C|) * 100`（単位：percentage point）です。総流量0のときは未定義として「—」を表示します。

## ファイルの内容

- `index.html` ― **完成済みの1ファイル版**。ダブルクリックで起動できます。
- `template.html`, `app-demo.js`, `glycan-solver.mjs`, `inverse_fixture.json` ― 編集・開発用のソース。
- `build_offline.py` ― ソースを変更した後、`python build_offline.py` で `index.html` を再生成。
- `oracle_trust_constr.json` ― Forwardの独立数値比較基準。
- `tests/test.mjs` ― Forwardの数値テスト（Node.js）。
- `tests/test_inverse_fixture.mjs` ― Inverseの容量制約・流量保存・目標分布再現の検証。
- `tests/test_ui.py` ― 画面の操作・状態保持・スマホ表示のテスト（Playwright + Chromiumが必要）。
- `preview_desktop.png`, `preview_inverse.png`, `preview_mobile.png` ― 検証時のスクリーンショット。

## GitHubへ保存するとき（まだ公開しない）

1. `sakura2579/Glycan_Flow_Promotion` を開く。
2. ブランチが **`feature/optimization-prototype`** になっていることを確認する。
3. `Add file → Upload files` から **`Glycan_Interactive_Prototype_v2` フォルダを丸ごと**アップロードする。
4. `Commit changes` を選択する。
5. **既存の `index.html`, `app.js`, `styles.css` は上書きしない。** 今回のフォルダの中に同名の `index.html` があっても、別フォルダなら競合しません。
6. `main` にマージするのは先輩と画面・数理計算をレビューした後にする。

補足：GitHub Pagesは現状 `main` のルートを配信しているので、作業用ブランチに保存しても公開URLは変わりません。

## 検証

- `node tests/test.mjs` ― Forward: 独立解との12例比較と540条件の計算テスト。
- `node tests/test_inverse_fixture.mjs` ― Inverse: 容量・保存・最大流・目標一致。
- `python tests/test_ui.py` ― Browser UIの操作検証（Playwright環境で実施）。

論文と同じ実データの数値を再現する試作ではありません。研究発表への利用前に論文の最適化ソルバーと精度比較を行ってください。
