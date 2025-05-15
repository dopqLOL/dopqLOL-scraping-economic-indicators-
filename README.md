# dopqLOL-scraping-economic-indicators-

GOLDの経済指標影響分析アプリ (Android/Jetpack Compose)

## 概要

経済指標や要人発言がGOLD価格に与える影響を分析し、ボラティリティを予測するためのAndroidアプリケーションです。

## 主な機能 (予定)

- kissfx.comからの経済指標データの自動取得 (指定時間帯)
- 過去データとの比較分析
- 市場ボラティリティ状況に応じた予測分類
- Jetpack ComposeによるモダンなUI

## セットアップ

(ここにビルドや実行の手順を記述)

## 技術スタック

- Kotlin
- Android
- Jetpack Compose
- Coroutines
- ViewModel
- Room/DataStore
- Ktor/Retrofit (検討中)

# KissFX 経済指標データ抽出スクリプト

## 概要

このPythonスクリプトは、外国為替情報サイト「羊飼いのFXブログ」(kissfx.com) の経済指標カレンダーから、指定された期間のデータを取得し、CSVファイルとして整形・出力します。

## 主な機能

-   指定期間における経済指標の予定を kissfx.com から取得します。
-   取得データから、発表日時 (日本時間 `YYYY.MM.DD HH:MM` 形式)、国名、指標名、重要度などの情報を抽出します。
-   抽出した情報を整形し、重複を除外した上でCSVファイルとして保存します。
    -   出力先: プロジェクトルートの `kissfx_data` ディレクトリ
    -   ファイル名例: `kissfx_data/economic_indicators_20200101-20241231.csv`
-   ウェブサイトへの過度な負荷を避けるため、日付ごとの処理の間にランダムな待機時間を挿入します。
-   **(オプション)** HTMLコンテンツの保存機能:
    -   デバッグや詳細分析を目的として、取得した各日付ページのHTMLを生のまま保存できます。
    -   この機能はデフォルトで無効化されています。有効にするには、スクリプト内の `get_economic_indicators_for_date` 関数にある `save_html_to_file` 関数の呼び出し部分のコメントを解除してください。
    -   HTMLファイルも `kissfx_data` ディレクトリに保存されます (例: `kissfx_data/kissfx_raw_YYYYMMDD.html`)。

## 実行環境および必要なライブラリ

-   Python 3.7 以降
-   requests
-   beautifulsoup4
-   pandas

上記ライブラリは、以下のコマンドでインストールできます。
```bash
pip install requests beautifulsoup4 pandas
```

## 使用方法

1.  **スクリプトの配置:**
    *   `Workspace_kissfx_indicators.py` が `Python/dopqLOL-scraping-economic-indicators-/` ディレクトリに配置されていることを確認します。(リポジトリをクローンした場合は既に配置済みです)
2.  **実行:**
    *   `GoldEventAnalyzer` プロジェクトのルートディレクトリから、以下のコマンドでスクリプトを実行します。
        ```bash
        python Python/dopqLOL-scraping-economic-indicators-/Workspace_kissfx_indicators.py
        ```
    *   実行後、データの取得開始日と終了日を `YYYYMMDD` 形式で入力するよう求められます。
3.  **出力結果の確認:**
    *   処理が完了すると、プロジェクトルートに `kissfx_data` ディレクトリが作成（または使用）され、その中に経済指標データがCSVファイルとして保存されます。
    *   HTML保存オプションを有効にした場合は、HTMLファイルも同ディレクトリに出力されます。
    *   コンソールには、処理の進捗状況と最終的に取得されたイベント件数が表示されます。

## 注意事項

-   本スクリプトは `kissfx.com` のウェブサイト構造に依存して動作します。サイト構造が大幅に変更された場合、スクリプトが正常に機能しなくなる可能性がありますので、その際は適宜修正が必要です。
-   長期間のデータを一度に取得しようとすると、対象ウェブサイトへのアクセス回数が非常に多くなります。スクリプトにはサーバー負荷を軽減するための待機処理が含まれていますが、節度を持った利用を心がけてください。
-   祝日など、経済指標の発表が予定されていない日付のページは存在しないことがあります。その場合、該当する日付のデータはスキップされます。 