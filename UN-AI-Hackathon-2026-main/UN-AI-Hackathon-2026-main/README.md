# UN Trade AI — RDTII Regulatory Analysis Demo

UN主催ハッカソン **"Global Hackathon on AI for Digital Trade Regulatory Analysis"** の審査提出用デモアプリです。
各国の法令文書をAIで自動収集・解析し、UN基準（RDTII Pillar 6/7）にマッピングするRAGシステムのフロントエンドです。

## 画面構成

| パス | 概要 |
| --- | --- |
| `/` (Dashboard) | 収集済み文書数・国数・条文数などの統計、最近追加された文書一覧 |
| `/search` | キーワード・国・言語・Pillarでフィルタリングできる法令検索、詳細モーダル |
| `/audit` | AIが抽出した引用スニペットと元文書の左右分割ビュー、Approve/Flagボタン |
| `/mapping` | 各国のPillar 6/7 対応状況テーブル、CSVエクスポート |

言語切り替え（EN/JA）はナビバーのボタンから行えます。`/en/...` と `/ja/...` でURLが切り替わります。

## 技術スタック

- **Next.js 14** (App Router)
- **TypeScript**
- **Tailwind CSS** + **shadcn/ui**
- **next-intl** — 英語/日本語 i18n
- **lucide-react** — アイコン
- バックエンド: Next.js API Routes（モックデータ）

## セットアップ

### 必要な環境

- Node.js 18.17 以上
- npm 9 以上

### インストール & 起動

```bash
# 依存パッケージのインストール
npm install

# 開発サーバー起動
npm run dev
```

ブラウザで [http://localhost:3000](http://localhost:3000) を開くと `/en` にリダイレクトされます。

### ビルド確認

```bash
npm run build
npm run start
```

## ディレクトリ構成

```text
.
├── app/
│   ├── [locale]/           # 言語ごとのページ (en / ja)
│   │   ├── layout.tsx      # Sidebar + Navbar を含むレイアウト
│   │   ├── page.tsx        # ダッシュボード
│   │   ├── search/         # 法令検索
│   │   ├── audit/          # 監査ビュー
│   │   └── mapping/        # Pillarマッピング
│   └── api/                # API Routes
│       ├── documents/      # GET /api/documents, /api/documents/[id]
│       ├── citations/      # GET /api/citations
│       ├── search/         # GET /api/search?q=
│       └── stats/          # GET /api/stats
├── components/
│   ├── layout/             # Sidebar, Navbar
│   ├── dashboard/          # StatsCard, RecentDocuments
│   ├── search/             # SearchBar, SearchFilters, SearchResults, CitationModal
│   ├── audit/              # SnippetPanel, SourcePanel, ReviewButtons
│   └── mapping/            # PillarBadge, CountryRow
├── src/
│   ├── data/mock/          # documents.json, citations.json（モックデータ）
│   ├── i18n/               # en.json, ja.json（翻訳ファイル）、routing.ts
│   ├── lib/api.ts          # fetch ユーティリティ
│   └── types/index.ts      # 共通型定義
└── middleware.ts            # next-intl ロケールルーティング
```

## API 仕様

すべて `GET` のみ。モックデータを JSON フィルタリングして返します。
FastAPI 等への差し替えは `src/lib/api.ts` の `BASE_URL` と各 Route Handler を置き換えるだけで対応できます。

| エンドポイント | クエリパラメータ | 概要 |
| --- | --- | --- |
| `/api/documents` | `country`, `pillar`, `language` | 文書一覧 |
| `/api/documents/[id]` | — | 文書詳細 |
| `/api/citations` | `pillar`, `doc_id` | 引用一覧 |
| `/api/search` | `q` | キーワード全文検索 |
| `/api/stats` | — | ダッシュボード用統計 |

## モックデータ

`src/data/mock/` 以下の JSON を直接編集することでデータを変更できます。

- **documents.json** — 5カ国（日本・タイ・ケニア・シンガポール・ブラジル）の法令文書
- **citations.json** — Pillar 6/7 にマッピングされた引用条文 3件

## 翻訳の追加・変更

`src/i18n/en.json` / `src/i18n/ja.json` を編集してください。
新しいロケールを追加する場合は `src/i18n/routing.ts` の `locales` 配列にも追加します。

## 環境変数

| 変数 | デフォルト | 用途 |
| --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:3000` | API のベース URL（FastAPI 差し替え時に設定） |
