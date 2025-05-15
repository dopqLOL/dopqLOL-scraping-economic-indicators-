# GoldEventAnalyzer

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

# KissFX 経済指標スクレイパー

## 概要

このPythonスクリプトは、外国為替情報サイト「羊飼いのFXブログ」(kissfx.com) から経済指標カレンダーの情報をスクレイピングし、指定された期間のデータを抽出してCSVファイルとして出力します。

## 主な機能

-   指定された期間の経済指標データをウェブサイトから取得します。
-   取得したデータから、日付、国名、指標名、重要度などの主要情報を抽出・整形します。
-   日付時刻は日本時間基準で `YYYY.MM.DD HH:MM` 形式で出力します。
-   不要なデータ（例: 単純な数値のみの行など）をフィルタリングします。
-   処理結果をCSVファイル（例: `kissfx_indicators_20200101-20241231.csv`）として保存します。
-   ウェブサイトへの連続アクセスを避けるため、各日付の処理間にランダムな待機時間を設けています。

## 必要なライブラリ / 実行環境

-   Python 3.7 以降
-   `requests`
-   `beautifulsoup4`
-   `pandas`

これらのライブラリは、`pip install requests beautifulsoup4 pandas` コマンドでインストールできます。

## 使い方

1.  **スクリプトの準備:**
    *   `Workspace_kissfx_indicators.py` ファイルを任意のディレクトリに配置します。
2.  **日付範囲の設定 (任意):**
    *   スクリプト内の `if __name__ == "__main__":` ブロックにある以下の部分を編集することで、データ取得期間を変更できます。
        ```python
        # --- 日付範囲の設定 ---
        date_to = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9))) # JSTの現在日時
        # date_from = date_to - timedelta(days=5*365) # 5年前 (デフォルト)
        # 特定の期間を指定する場合 (例)
        # date_from = datetime(2020, 1, 1, tzinfo=timezone(timedelta(hours=9))) 
        # date_to = datetime(2020, 12, 31, tzinfo=timezone(timedelta(hours=9)))
        ```
    *   デフォルトでは、実行時から過去5年間のデータを取得しようとします。テスト実行時は短い期間（例: `timedelta(days=7)`）に設定することをおすすめします。
3.  **実行:**
    *   コマンドラインからスクリプトを実行します。
        ```bash
        python Workspace_kissfx_indicators.py
        ```
4.  **出力確認:**
    *   スクリプトと同じディレクトリに、指定期間のデータが含まれるCSVファイル (例: `kissfx_indicators_YYYYMMDD-YYYYMMDD.csv`) が生成されます。
    *   コンソールには処理の進捗状況と最終的な取得件数が表示されます。

## 注意点

-   このスクリプトは `kissfx.com` のHTML構造に依存しています。ウェブサイトの構造が大幅に変更された場合、スクリプトの修正が必要になることがあります。
-   長期間のデータを取得する場合、ウェブサイトへのアクセス回数が多くなります。サーバーに過度な負荷をかけないよう、`time.sleep()` による待機時間が設けられていますが、常識の範囲内でご利用ください。
-   祝日などで経済指標の発表がない日付のページは存在しない場合があり、その場合はスキップされます。 