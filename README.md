# Akito Kawabata — Portfolio

九州工業大学 / Kyushu Institute of Technology  
kawabata.akito768@mail.kyutech.jp

---

## Projects

### 1. UN Trade AI — RDTII Regulatory Analysis Demo
**[`UN-AI-Hackathon-2026-main/`](./UN-AI-Hackathon-2026-main/UN-AI-Hackathon-2026-main)**

UN主催「Global Hackathon on AI for Digital Trade Regulatory Analysis」提出作品。  
各国の法令文書をAIで自動収集・解析し、UN基準（RDTII Pillar 6/7）へマッピングするRAGシステムのフロントエンド。

| 項目 | 内容 |
|------|------|
| 技術スタック | Next.js 14 (App Router) · TypeScript · Tailwind CSS · shadcn/ui · next-intl |
| 主な機能 | ダッシュボード / 法令検索 / AI引用監査ビュー / Pillarマッピングテーブル |
| 多言語対応 | 英語 / 日本語 (i18n) |
| API | Next.js API Routes（モックデータ、FastAPI差し替え対応設計） |

---

### 2. Yamaha SCARA Robot ROS2 Packages
**[`yamaha_scara-main/`](./yamaha_scara-main/yamaha_scara-main)**

九州工業大学 Hayashi Lab で運用中の Yamaha YK400XE SCАRAロボット向け ROS2 パッケージ群。  
2026年9月よりメンテナー担当。

