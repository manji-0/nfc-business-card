# NFC Business Card PCB Fix Plan

この計画は、短絡、クリアランス違反、部品番号不一致を修正し、修正途中の生成物や未コミット作業を失わないための工程を定義する。

## Verdict

<!-- constrained-by ./AGENTS.md -->

現行出力は発注不可である。2026-08-02 の KiCad 10.0.4 検査では、ERC は通過したが PCB DRC は失敗している。

| 検査 | 現状 | 完了条件 |
|------|------|----------|
| KiCad DRC error | 27件 | 0件 |
| KiCad DRC warning | 12件 | 意図したものを除き0件 |
| ERC error | 0件 | 0件 |
| schematic parity | 0件 | 0件 |
| unconnected items | 0件 | 0件 |
| 軽量レイアウト検査 | 通過。ただし不十分 | 強化後も通過 |

## Detected Problems

### Cross-Net Shorting

同一層の異なるネットの配線中心線が交差している。KiCad では `tracks_crossing` として報告されているが、製造上は短絡として扱う。

| ネット | 交差位置 | PCB上の該当配線 |
|--------|----------|------------------|
| LA / VOUT | 約 `(54.80, 5.775)` | LA 水平配線と VOUT 垂直配線 |
| GND / VOUT | 約 `(52.25, 4.575)` | GND 水平配線と VOUT 垂直配線 |
| VOUT / GND | 約 `(51.55, 8.90)` | VOUT 水平配線と GND 垂直配線 |

### Clearance

- 要求設計値は 0.20 mm。
- DRCの実測値は 0.025 mm から 0.185 mm。
- 23件すべてが設計値未満。
- 5件は JLC の下限 0.127 mm 未満。
- R3 の SDA パッドと SCL ビアの穴クリアランスは 0.2436 mm で、要求 0.25 mm に届かない。
- LA/LB バスの実効間隔は 0.15 mm で、JLC下限は満たすが設計目標 0.20 mm 未満である。

### Component Identity

<!-- constrained-by ./parts.md -->

- U1 `NT3H2111W0FHKH / C710403` は対象部品と一致する。
- C1 `C301961` は 10 pF、NP0、0402 で対象部品と一致する。
- R2-R6 は設計値が 100 kOhm だが、現在の `C25744` は LCSC上で 10 kOhm 0402 ±1% である。
- R2-R6 はデフォルトDNPのため現行組立BOMには出ないが、オプション実装手順としては不正確である。

## Fixed Design Decisions

<!-- constrained-by ./antenna/NOTES.md -->

- アンテナは 5ターン、トレース 0.25 mm、ターン間ギャップ 0.30 mm、外形約29 x 45 mmを維持する。
- U1 は XQFN-8 1.6 x 1.6 mm、EPは実装しない。
- アンテナ螺旋は net付き F.Cu の LA トラックとし、内側終端は `net_tie_pad_groups "1,2"` の重なりパッドでLBへ接続する。
- no-net の螺旋銅、LA/LBを橋渡しする通常トラック、アンテナ下のGND銅箔は追加しない。
- C1 はDNPを既定とし、初回チューニング用の10 pF NP0候補を維持する。
- R2-R6 はDNPを既定とし、実装する場合だけ検証済み100 kOhm 0402 ±1%部品を指定する。
- `README.md` の6ターン記載は、生成元を変更せず、最後に現行の設計目標へ同期する。

## Worktree Preservation

### Step 0: Freeze the Dirty Worktree

現在の作業ツリーには、PCB、回路図、フットプリント、Gerber、プレビュー、スクリプトの未コミット変更がある。これらを無断で破棄しない。

実施内容:

- `git status --short` を保存する。
- `git diff --stat` と `git diff -- scripts/ nfc-business-card.kicad_pcb nfc-business-card.kicad_pro nfc-business-card.kicad_sch` を確認する。
- 既存変更が今回の修正対象か、別作業かを分類する。
- `.pi/`、一時DRCレポート、実験ファイルを修正対象のコミットから除外する。
- 意図不明の既存変更は、削除・reset・checkoutせず、そのファイルを今回のコミット対象から外す。
- 生成コマンドを実行する前に、上書き対象を確認する。特に `./task design` と `./task export` は生成物を上書きする。

