# AGENTS.md — NFC Business Card Design Rules

このリポジトリは **89 × 51 mm** のパッシブ NFC 名刺 PCB を、Python ジェネレータ + KiCad 10 で再現可能に保つプロジェクトです。エージェントはレイアウト・コピー・生成パイプラインを触る前に、ここに書いたルールに従ってください。

## 1. ボード仕様（物理）

| 項目 | 値 |
|------|-----|
| サイズ | 89 × 51 mm（クレジットカード系） |
| 層 | 2 層、板厚 **0.8 mm** |
| 仕上げ | 黒マスク、白シルク、**ENIG** |
| IC | NXP NT3H2111W0FHKH（LCSC C710403） |
| パッケージ | XQFN-8 1.6 × 1.6 mm |

### ゾーン分割（上面・左→右）

```
┌──────────────────┬───┬─────────────────────┐
│ TEXT ZONE 50 mm  │ 7 │ NFC antenna + chip  │
│ 銅なし           │mm │ 螺旋 + U1/C1        │
└──────────────────┴───┴─────────────────────┘
```

- **左 50 mm（TEXT_ZONE_W）**: 銅パターン禁止。名前・シルク・QR のみ。
- **中央 7 mm（COMP_STRIP_W）**: U1 + C1（DNP）のコンポーネント帯。
- **右**: 矩形螺旋アンテナ。`TURNS=5`、トレース 0.25 mm、ターン間ギャップ 0.30 mm。
- アンテナ外周インセット: **3 mm** 以上（`ANT_INSET_MM`）。

JLCPCB 下限は `scripts/jlcpcb_limits.py` を参照。設計値は JLC 最小の約 1.5 倍を目安にする。

## 2. ビジュアルデザインルール

### 前面（F 面）

| 要素 | レイヤ | フォント / 素材 | 配置 |
|------|--------|-----------------|------|
| 氏名 | **F.Cu + F.Mask**（ENIG） | Georgia Bold、cap 高さ 5.2 mm | 左上、`TEXT_LEFT_MM=5` |
| 肩書き 2 行 | F.SilkS（PNG） | Arial 1.6 mm | 氏名の下、`ROLES_Y0_MM=18.5` |
| QR | F.SilkS（PNG） | 白モジュール | 左列、連絡先ブロックと縦中央揃え |
| 連絡先 4 行 | F.SilkS（PNG） | Arial 1.5 mm | `CONTACT_X_MM=16.5` |
| NFC ロゴ | F.SilkS（PNG） | N マーク | アンテナ中心 |

**縦方向の並び（上→下）**: 氏名 → 肩書き → QR＋連絡先。氏名下端と肩書き上端の隙間は **≥ 1.8 mm**（`check_layout.py` で検証）。

**氏名（ENIG）の制約**

- 右端はテキストゾーン右から **≥ 8 mm** 空ける（`NAME_RIGHT_MARGIN_MM`）。
- KiCad では `bake_name_enig.py` が Pillow のインク境界に合わせて `render_cache` を配置する。
- **上揃え**（preview Y-down）。`y_kicad()` で反転しない。

**シルク文字**

- プレビューと KiCad は **同じ PNG**（`make_text_silk.py` → `roles-silk.png` / `contacts-silk.png`）を使う。ベクタ `gr_text` ベイクは使わない（フォントメトリクス差で重なるため）。
- 肩書き 2 行目は長すぎると折り返し風に見えるので、**40 文字前後**を上限目安にする。

### 背面（B 面）

- OpenStack / Kubernetes / Prometheus / OIDC の **2×2 グリッド**（`back_logo_grid()`）。
- ロゴサイズ: セル幅の 88%、上下マージン各 **5 mm**、セル間ギャップ **3 mm**。
- 編集時は KiCad で **B.SilkS を非表示**にすると、前面編集時に裏ロゴが透けて見えるのを防げる。

### プレビュー（`fab/preview.png`）

- `render_preview.py` が photoreal モックを出力。fab 確認用の正とする。
- 氏名は単色ゴールド（エンボス影なし）。fab 出力との一致を優先。

## 3. 座標系（最重要）

**すべてのシルク・テキスト・PNG 配置は preview 座標**（ボード上端から Y が増える）を使う。