| 項目 | 内容 |
|------|------|
| 技術スタック | ROS2 · Python · C++ |
| 主な機能 | PC–ロボット通信ブリンガップ / GUIコントロール（関節値・標準座標） / 真空システム制御 |
| 含まれる例 | 文字描画（HAYASHI LABロゴ） / 真空ピック＆プレイス |
| ベースリポジトリ | [yk400xe_ros2](https://github.com/Sappy27/yk400xe_ros2) |

---

### 3. 九州爬虫類フェス 2026 — 非公式ファンサイト
**[`reptiles/`](./reptiles)**

2026年5月30〜31日開催「九州爬虫類フェス 2026」の非公式ファンサイト。  
外部ライブラリゼロ、Vanilla HTML/CSS/JS のみで構築した単一ファイルWebサイト。

| 項目 | 内容 |
|------|------|
| 技術スタック | HTML5 · CSS3 · Vanilla JavaScript（外部依存: Google Fonts のみ） |
| データ規模 | 167店舗の出展者情報（AIによるスクレイピング・OCR・Web検索で収集） |
| 主な機能 | エリア/注目/地元/グッズ フィルター · キーワード検索 · モーダル詳細 · レスポンシブ対応 |
| 工夫 | CSS変数によるテーマ管理 / `clip-path` デザイン / `@keyframes` アニメーション |

---

### 4. Vlog Maker App
**[`Vlogapp/`](./Vlogapp)**

動画素材・テキスト台本を入力すると、自動でナレーション付きVlog動画を生成するStreamlitアプリ。

| 項目 | 内容 |
|------|------|
| 技術スタック | Python · Streamlit · MoviePy · VOICEVOX · Pillow · NumPy |
| 主な機能 | シーンごとの音声生成（VOICEVOX）/ テキストオーバーレイ・アニメーション / フリガナ対応 / キャッシュ最適化 |
| 特徴 | 並列処理（`concurrent.futures`）による高速レンダリング |

---

## Skills

> 各スキルの概要一覧

| スキル | 経験 | 一言サマリー |
|--------|------|-------------|
| Python | 2年 | Vlog 動画自動生成アプリ・データ処理ツールの開発経験あり |
| ROS2 | 1年 | 産業用 SCARA ロボットの制御パッケージ開発・メンテナー経験あり |
| HTML / CSS | 3年 | ゼロ依存の静的 Web サイト（167店舗対応）の設計・実装経験あり |
| TypeScript / Next.js | 3ヶ月 | UN ハッカソン向け RAG フロントエンドの開発経験あり |
| Streamlit | 5ヶ月 | Python 製 Web アプリの UI 構築・並列処理最適化の経験あり |
| Git | 2年 | 個人・研究室プロジェクトでのバージョン管理・リポジトリ保守経験あり |
| Claude API / AI | 2ヶ月 | RAG システム設計・プロンプトエンジニアリングの開発経験あり |
| Java | 半年未満 | スキルアップ学習およびハッカソン要件定義システムのテスト実装経験あり |

---

### 🐍 Python `経験 2年`
> **Python: 2年、ナレーション付き動画自動生成アプリの開発経験あり**

**レベル**: 中級 ／ **目的**: データ処理・自動化・アプリ開発  
大学の研究活動および個人開発で習得。Streamlit を用いた Web アプリ、MoviePy による動画自動生成、NumPy を使った並列レンダリングなど実用的なツール開発に活用。VOICEVOX API との連携でナレーション付き動画生成アプリ（Vlog Maker）を開発。

---

### 🤖 ROS2 `経験 1年`
> **ROS2: 1年、産業用 SCARA ロボット制御パッケージの開発経験あり**

**レベル**: 中級 ／ **目的**: 産業用ロボット制御・研究  
九州工業大学 Hayashi Lab にて Yamaha YK400XE SCARA ロボットの制御パッケージを開発・保守。ROS2 サービス／トピックを用いた PC–ロボット通信、GUI コントロール（関節値・標準座標）、真空システム制御を実装。2026年9月よりプロジェクトメンテナーとして担当。

---

### 🌐 HTML / CSS `経験 3年`
> **HTML/CSS: 3年、167店舗対応のゼロ依存静的 Web サイトの開発経験あり**

**レベル**: 中上級 ／ **目的**: フロントエンド Web 制作  
外部ライブラリに頼らない Vanilla JS での実装を得意とする。九州爬虫類フェス 2026 の非公式ファンサイトでは 167 店舗分のデータを単一 HTML ファイルにまとめ、CSS 変数・`clip-path`・`@keyframes` アニメーション・リアルタイム検索フィルターをゼロ依存で実装。

---

### ⚛️ TypeScript / Next.js / React `経験 3ヶ月`
> **TypeScript/Next.js: 3ヶ月、UN AI ハッカソン向け RAG フロントエンドの開発経験あり**

**レベル**: 初中級 ／ **目的**: モダン Web アプリ開発  
UN AI ハッカソン（2026）に向けて短期集中で習得。Next.js 14 App Router・Tailwind CSS・shadcn/ui を用いた RAG フロントエンドを構築。next-intl による英語/日本語 i18n、API Routes によるバックエンド設計まで一気通貫で実装。

---

### 🎬 Streamlit `経験 5ヶ月`
> **Streamlit: 5ヶ月、動画生成アプリの UI 構築・高速レンダリング最適化の開発経験あり**

**レベル**: 初中級 ／ **目的**: Python 製 Web アプリの迅速な UI 構築  
Vlog Maker アプリの UI フレームワークとして採用。動画素材アップロード・台本入力・シーン別プレビューを Streamlit で実現。`concurrent.futures` による並列処理と SHA-256 ハッシュキャッシュ機構を組み合わせ、レンダリング速度を大幅改善。

---

### 🔧 Git `経験 2年`
> **Git: 2年、研究室ロボットプロジェクトのリポジトリ保守・メンテナー経験あり**

**レベル**: 中級 ／ **目的**: バージョン管理・チーム開発  
個人・研究室プロジェクトで継続利用。ブランチ運用・コンフリクト解消・リモートリポジトリ管理を習得。Yamaha ロボットプロジェクトのメンテナー業務でリポジトリ管理を担当。

---

### 🤖 Claude API / AI `経験 2ヶ月`
> **Claude API/AI: 2ヶ月、RAG システム設計・プロンプトエンジニアリングの開発経験あり**

**レベル**: 初級 ／ **目的**: AI 機能のアプリ組み込み・RAG システム設計  
UN AI ハッカソンでプロンプトエンジニアリングおよび RAG アーキテクチャを学習。各国法令文書の自動収集・解析・UN 基準マッピングのシステム設計に携わる。Claude Code を活用した AI 駆動開発フローも実践中。

---

### ☕ Java `経験 半年未満`
> **Java: 半年未満、スキルアップ学習およびハッカソン要件定義システムのテスト実装経験あり**

**レベル**: 初級 ／ **目的**: 基礎的なオブジェクト指向プログラミングの習得・システム検証  
自己研鑽として Java の基礎文法・オブジェクト指向設計を学習。ハッカソンで要件定義したシステムの動作検証・テスト実装に活用。今後もバックエンド開発やアルゴリズム学習の文脈でスキルアップを継続予定。

---

## Contact

- Email: kawabata.akito768@mail.kyutech.jp
- GitHub: (このREADMEをご参照ください)