保全ゲート:

- [ ] 既存の変更一覧を作業ログに残した。
- [ ] 今回変更するファイル一覧を確定した。
- [ ] 意図不明の変更をコミットに混ぜない方針を確認した。

コミット:

- 現在の作業ツリーを無断でbaselineコミットしない。
- 既存変更がすべて今回の設計変更であることを確認できた場合だけ、別途 `chore: capture PCB validation baseline` を作成する。

## Validation First

### Step 1: Add Component Invariant Checks

目的は、配線修正と部品修正を同時に行って原因を混ぜないことにある。

変更対象:

- `scripts/check_layout.py` または専用の部品検査スクリプトに、U1、C1、R2-R6のMPN、LCSC ID、値、パッケージ、DNP状態の検査を追加する。
- 100 kOhm指定とLCSC IDの不一致を自動的にエラーにする。
- C1のDNP版と10 pF版がそれぞれ正しいBOM/CPLに出ることを検査する。
- 現行の5ターン、0.25/0.30 mm、3 mmインセットを設計制約として検査する。

検査ゲート:

- [ ] 現行基板で、R2-R6の `C25744` 不一致を再現性のあるエラーとして検出する。
- [ ] U1とC1の正しい部品IDはエラーにならない。
- [ ] 配線問題の失敗と部品問題の失敗を別メッセージで識別できる。

コミット:

- `test: enforce NFC component and antenna invariants`

### Step 2: Add Exhaustive Copper Checks

現行の軽量検査はLA/LBの一部の軸方向重複しか見ておらず、VOUT/GND、VOUT/LAの交差を見逃した。配線修正前に、同じ退行を検出できる検査を先に入れる。

変更対象:

- 同一層の全ネット配線について、交差、重複、最小エッジ間隔を検査する。
- パッド、配線、ビアの銅箔間隔を同一層およびビア貫通範囲で検査する。
- ビア穴とパッド、ビア穴同士のクリアランスを検査する。
- ボード外形、テキストゾーン、アンテナゾーン、コンポーネント帯の境界を検査する。
- net-tie内部のLA/LB重なりだけを明示的な許可リストにする。
- 設計目標 0.20 mm 未満を警告ではなくエラーにする。ただしJLC下限だけを判定する項目は別に残す。
- GNDビアが両層の意図した銅箔へ接続していることを検査する。

検査ゲート:

- [ ] 現行基板で、3箇所の交差を必ず検出する。
- [ ] 0.025 mm、0.095 mm、0.125 mmの既知違反を検出する。
- [ ] 意図したアンテナnet-tieだけは許可される。
- [ ] no-net銅が存在する場合に失敗する。

コミット:

- `test: reject all-net copper crossings and tight clearances`

## Normalize Component Data

### Step 3: Correct the NC Resistor Identity

<!-- constrained-by ./parts.md -->

変更対象:

- `scripts/jlcpcb_limits.py` の `NC_TERM_R_LCSC` を、100 kOhm、0402、±1%として確認したLCSC部品へ変更する。
- `parts.md` のLCSC ID、メーカー型番、抵抗値、定格、検証日を同じ部品に揃える。
- `scripts/generate_kicad_project.py` の生成メタデータは定数から読む状態を維持し、個別のハードコードを増やさない。
- R2-R6のDNP属性、B.Cu配置、SCL/SDA/FD/VCC/VOUTからGNDへの接続意図を維持する。

検査ゲート:

- [ ] 部品検査が通過する。
- [ ] 生成前のソースに100 kOhmとLCSC IDの矛盾がない。
- [ ] 現行PCBをまだ再生成せず、配線修正と混ぜない。

コミット:

- `fix: correct NC terminator component identity`

## Repair Routing in Stages

### Step 4: Build Pure Geometry Routes

