# ClaudeCode 初回指示 — UN AI Hackathon 2026 デモフロント

---

## ペーストしてそのまま使える初回プロンプト

```
以下の仕様書に基づいて、UN AI Hackathon 2026のデモ用Webアプリを作成してください。

---

# プロジェクト概要

UN主催のハッカソン「Global Hackathon on AI for Digital Trade Regulatory Analysis」の審査提出用デモです。
各国の法令文書をAIで自動収集・解析し、UN基準（RDTII Pillar 6/7）にマッピングするRAGシステムのフロントエンドです。
本番データではなくデモデータで動作します。

---

# 技術スタック

- フレームワーク：Next.js 14（App Router）
- スタイリング：Tailwind CSS + shadcn/ui
- 言語：TypeScript
- バックエンド：Next.js API Routes（後でFastAPIに差し替えられるよう設計）
- データ：モックデータ（JSONファイル）
- 多言語：next-intl（英語/日本語切り替え）
- パッケージマネージャー：npm

---

# 画面構成（4画面）

## 1. ダッシュボード（/）
- 収集済み文書数、対象国数、マッピング済み条文数などの統計カード
- 最近追加された文書一覧（国旗・文書名・Pillar・信頼スコア）
- システムステータス表示

## 2. 法令検索・引用表示（/search）
- 検索バー（キーワード入力）
- フィルター：国、言語、Pillar 6 / Pillar 7
- 検索結果一覧（文書名・国・条番号・スニペット・信頼スコア）
- 結果クリックで詳細モーダル表示

## 3. 監査ビュー（/audit）
- 左右分割レイアウト
- 左：抽出されたスニペット（条文・引用・Pillarタグ・信頼スコア）
- 右：元文書のプレビュー（該当箇所ハイライト）
- 下部：人間レビュー用のApprove / Flag ボタン

## 4. Pillarマッピング結果（/mapping）
- 対象国一覧テーブル
- 各国のPillar 6 / Pillar 7 対応状況をバッジで表示
- 詳細展開で該当条文・引用を表示
- CSVエクスポートボタン（モック）

---

# モックデータ仕様

`/src/data/mock/` 以下に以下のJSONを作成：

## documents.json（法令文書一覧）
```json
[
  {
    "id": "doc_001",
    "country": "Japan",
    "country_code": "JP",
    "language": "ja",
    "title": "個人情報の保護に関する法律",
    "title_en": "Act on the Protection of Personal Information",
    "source_url": "https://laws.e-gov.go.jp/law/415AC0000000057",
    "crawled_at": "2026-05-10",
    "pillar": "Pillar 7",
    "status": "indexed"
  },
  {
    "id": "doc_002",
    "country": "Thailand",
    "country_code": "TH",
    "language": "th",
    "title": "พระราชบัญญัติคุ้มครองข้อมูลส่วนบุคคล",
    "title_en": "Personal Data Protection Act B.E. 2562",
    "source_url": "https://www.ratchakitcha.soc.go.th",
    "crawled_at": "2026-05-09",
    "pillar": "Pillar 7",
    "status": "indexed"
  },
  {
    "id": "doc_003",
    "country": "Kenya",
    "country_code": "KE",
    "language": "en",
    "title": "Data Protection Act, 2019",
    "title_en": "Data Protection Act, 2019",
    "source_url": "https://www.kenyalaw.org",
    "crawled_at": "2026-05-08",
    "pillar": "Pillar 7",
    "status": "indexed"
  },
  {
    "id": "doc_004",
    "country": "Singapore",
    "country_code": "SG",
    "language": "en",
    "title": "Personal Data Protection Act 2012",
    "title_en": "Personal Data Protection Act 2012",
    "source_url": "https://sso.agc.gov.sg",
    "crawled_at": "2026-05-07",
    "pillar": "Pillar 6",
    "status": "indexed"
  },
  {
    "id": "doc_005",
    "country": "Brazil",
    "country_code": "BR",
    "language": "pt",
    "title": "Lei Geral de Proteção de Dados",
    "title_en": "General Data Protection Law (LGPD)",
    "source_url": "https://www.planalto.gov.br",
    "crawled_at": "2026-05-06",
    "pillar": "Pillar 7",
    "status": "indexed"
  }
]
```

## citations.json（引用・マッピング結果）
```json
[
  {
    "id": "cit_001",
    "doc_id": "doc_001",
    "article": "第24条",
    "article_en": "Article 24",
    "section": "第1項",
    "verbatim_ja": "個人情報取扱事業者は、外国にある第三者に個人データを提供する場合には、あらかじめ外国にある第三者への提供を認める旨の本人の同意を得なければならない。",
    "verbatim_en": "A personal information handling business operator shall, when providing personal data to a third party in a foreign country, obtain in advance the consent of the individual to the provision to a third party in a foreign country.",
    "pillar": "Pillar 6",
    "indicator": "6.2 Cross-border data transfer conditions",
    "confidence": 0.94,
    "discovery_method": "semantic",
    "reviewed": false
  },
  {
    "id": "cit_002",
    "doc_id": "doc_003",
    "article": "Section 48",
    "article_en": "Section 48",
    "section": "Subsection (1)",
    "verbatim_ja": null,
    "verbatim_en": "A data controller shall not transfer personal data to a foreign country or international organisation unless the country or international organisation ensures an adequate level of data protection.",
    "pillar": "Pillar 6",
    "indicator": "6.1 Data localisation requirements",
    "confidence": 0.91,
    "discovery_method": "keyword",
    "reviewed": true
  },
  {
    "id": "cit_003",
    "doc_id": "doc_002",
    "article": "มาตรา 37",
    "article_en": "Section 37",
    "section": null,
    "verbatim_ja": null,
    "verbatim_en": "The data controller shall notify the data subject of the purpose of collection, use and disclosure of personal data.",
    "pillar": "Pillar 7",
    "indicator": "7.1 Data subject rights",
    "confidence": 0.88,
    "discovery_method": "semantic",
    "reviewed": false
  }
]
```

---

# API Routes仕様（Next.js API Routes）

後でFastAPIに差し替えられるよう、インターフェースを統一する。

- `GET /api/documents` — 文書一覧（フィルター: country, pillar, language）
- `GET /api/documents/[id]` — 文書詳細
- `GET /api/citations` — 引用一覧（フィルター: pillar, doc_id）
- `GET /api/search?q=` — キーワード検索（モックはJSONフィルタリング）
- `GET /api/stats` — ダッシュボード用統計

---

# UIデザイン方針

- テーマ：ダークモード / ネイビー × ホワイト × アクセントカラー（国連ブルー #009EDB）
- フォント：英語はGeist、日本語は Noto Sans JP
- 雰囲気：国連らしい信頼感のある、クリーンでプロフェッショナルなデザイン
- 言語切り替えボタンをナビゲーションバーに配置（EN / JA）
- レスポンシブ対応（PC優先）

---

# 多言語対応

`/src/i18n/` 以下に英語・日本語の翻訳ファイルを作成。
UIテキストはすべて翻訳キーで管理。

---

# ディレクトリ構成

```
src/
  app/
    [locale]/
      page.tsx              # ダッシュボード
      search/page.tsx       # 法令検索
      audit/page.tsx        # 監査ビュー
      mapping/page.tsx      # Pillarマッピング
    api/
      documents/route.ts
      citations/route.ts
      search/route.ts
      stats/route.ts
  components/
    layout/
      Navbar.tsx
      Sidebar.tsx
    dashboard/
      StatsCard.tsx
      RecentDocuments.tsx
    search/
      SearchBar.tsx
      SearchFilters.tsx
      SearchResults.tsx
      CitationModal.tsx
    audit/
      AuditView.tsx
      SnippetPanel.tsx
      SourcePanel.tsx
      ReviewButtons.tsx
    mapping/
      MappingTable.tsx
      PillarBadge.tsx
      CountryRow.tsx
  data/
    mock/
      documents.json
      citations.json
  i18n/
    en.json
    ja.json
  lib/
    api.ts   # API呼び出しユーティリティ
