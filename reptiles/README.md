# 九州爬虫類フェス 2026 — 非公式ファンサイト

![HTML](https://img.shields.io/badge/HTML5-E34F26?style=flat&logo=html5&logoColor=white)
![CSS](https://img.shields.io/badge/CSS3-1572B6?style=flat&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black)
![License](https://img.shields.io/badge/license-MIT-green)

> 2026年5月30日・31日に開催された「九州爬虫類フェス 2026」の非公式ファンサイトです。  
> 公式サイト → [q-reptile.com/fukuoka](https://q-reptile.com/fukuoka/)

---

## 📸 サイト概要

来場者・爬虫類ファン向けに、イベント情報・出展者一覧・アクセス情報をまとめた静的Webサイトです。
外部ライブラリ・フレームワークを一切使わず、**HTML / CSS / JavaScript のみ**で構築しています。

### 主な機能

| 機能 | 内容 |
|------|------|
| イベント情報 | 8つの特別企画・グルメ・チケット・アクセスを掲載 |
| 出展者一覧 | 全167店舗の名前・説明・SNSリンクを収録 |
| フィルター検索 | エリア別・注目ショップ・地元九州・グッズ系でフィルタリング |
| キーワード検索 | 店名・タグ・説明文から横断検索 |
| モーダル詳細 | クリックで各店舗の詳細情報・外部リンクを表示 |
| レスポンシブ対応 | スマートフォン・タブレット・PCで閲覧可能 |
| 駐車場警告 | 来場者向けの重要情報をアニメーションバナーで強調表示 |

---

## 🛠️ 技術スタック

```
HTML5 / CSS3 / Vanilla JavaScript
外部依存：Google Fonts のみ（Zen Antique Soft / Noto Sans JP / Oswald）
ビルドツール：なし（単一HTMLファイル）
```

### 工夫した実装

- **CSS変数（カスタムプロパティ）** でカラーテーマを一元管理。テーマ変更が容易な設計。
- **モーダルウィンドウ** をJavaScriptのみで実装（ライブラリ不使用）。ESCキー・背景クリックで閉じる。
- **リアルタイム検索フィルター** を配列の `.filter()` メソッドで実装。167件でも即座に絞り込み。
- **スクロール連動ナビ** で `window.scrollY` を監視し、ヘッダーのスタイルを動的に切り替え。
- **clip-path** を使ったCSSのみのデザイン（ボタンの斜めカット）。
- **アニメーション** は `@keyframes` のみ使用。ヒーローのフェードイン・バナーのシマーエフェクト・葉のスウェイなど。

---

## 📂 ファイル構成

```
.
├── index.html       # サイト本体（すべてのHTML・CSS・JSを含む単一ファイル）
└── README.md        # このファイル
```

単一ファイルで完結しているため、ダウンロードしてブラウザで開くだけで動作します。

---

## 🔍 情報収集の方法

このサイトの出展者情報（167店舗）は、以下のステップで収集・整理しました。

### Step 1 — 公式サイトのスクレイピング（手動フェッチ）

まず公式サイトの出展者一覧ページ（`q-reptile.com/fukuoka/shop/`）を取得し、
各ショップの **自己紹介文・公式リンク** を一括で収集しました。

```
取得元: https://q-reptile.com/fukuoka/shop/
取得方法: Claude（AI）のweb_fetchツールでHTMLを取得 → Markdownに変換 → 構造化
```

公式サイトには各ショップが自ら書いた紹介文と、
Instagram・Twitter（X）・公式サイトのリンクが掲載されており、
これをそのまま `exhibitors` 配列のデータとして整理しました。

### Step 2 — フロアマップのOCR的読み取り

イベント当日に入手したチラシ（フロアマップ）の写真を Claude に読み込ませ、
エリアブース・テーブルブースのブース番号と店舗名の対応表を抽出しました。

```
入力: チラシ写真（JPEG 2枚）
出力: ブース番号ごとのショップ名リスト
```

画像内に小さく印刷されたテキストも含めて、
AIの画像認識を使い全店舗名を読み取りました。

### Step 3 — 追加SNS情報の検索

公式サイトにリンクが掲載されていなかったショップについては、
Web検索で個別に調査しました。

```
検索クエリの例:
  "MOLTING BASE 爬虫類 Instagram"
  "マニアックレプタイルズ Twitter site:x.com"
  "REPTILESTOKYO 公式サイト"
```

これにより、Instagramアカウント・Twitterアカウント・公式ECサイトなどを
各ショップに紐づけることができました。

### Step 4 — データの構造化

収集した情報をJavaScriptの配列オブジェクトとして整形しました。

```javascript
// 1店舗あたりのデータ構造
{
  num: "1",                        // ブース番号
  area: "a",                       // "a"=エリアブース / "b"=テーブルブース
  local: true,                     // 九州地元かどうか
  featured: true,                  // 注目ショップフラグ
  name: "MOLTING BASE",            // 店舗名
  tags: ["爬虫類全般", "福岡地元"], // 検索・フィルター用タグ
  desc: "福岡県で活動。...",        // 公式サイト掲載の紹介文
  instagram: "https://...",        // Instagram URL
  twitter: "https://...",          // X(Twitter) URL
  web: "https://..."               // 公式サイト URL
}
```

### 収集結果サマリー

| 項目 | 件数 |
|------|------|
| 総出展店舗数 | 167店舗 |
| エリアブース | 95店舗 |
| テーブルブース | 72店舗 |
| SNS・リンクあり | 約120店舗 |
| 九州地元ショップ | 約30店舗 |
| 注目ショップ指定 | 約70店舗 |

### 注意事項・免責

- 情報の一部は掲載時点（2026年5月）のものです。最新情報は各ショップのSNSや公式サイトをご確認ください。
- 紹介文は公式サイト（`q-reptile.com`）の各ショップ自己紹介を引用・要約しています。
- SNSリンクは検索によって収集したものです。誤りがある場合はIssueにてご報告ください。

---

## 🚀 使い方

### ブラウザで直接開く

```bash
git clone https://github.com/YOUR_USERNAME/kyushu-reptile-fes-2026.git
cd kyushu-reptile-fes-2026
open index.html   # macOS
# または index.html をブラウザにドラッグ&ドロップ
```

### GitHub Pages で公開する

1. このリポジトリをフォーク or クローン
2. GitHub の Settings → Pages → Source を `main / (root)` に設定
3. 数分後に `https://YOUR_USERNAME.github.io/kyushu-reptile-fes-2026/` で公開

---

## ✏️ カスタマイズ・データ更新

出展者情報の追加・修正は `index.html` 内の `exhibitors` 配列を編集するだけです。

```javascript
// index.html の <script> タグ内
const exhibitors = [
  {
    num: "1",
    name: "MOLTING BASE",
    desc: "説明文をここに...",
    instagram: "https://www.instagram.com/xxxxx/",
    // ...
  },
  // 以下続く
];
```

HTMLの知識がなくても、この配列部分だけ編集すれば情報を更新できます。

---

## 📄 ライセンス

MIT License

イベント情報・出展者情報の著作権は各権利者に帰属します。
公式サイトおよびイベント主催者（九州爬虫類フェス実行委員会）の情報を元に作成しています。

---

## 🙏 クレジット

- イベント公式サイト: [q-reptile.com](https://q-reptile.com/fukuoka/)
- 主催: 九州爬虫類フェス実行委員会（合同会社浦田企画 / TVQ九州放送 / 爬虫類ショップ アンテナ）
- 協賛: ジェックス株式会社（EXO-TERRA）
- フォント: [Google Fonts](https://fonts.google.com/)（Zen Antique Soft, Noto Sans JP, Oswald）

---

<p align="center">
  <a href="https://q-reptile.com/fukuoka/">公式サイト</a> ·
  <a href="https://twitter.com/9rep_official">公式X（Twitter）</a>
</p>