<!-- constrained-by ./AGENTS.md -->

配線座標をPCBファイルへ直接編集せず、`scripts/generate_kicad_project.py` の生成元で修正する。

設計手順:

- `nfc_layout()` が返すアンテナ、U1、C1の座標を固定条件として扱う。
- `feed_routes()` のLA/LB RF経路を、既に成立しているアンテナnet-tieとLB B.Cuアンダーパスを壊さない範囲で再配置する。
- `nc_terminator_routes()` の5本のNC経路を、ネットごとの予約チャネルに分ける。
- VOUTの長いF.Cu配線を廃止し、LA、GND、U1パッド、SCLビアを横切らない層遷移を設計する。
- GNDトランクとVOUTトランクは、同一層で交差しないようにする。
- U1直近のF.Cuスタブは、対象パッド以外のU1パッド、他ネットのビア、他ネット配線から0.20 mm以上離す。
- NC信号のB.Cu行配線は、隣接行のパッドとビアを含めて0.20 mm以上離す。
- すべてのNC経路をコンポーネント帯内に収め、アンテナ左辺のkeep-outへ入れない。
- GND遷移は、B.Cuトランクの実配線終端とビア中心を一致させる。未接続の冗長ビアは削除する。

検査ゲート:

- [ ] まず純粋なルートデータを出力し、同一層の全交差が0件である。
- [ ] 全パッド、配線、ビアの最小銅箔間隔が0.20 mm以上である。
- [ ] ビア穴クリアランスが0.25 mm以上である。
- [ ] 既知のLA/VOUT、GND/VOUT、VOUT/GNDの交差が消えている。

コミット:

- `fix: reroute component strip without cross-net tracks`

### Step 5: Pass KiCad DRC on Generated PCB

変更対象:

- `./task design` を実行して、スクリプトからPCB、回路図、フットプリント、プレビューを再生成する。
- `./task check` を実行し、KiCad 10.0.4でERC、DRC、schematic parity、unconnected itemsを検査する。
- DRCのerrorだけでなく、warningを全件確認する。
- `via_dangling`、`lib_footprint_mismatch`、背面フィールドの警告を個別に解消または意図を記録する。

検査ゲート:

- [ ] `./task design` が終了コード0で完了する。
- [ ] DRC errorが0件である。
- [ ] DRC warningが0件、または発注前に許可した理由がある。
- [ ] ERC error、parity、unconnected itemsがすべて0件である。
- [ ] `fab/kicad-drc.json` の生成日時が今回の実行時刻になっている。

コミット:

- 配線修正と同じコミットに生成物を混ぜず、検査が通った後に次の同期コミットへ進む。

## Sync Outputs and Documentation

### Step 6: Synchronize Source and Outputs

<!-- constrained-by ./README.md -->

生成物はソース修正が検査を通った後にだけ更新する。

実施内容:

- `./task design` の出力を確認する。
- `./task fab` を実行し、Gerber、ドリル、BOM、CPL、プレビューを更新する。
- `fab/bom.csv` はC1 DNP版、`fab/bom-c1.csv` はC1 C301961版になっていることを確認する。
- `fab/positions.csv` と `fab/positions-c1.csv` にDNP部品が出ていないことを確認する。
- READMEのアンテナ表記を、生成元と `antenna/NOTES.md` の5ターン、0.25/0.30 mmへ揃える。
- `fab/ORDER_CHECKLIST.md` のU1、C1、基板仕様、検査コマンドを現行出力と照合する。
- transientな `*.rpt`、`fab/kicad-drc.json`、`fab/kicad-erc.json`、`.pi/` はコミット対象にしない。ただし既存の追跡状態を確認してから判断する。

検査ゲート:

- [ ] `git diff --check` が通る。
- [ ] GerberのEdge.Cutsが89 x 51 mmである。
- [ ] 基板厚0.8 mm、2層、黒マスク、白シルク、ENIGの出力条件を確認した。
- [ ] F.Cuアンテナ、B.Cuアンダーパス、GND島、ENIG名の位置をプレビューとGerberで確認した。
- [ ] BOM/CPLの部品IDがソース、PCB、CSVで一致する。