```

---

# 注意事項

- モックデータはJSONから読み込む。外部APIは叩かない
- API Routesは後でFastAPIに差し替えられるようインターフェースを統一する
- コンポーネントは細かく分割して再利用しやすくする
- TypeScriptの型定義をしっかり書く（`/src/types/index.ts`に集約）
- shadcn/uiのコンポーネントを積極的に使う

まず最初に全体のディレクトリ構成とpackage.jsonを作成し、その後各画面を順番に実装してください。
```

---

## 仕様書サマリー（ClaudeCodeに渡す前に確認用）

### 作るもの
Next.js 14 + TypeScript + Tailwind CSSのWebアプリ（デモ用）

### 4画面
1. **ダッシュボード** — 統計・最近の文書一覧
2. **法令検索** — キーワード検索・フィルター・詳細モーダル
3. **監査ビュー** — 左右分割で抽出スニペット + 原文、Approve/Flagボタン
4. **Pillarマッピング** — 各国の対応状況テーブル・CSVエクスポート

### デモデータ
- 5カ国（日本・タイ・ケニア・シンガポール・ブラジル）
- 英語・日本語・タイ語・ポルトガル語の多言語文書
- 引用3件（Pillar 6 / Pillar 7）

### バックエンド
- Next.js API Routesで実装（後でFastAPIに差し替え可能な設計）

### UI
- ダークモード・国連ブルー（#009EDB）
- 英語/日本語切り替え対応

---

## ClaudeCodeへの補足指示（必要に応じて追加）

詰まった時や追加したい時のプロンプト例：

```
# 監査ビューの左右分割をもう少し見やすくしてほしい
# 信頼スコアをプログレスバーで表示してほしい
# モーダルにアニメーションを追加してほしい
# CSVエクスポート機能を実装してほしい（モックでOK）
```
