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

- **Languages**: Python · TypeScript · JavaScript · C++ · Bash
- **Frontend**: Next.js · React · Tailwind CSS · shadcn/ui · Vanilla JS
- **Robotics**: ROS2 · URDF · モーション制御
- **AI/ML**: RAGシステム設計 · プロンプトエンジニアリング · Claude API
- **Tools**: Git · Streamlit · MoviePy · VOICEVOX

---

## Contact

- Email: kawabata.akito768@mail.kyutech.jp
- GitHub: (このREADMEをご参照ください)