| 系 | 原点 | Y の向き | 用途 |
|----|------|----------|------|
| **Preview** | 左上 | 下向きに増加 | `silk_layout.py`、プレビュー、PNG、ENIG 名 |
| レガシー bottom-origin | 左下 | 上向きに増加 | `y_kicad()` のみ（新規コードでは使わない） |

- 定数は `scripts/silk_layout.py` の `SilkLayout` / `DEFAULT` が単一の真実。
- コピー文は `scripts/card_copy.py` の `CardCopy`。
- 変更時は **preview と KiCad の両方**が同じ定数を読むこと。片方だけ手編集しない。

## 4. 生成パイプライン

### ソース・オブ・トゥルース

| 変更内容 | 編集するファイル |
|----------|------------------|
| 文言 | `scripts/card_copy.py` |
| 寸法・余白・フォントサイズ | `scripts/silk_layout.py` |
| JLC 最小/feature | `scripts/jlcpcb_limits.py` |
| アンテナターン数・配線 | `scripts/generate_kicad_project.py`（`nfc_layout()`） |

### 再生成コマンド

```bash
devbox shell          # 初回セットアップ — 詳細は SETUP.md
./task export
./task design
./task list
```

KiCad 10 が `/Applications/KiCad/` に必要（氏名の TTF ベイク）。無い場合は stroke フォントにフォールバックする。

### アセット解像度

- ロゴ・NFC マークのラスタ: **512 px** 長辺目安（4096 px は KiCad 上で巨大グレーブロックになる）。
- シルク PNG: `SILK_BITMAP_PX_PER_MM = 40`。

## 5. コード設計（kamae-py）

`scripts/kamae/` にドメイン primitives を置く。詳細は `~/.cursor/skills/kamae-py/SKILL.md`。

1. **frozen dataclass** — `SilkLayout`, `CardCopy`, `InkBounds`
2. **Branded types** — `Mm`, `PreviewY`（裸の `float` で座標意味を混ぜない）
3. **Result** — `bake_specs_raw()` など I/O 境界の手前で `Ok` / `Err`
4. **Boundary** — `require_existing_file()` でアセット欠落を早期検出
5. **PII** — メールは `Sensitive` でラップ（ログに出さない）

レイアウト計算は純関数に保ち、subprocess（pcbnew）・ファイル書き込みはパイプライン末端に集約する。

## 6. やってはいけないこと

- シルクだけ KiCad 上でドラッグして終わりにしない（次回 `generate_kicad_project.py` で上書きされる）。
- 氏名・シルクに **`y_kicad()` をかけない**（前面テキストが上下反転する）。
- ENIG 名を `gr_poly` 大量矩形や stroke フォントだけに戻さない（プレビューと幅・見た目がずれる）。
- `roles-silk.png` を使わず KiCad ベクタシルクだけに戻さない。
- U1/C1 のシルク参照を前面に出さない（`hide=True` 維持）。
- `.history/`, `.glb` をコミットしない。
- `git config` をエージェントから変更しない。

## 7. 検証

`scripts/check_layout.py` は最低限以下を確認する:

- 螺旋がテキストゾーンに入らない
- LA/LB フィードが短絡しない（FD 等 NC パッドへの貫通含む）
- LB の F.Cu がアンテナ左辺を横切らない（内側終端は B.Cu アンダーパス）
- アンテナ FP は net-tie（`net_tie_pad_groups "1,2"`）— 螺旋銅の LA↔LB は意図的
- XQFN 同一辺パッドの向き・間隔（サイドパッド長軸 = パッケージ中心方向）
- 局所 GND 島がコンポーネント帯内にあり SCL / LA バイパスとクリア
- 氏名右端マージン
- 氏名→肩書きの縦ギャップ
- 主要 fab 成果物の存在

レイアウト定数を変えたら、必ず再生成後にこのスクリプトを通す。

## 8. 関連ドキュメント

- [`SETUP.md`](SETUP.md) — devbox + uv セットアップ（1 から）
- [`README.md`](README.md) — 概要・JLC 発注・NFC 書き込み
- [`parts.md`](parts.md) — BOM 固定
- [`antenna/NOTES.md`](antenna/NOTES.md) — LC チューニング
- [`fab/ORDER_CHECKLIST.md`](fab/ORDER_CHECKLIST.md) — 発注チェックリスト
