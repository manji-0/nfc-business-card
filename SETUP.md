# セットアップガイド（devbox + uv）

このリポジトリを **1 から** 動かす手順です。Python 依存は **uv**、システムツールは **devbox** で揃えます。KiCad は別途インストールが必要です。

## 前提

| ツール | 用途 |
|--------|------|
| [devbox](https://www.jetify.com/devbox) | Python 3.12 / uv / rsvg-convert を隔離インストール |
| [uv](https://docs.astral.sh/uv/) | Python 仮想環境と pip 依存（Pillow, qrcode） |
| **KiCad 10+** | PCB 編集・Gerber 出力・ENIG 名の TTF ベイク |

macOS では KiCad を [公式サイト](https://www.kicad.org/download/) から入れるのが確実です（devbox の `kicad` パッケージは環境によっては入らないことがあります）。

## 1. リポジトリを取得

```bash
git clone https://github.com/manji-0/nfc-business-card.git
cd nfc-business-card
```

## 2. devbox を入れる（未導入の場合）

```bash
curl -fsSL https://get.jetify.com/devbox | bash
```

または [devbox インストール手順](https://www.jetify.com/devbox/docs/installing_devbox/) を参照。

## 3. 開発シェルを起動

```bash
devbox shell
```

初回は Nix パッケージのダウンロードと `uv sync` が走り、`.venv/` が作られます。

シェル内で確認:

```bash
python --version    # 3.12.x
uv --version
rsvg-convert --version
```

## 4. KiCad をインストール

### macOS

1. KiCad 10 を `/Applications/KiCad/` にインストール
2. 確認:

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli version
```

### Linux / カスタムパス

`kicad-cli` が PATH にあるか、環境変数で指定:

```bash
export KICAD_CLI=/path/to/kicad-cli
export KICAD_PYTHON=/path/to/kicad-python   # pcbnew 用（任意）
export KICAD_SITE=/path/to/kicad/site-packages
```

## 5. フォント（シルク・ENIG 名）

レイアウトは **Georgia Bold**（氏名）と **Arial**（シルク）を使います。

- **macOS**: システムフォントをそのまま利用（追加不要）
- **Linux**: `fonts-liberation` 等を入れ、必要なら `scripts/layout_metrics.py` / `text_silk.py` のフォントパスを変更

## 6. パイプラインを実行

devbox シェル内:

```bash
./task list
./task design          # アセット → KiCad → プレビュー → チェック
./task export          # 上記 + Gerber zip（KiCad CLI 必須）
```

devbox のショートカット:

```bash
devbox run task
devbox run design
devbox run export
```

## 7. 成果物

| 出力 | パス |
|------|------|
| KiCad プロジェクト | `nfc-business-card.kicad_pro` |
| プレビュー画像 | `fab/preview.png` |
| JLC 用 Gerber zip | `fab/nfc-business-card-gerbers.zip` |
| BOM / CPL | `fab/bom.csv`, `fab/positions.csv` |

## トラブルシュート

### `kicad-cli not found`

KiCad をインストールするか `KICAD_CLI` を設定してから `./task fab` を再実行。

### `Georgia Bold` / `Arial` not found

macOS 以外ではフォントパスを確認。`./task design` の前半（PNG 生成）は通っても `generate_kicad_project` の ENIG ベイクで警告が出る場合は KiCad ストロークフォントにフォールバックします。

### `rsvg-convert not found`

`devbox shell` 内で実行しているか確認。devbox の `librsvg` パッケージが `rsvg-convert` を提供します。

### uv / .venv を手動で更新

```bash
uv sync
uv add package-name   # 依存を増やす場合
```

## 最小コマンドまとめ

```bash
git clone https://github.com/manji-0/nfc-business-card.git
cd nfc-business-card
devbox shell
# KiCad 10 をインストール（macOS）
./task export
```