コミット:

- `chore: regenerate verified fabrication outputs`

### Step 7: Independent Pre-Order Review

<!-- constrained-by ./fab/ORDER_CHECKLIST.md -->

生成パイプラインとは別に、発注者が以下を確認する。

- [ ] KiCad DRC画面で除外・無視設定を確認した。
- [ ] 3DまたはGerberビューで、短絡経路がないことを確認した。
- [ ] U1のピン1マークとC1の配置方向を確認した。
- [ ] JLCPCBのオンラインDFMを実行した。
- [ ] U1がC710403、C1 DNP版またはC301961版の選択が正しい。
- [ ] R2-R6を注文BOMへ誤って追加していない。

コミット:

- レポートのみの場合はコミットしない。
- 追加修正が出た場合は、該当するStepへ戻り、新しい修正コミットを作成する。

## Commit Policy

各コミットは1つの責務だけを持たせる。生成物の更新を先行させない。

| 順序 | コミット | 主なファイル | 必須ゲート |
|------|----------|--------------|------------|
| 1 | `docs: add staged PCB fix plan` | `FIX_PLAN.md` | Markdown構文、依存関係確認 |
| 2 | `test: enforce NFC component and antenna invariants` | 検査スクリプト | 部品・アンテナ制約を検出 |
| 3 | `test: reject all-net copper crossings and tight clearances` | 検査スクリプト | 現行既知違反を検出 |
| 4 | `fix: correct NC terminator component identity` | `parts.md`, `scripts/jlcpcb_limits.py` | 部品検査通過 |
| 5 | `fix: reroute component strip without cross-net tracks` | `scripts/generate_kicad_project.py` | 交差・クリアランス検査通過 |
| 6 | `chore: regenerate verified fabrication outputs` | PCB、回路図、フットプリント、fab成果物 | `./task check`、BOM/CPL照合 |
| 7 | 必要時のみ追加修正 | 最小範囲 | Step 4以降の該当ゲート |

コミット前に必ず以下を実行する。

- `git status --short`
- `git diff --check`
- `git diff --stat`
- ステージしたファイルだけを対象にした `git diff --cached --check`
- コミットメッセージと変更責務の一致確認

禁止事項:

- `git reset --hard`、`git checkout --`、force pushを使わない。
- 未確認の既存変更を削除しない。
- PCBをKiCad上で直接編集して生成元へ反映しない。
- DRC違反を除外設定で隠して合格扱いにしない。
- 生成されたPCBだけを修正し、次回生成で消える変更を残さない。

## Recovery Procedure

各ステップでゲートが失敗した場合は、次のステップへ進まない。

- 失敗したコマンド、生成日時、エラー件数、座標を記録する。
- 直前のコミットと現在の差分を比較する。
- 修正対象を1つの責務に限定する。
- 生成物を手編集せず、生成元を修正して再生成する。
- 既知の違反件数が増えた場合は、原因を切り分けるまでコミットしない。
- 既にコミット済みのステップへ戻す場合はrevertを新しいコミットとして行い、履歴を書き換えない。

## Summary

<!-- derived-from #verdict -->
<!-- derived-from #detected-problems -->
<!-- derived-from #validation-first -->
<!-- derived-from #normalize-component-data -->
<!-- derived-from #repair-routing-in-stages -->
<!-- derived-from #sync-outputs-and-documentation -->

最初に検査を強化し、次に部品情報を正規化し、その後に生成元の配線を直す。最後にKiCadとfab成果物を再生成して独立レビューを通す。この順序により、配線を直している間に部品IDや生成物の古さが混ざることを防ぐ。

## Conclusion

<!-- derived-from #summary -->

この計画の完了条件は、ソース生成、全ネット銅箔検査、KiCad DRC/ERC、BOM/CPL、Gerber、発注チェックリストが同じ部品仕様と座標制約を示すことである。全ゲートが通るまで発注用zipを更新済みとは扱わない。
