import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta, timezone, time as dt_time
import time
import re
import random
import os # 追加

# --- 出力ディレクトリ定義 ---
OUTPUT_DIR = "kissfx_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- HTMLコンテンツをファイルに保存するヘルパー関数 (デバッグ用) ---
def save_html_to_file(html_content, filename="page_content.html"):
    try:
        # 変更: 出力ディレクトリをファイルパスに含める
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        # print(f"  HTMLコンテンツを {filepath} に保存しました。") 
    except Exception as e:
        print(f"  HTMLコンテンツのファイル保存中にエラー: {e}")

# --- 経済指標・イベント情報抽出関数 ---
def get_economic_indicators_for_date(target_date_str):
    url = f"https://kissfx.com/article/fxdays{target_date_str}.html"
    events_for_date = []
    extracted_count_for_day = 0 # 初期化
    
    try:
        print(f"Fetching data for: {target_date_str} from {url}")
        response = requests.get(url, timeout=15)
        # HTML保存をコメントアウト
        # save_html_to_file(response.text, f"kissfx_raw_{target_date_str}.html")

        if response.status_code == 404:
            print(f"  ページが見つかりませんでした (404 Not Found): {url}")
            return events_for_date
            
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        
        article_content_body = soup.find('div', class_='c-article-content__body')
        if not article_content_body:
            print(f"  主要コンテナ <div class='c-article-content__body'> が見つかりませんでした。")
            return events_for_date
        else:
            print(f"  コンテナ <div class='c-article-content__body'> を使用します。")

        date_obj_for_event = datetime.strptime(target_date_str, "%Y%m%d")
        extracted_events_temp = [] # 抽出したイベントを一時的に格納 (重複チェック用)
        
        # --- 1. 「本日の必見イベント＆経済指標はコレだ！！」セクションの解析 ---
        # このセクションは <table bgcolor="#ffe6f2"> の中の <td> に <br> 区切りと推測
        print("  「必見イベント」セクションを解析します...")
        summary_table = article_content_body.find('table', attrs={'bgcolor': '#ffe6f2'})
        if summary_table:
            td_elements = summary_table.find_all('td')
            for td_idx, td in enumerate(td_elements):
                # .stripped_strings を使って <br> 区切りを意識しつつテキストを取得
                raw_text_parts = list(td.stripped_strings) # これで各行が取れるはず
                
                for line_num, text_line in enumerate(raw_text_parts):
                    text = text_line.strip()
                    if not text or not text.startswith("・"): continue # 「・」で始まらないものはスキップ
                    
                    text_to_parse = text.lstrip('・').strip()
                    # print(f"    必見イベント候補: {text_to_parse}") # デバッグ用

                    time_str, country, indicator_name, importance_str = "", "N/A", "", "UNKNOWN"
                    
                    time_match = re.match(r'(\\d{1,2}時\\d{1,2}分)：\\s*', text_to_parse)
                    if time_match:
                        time_str = time_match.group(1).replace("時",":").replace("分","")
                        text_to_parse = text_to_parse[len(time_match.group(0)):].strip()

                    # 国プレフィックスと指標名/発言者
                    country_patterns = {
                        "米国": r"米\)", "ユーロ圏": r"欧\)", "英国": r"英\)", "日本": r"日\)", 
                        "中国": r"中\)", "豪州": r"豪\)", "NZ": r"NZ\)|ﾆｭｰｼﾞｰﾗﾝﾄﾞ\)", "カナダ": r"加\)", 
                        "スイス": r"スイス\)", "独": r"独\)"} # ) まで含めて特徴とする
                    
                    found_country = False
                    for c_name, c_pattern in country_patterns.items():
                        country_match = re.match(c_pattern, text_to_parse, re.IGNORECASE)
                        if country_match:
                            country = c_name
                            indicator_name = text_to_parse[len(country_match.group(0)):].strip()
                            found_country = True
                            break
                    if not found_country: # 国プレフィックスがない場合は、全体を指標名とみなす
                        indicator_name = text_to_parse
                    
                    # 重要度 (このセクションでは太字や色で示唆されていることが多い)
                    # 簡単なキーワードで判定 (実際のHTMLのspan classなどを参照して改善可能)
                    if "総裁の発言" in indicator_name or "決定会合" in indicator_name or "消費者物価指数" in indicator_name or "失業率" in indicator_name:
                        importance_str = "HIGH"
                    elif "景況感調査" in indicator_name or "小売売上高" in indicator_name:
                        importance_str = "MEDIUM"
                    elif "主な意見" in indicator_name or "申請件数" in indicator_name:
                        importance_str = "LOW"

                    # 指標名から不要な部分を除去 (例: (4月30日・5月1日開催分), ＆以降)
                    indicator_name = re.sub(r'\\(.*?開催分\\)', '', indicator_name).strip() # バックスラッシュ修正
                    indicator_name = re.sub(r'＆.*', '', indicator_name).strip() # 「失業率＆失業保険申請件数」の後半を除去する簡易処理
                    indicator_name = re.sub(r'→過去発表時.*', '', indicator_name).strip() # 詳細リンクを除去
                    indicator_name = re.sub(r'\\s*\\[.*?\\]\\s*', '', indicator_name).strip() # [ドル円]のような通貨ペア情報を除去 (バックスラッシュ修正)
                    indicator_name = indicator_name.replace('【コア】', ' コア').replace('[コア]', ' コア').strip()
                    indicator_name = re.sub(r'^・', '', indicator_name).strip() # 先頭の・を除去
                    indicator_name = re.sub(r'^↑', '', indicator_name).strip() # 先頭の↑を除去
                    indicator_name = re.sub(r'\\s{2,}', ' ', indicator_name).strip() # 連続するスペースを1つに (バックスラッシュ修正)

                    if not indicator_name or len(indicator_name) < 2: continue # 短すぎるものはスキップ
                    if not time_str : continue # 時刻がないものは一旦スキップ (要調整)

                    event_datetime_jst = pd.Timestamp(datetime.combine(date_obj_for_event, dt_time(0,0,0)), tz='Asia/Tokyo')
                    try:
                        event_time_obj = datetime.strptime(time_str, "%H:%M").time()
                        event_datetime_jst = pd.Timestamp(datetime.combine(date_obj_for_event, event_time_obj), tz='Asia/Tokyo')
                    except ValueError: continue # 時刻パース失敗はスキップ

                    if country != "N/A": # 国が特定できたものだけ
                        extracted_events_temp.append({
                            'datetime_jst': event_datetime_jst, 'country': country, 'indicator': indicator_name,
                            'importance': importance_str, 'forecast': "", 'result': "", 'previous': "",
                            'source_tag_type': 'summary_list'
                        })
                        # print(f"      必見リスト抽出: {event_datetime_jst.strftime('%H:%M')} {country} {indicator_name} ({importance_str})")
        else:
            print("  「必見イベント」セクションのテーブルが見つかりませんでした。")

        # --- 2. 指標カレンダーテーブル (<div class="c-shihyo-calendar"> 内の <table class="table">) の解析 ---
        shihyo_calendar_div = article_content_body.find('div', class_='c-shihyo-calendar')
        if shihyo_calendar_div:
            indicator_table = shihyo_calendar_div.find('table', class_='table')
            if indicator_table:
                print(f"  指標カレンダーテーブルを解析します...")
                rows = indicator_table.select("tbody > tr") if indicator_table.select_one("tbody") else indicator_table.find_all("tr")
                if rows:
                    header_skipped = False; current_row_time_str = ""; current_row_country_text = "" # 国名引き継ぎ用変数を追加
                    for row_idx, row in enumerate(rows):
                        if not header_skipped and row.find('th'): header_skipped = True; continue
                        cols = row.find_all('td')
                        # print(f"DEBUG ROW {row_idx}: len(cols)={len(cols)}, texts={[col.text.strip() for col in cols]}") # DEBUG column count and texts
                        if not cols or cols[0].has_attr('colspan'): continue
                        time_str, country_text, indicator_name_raw, importance_str, forecast, previous_val, result_text = "", "", "", "UNKNOWN", "", "", ""
                        country_col_idx, indicator_cell_idx, importance_cell_idx, forecast_cell_idx, previous_cell_idx, result_cell_idx = -1,-1,-1,-1,-1,-1

                        if len(cols) >= 6 :
                            time_str = cols[0].text.strip()
                            country_col_idx, indicator_cell_idx, importance_cell_idx, forecast_cell_idx, previous_cell_idx = 1, 2, 3, 4, 5
                            result_cell_idx = 6;
                            if time_str: current_row_time_str = time_str 
                        elif len(cols) == 5:
                            time_candidate = cols[0].text.strip()
                            if re.match(r'^\d{1,2}:\d{2}$', time_candidate):
                                time_str = time_candidate
                                country_col_idx, indicator_cell_idx, importance_cell_idx, forecast_cell_idx = 1, 2, 3, 4
                                if time_str: current_row_time_str = time_str
                            elif current_row_time_str: 
                                time_str = current_row_time_str
                                country_col_idx, indicator_cell_idx, importance_cell_idx, forecast_cell_idx, previous_cell_idx = 0, 1, 2, 3, 4 
                            else:
                                continue 
                        else: 
                            if current_row_time_str and len(cols) >= 2: 
                                time_str = current_row_time_str
                                country_text = current_row_country_text # 前行の国名を引き継ぐ
                                indicator_cell_idx = 1 
                                if len(cols) > 2: importance_cell_idx = 2
                                if len(cols) > 3: forecast_cell_idx = 3
                            else:
                                continue
                        try:
                            if country_col_idx != -1 and country_col_idx < len(cols):
                                country_img = cols[country_col_idx].find('img'); 
                                temp_country = country_img['alt'].strip() if country_img and country_img.has_attr('alt') else cols[country_col_idx].text.strip()
                                if temp_country: country_text = temp_country; current_row_country_text = temp_country # 国名があれば更新・保持
                                elif current_row_country_text : country_text = current_row_country_text # 国名が空なら前行を引き継ぐ
                            elif country_text == "": # country_col_idx が -1 だったり、取得できなかった場合で、かつcountry_textが未設定の場合
                                 country_text = current_row_country_text # 前行の国名を引き継ぐ
                            
                            if indicator_cell_idx == -1 or indicator_cell_idx >= len(cols): continue # 指標セルが無効ならスキップ
                            indicator_cell = cols[indicator_cell_idx]; indicator_text_parts = []

                            for content_part in indicator_cell.contents:
                                if hasattr(content_part, 'name') and content_part.name == 'a' and '過去発表時' in content_part.text : break 
                                if hasattr(content_part, 'name') and content_part.name == 'br': indicator_text_parts.append(" ") 
                                elif hasattr(content_part, 'text'): indicator_text_parts.append(content_part.text.strip())
                                elif isinstance(content_part, str): indicator_text_parts.append(content_part.strip())
                            indicator_name_raw = " ".join(indicator_text_parts).strip()
                            
                            indicator_name_raw = re.sub(r'→過去発表時.*', '', indicator_name_raw).strip()
                            potential_indicators_raw = re.split(r'(↑)', indicator_name_raw)
                            current_indicator_parts = []
                            structured_indicators = []
                            for part in potential_indicators_raw:
                                if part == '↑':
                                    if current_indicator_parts:
                                        structured_indicators.append("".join(current_indicator_parts).strip())
                                        current_indicator_parts = ['↑'] 
                                    else: 
                                        current_indicator_parts.append('↑')
                                else:
                                    current_indicator_parts.append(part)
                            if current_indicator_parts:
                                structured_indicators.append("".join(current_indicator_parts).strip())
                            if not structured_indicators and indicator_name_raw: 
                                structured_indicators = [indicator_name_raw]
                            
                            for single_indicator_raw_text in structured_indicators:
                                if not single_indicator_raw_text.strip(): continue
                                indicator_name = single_indicator_raw_text
                                country_prefix_match = None
                                try:
                                    country_prefix_match = re.match(r'^[日月火水木金土祝米欧英独仏伊中豪NZ加瑞南アト]{1,3}\)\s*', indicator_name)
                                except Exception as e_re_match_country:
                                    print(f"        ERROR in re.match for country_prefix: {e_re_match_country}, on: '{indicator_name}'")
                                    continue 
                                if country_prefix_match: 
                                    indicator_name = indicator_name[len(country_prefix_match.group(0)):].strip()
                                indicator_name = indicator_name.replace("・", " ").strip()
                                try:
                                    indicator_name = re.sub(r'\([^)]*\)', '', indicator_name).strip()
                                except Exception as e_re_sub_parens:
                                    print(f"        ERROR in re.sub for (...) removal: {e_re_sub_parens}, on: '{indicator_name}'")
                                try:
                                    indicator_name = re.sub(r'\s*\[[^\]]*\]\s*', '', indicator_name).strip()
                                except Exception as e_re_sub_brackets:
                                    print(f"        ERROR in re.sub for [...] removal: {e_re_sub_brackets}, on: '{indicator_name}'")
                                indicator_name = indicator_name.replace('【コア】', ' コア').replace('[コア]', ' コア').strip()
                                indicator_name = re.sub(r'^↑', '', indicator_name).strip()
                                indicator_name = re.sub(r'^・', '', indicator_name).strip()
                                try:
                                    indicator_name = re.sub(r'\s{2,}', ' ', indicator_name).strip()
                                except Exception as e_re_sub_spaces:
                                    print(f"        ERROR in re.sub for extra spaces: {e_re_sub_spaces}, on: '{indicator_name}'")
                                    continue
                                if not indicator_name or len(indicator_name) < 2:
                                    continue 
                                importance_text = ""
                                if importance_cell_idx != -1 and importance_cell_idx < len(cols):
                                    importance_cell = cols[importance_cell_idx]
                                    icon_tag = importance_cell.find(['div', 'span', 'i'], class_=lambda x: x and x.startswith('icon-'))
                                    if icon_tag and icon_tag.has_attr('class'):
                                        class_names = " ".join(icon_tag['class'])
                                        if "icon-ss" in class_names: importance_str = "VERY_HIGH_US"
                                        elif "icon-s" in class_names: importance_str = "HIGH_US"
                                        elif "icon-aa" in class_names: importance_str = "MEDIUM_HIGH_US"
                                        elif "icon-a" in class_names: importance_str = "MEDIUM_US"
                                        elif "icon-bb" in class_names: importance_str = "MEDIUM_LOW_US"
                                        elif "icon-b" in class_names: importance_str = "LOW_US"
                                        elif "icon-c" in class_names: importance_str = "VERY_LOW_US"
                                        elif "icon-maru2" in class_names: importance_str = "HIGH"
                                        elif "icon-maru" in class_names: importance_str = "MEDIUM"
                                        elif "icon-san" in class_names: importance_str = "LOW"
                                        elif "icon-batu" in class_names: importance_str = "VERY_LOW"
                                    else: # If no icon class, try to get text content as importance
                                        importance_text = importance_cell.text.strip()
                                        if importance_text == "★★★★★": importance_str = "VERY_HIGH"
                                        elif importance_text == "★★★★": importance_str = "HIGH"
                                        elif importance_text == "★★★": importance_str = "MEDIUM"
                                        elif importance_text == "★★": importance_str = "LOW"
                                        elif importance_text == "★": importance_str = "VERY_LOW"
                                current_forecast = cols[forecast_cell_idx].text.strip().replace("－", "").replace("-", "") if forecast_cell_idx != -1 and forecast_cell_idx < len(cols) else ""
                                current_previous = cols[previous_cell_idx].text.strip().replace("－", "").replace("-", "") if previous_cell_idx != -1 and previous_cell_idx < len(cols) else ""
                                current_result = cols[result_cell_idx].text.strip().replace("－", "").replace("-", "") if result_cell_idx != -1 and result_cell_idx < len(cols) else ""
                                event_datetime_jst = pd.Timestamp(datetime.combine(date_obj_for_event, dt_time(0,0,0)), tz='Asia/Tokyo')
                                if time_str and not any(kw in time_str for kw in ["未定", "All Day", "決定次第"]):
                                    try:
                                        event_time_obj = datetime.strptime(time_str.replace("時",":").replace("分",""), "%H:%M").time()
                                        event_datetime_jst = pd.Timestamp(datetime.combine(date_obj_for_event, event_time_obj), tz='Asia/Tokyo')
                                    except ValueError: pass
                                if indicator_name and country_text and country_text != "N/A":
                                    extracted_events_temp.append({'datetime_jst': event_datetime_jst, 'country': country_text, 'indicator': indicator_name,
                                                                  'importance': importance_str, 'forecast': current_forecast, 'result': current_result,
                                                                  'previous': current_previous, 'source_tag_type': 'table_calendar'
                                                             })
                        except Exception as e_inner_parse: # line 167のtryに対応するexcept
                            print(f"    指標カレンダーテーブル内部解析エラー (行 {row_idx}, 時刻 {time_str}): {e_inner_parse}")
                            continue # この行の処理をスキップ
                else: print(f"  指標カレンダーテーブルの行が見つかりませんでした。") # if rows: の else
            else: print(f"  指標カレンダーテーブルが見つかりませんでした。") # if indicator_table: の else
        else: print(f"  <div class='c-shihyo-calendar'> が見つかりませんでした。") # if shihyo_calendar_div: の else
        
        # --- 抽出結果の整理と最終リストへの追加 (インデントを修正) ---
        if extracted_events_temp:
            df_temp_events = pd.DataFrame(extracted_events_temp)
            df_temp_events.drop_duplicates(subset=['datetime_jst', 'country', 'indicator'], keep='first', inplace=True)
            events_for_date.extend(df_temp_events.to_dict('records'))
            extracted_count_for_day = len(events_for_date)

        if extracted_count_for_day > 0:
            print(f"  {target_date_str} から合計 {extracted_count_for_day} 件のイベント情報を抽出しました (重複削除後)。")
        else:
            print(f"  {target_date_str} からは有効なイベント情報が見つかりませんでした。")
            
    except requests.exceptions.HTTPError as e_http:
        if e_http.response.status_code == 404: print(f"  ページが見つかりませんでした (404 Not Found): {url}")
        else: print(f"  HTTPエラーが発生しました: {url} - {e_http}")
    except requests.exceptions.RequestException as e_req: print(f"  URLへのリクエスト中にエラー: {url} - {e_req}")
    except Exception as e_general: print(f"  予期せぬエラー ({target_date_str}): {e_general}")
    return events_for_date

# --- メイン処理 ---
if __name__ == "__main__":
    all_events = []
    
    # --- 日付範囲の設定 ---
    # date_to = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9))) # JSTの現在日時
    # date_from = date_to - timedelta(days=5*365) # 5年前
    # # テスト用に期間を短縮 (例: 直近7日間)
    date_from = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9))) - timedelta(days=5*365)
    date_to = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9)))

    current_date = date_from
    target_dates_str = []
    while current_date <= date_to:
        if current_date.weekday() < 5: # 月曜日(0)から金曜日(4)まで
            target_dates_str.append(current_date.strftime("%Y%m%d"))
        current_date += timedelta(days=1)
    
    print(f"経済指標データの取得を開始します (対象期間: {date_from.strftime('%Y.%m.%d')} - {date_to.strftime('%Y.%m.%d')})")
    print(f"処理対象の日付 (平日のみ): {len(target_dates_str)} 日間")

    for i, date_str_yyyymmdd in enumerate(target_dates_str):
        print(f"\n--- {i+1}/{len(target_dates_str)} : {date_str_yyyymmdd} のデータを取得中 ---")
        daily_events = get_economic_indicators_for_date(date_str_yyyymmdd)
        if daily_events:
            all_events.extend(daily_events)
        if len(target_dates_str) > 1 and i < len(target_dates_str) - 1: # 最後の呼び出し以外
            wait_time = random.uniform(1.5, 3.5) # 1.5秒から3.5秒のランダムな待機
            print(f"    {wait_time:.1f}秒待機...")
            time.sleep(wait_time) 

    if all_events:
        df_indicators = pd.DataFrame(all_events)
        df_indicators = df_indicators[df_indicators['country'].notna() & (df_indicators['country'] != 'N/A') & (df_indicators['country'] != '')].copy()
        df_indicators = df_indicators[df_indicators['indicator'].str.len() >= 2].copy() # 指標名が2文字以上のものを維持 (以前は3)
        # 数値のみの指標を除外 (例: +2.4%)
        df_indicators = df_indicators[~df_indicators['indicator'].str.fullmatch(r'[+-]?\d{1,3}(\.\d{1,2})?%?')].copy()

        df_indicators.drop_duplicates(subset=['datetime_jst', 'country', 'indicator'], keep='first', inplace=True)
        df_indicators.sort_values(by='datetime_jst', inplace=True)
        df_indicators.reset_index(drop=True, inplace=True)
        
        # datetime_jst を YYYY.MM.DD HH:MM 形式の文字列に変換
        if 'datetime_jst' in df_indicators.columns:
            df_indicators['datetime_jst'] = pd.to_datetime(df_indicators['datetime_jst']).dt.strftime('%Y.%m.%d %H:%M')

        print("\n--- 取得した経済指標データ (最終整形後) ---")
        final_display_cols = ['datetime_jst', 'country', 'indicator', 'importance'] 
        existing_final_cols = [col for col in final_display_cols if col in df_indicators.columns]
        pd.set_option('display.max_rows', None); pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 2000); pd.set_option('display.max_colwidth', 150)
        
        if not df_indicators.empty and existing_final_cols:
            print(df_indicators[existing_final_cols])
        else:
            print("フィルタリングの結果、表示するデータがありませんでした。")

        print(f"\n最終的に {len(df_indicators)} 件の経済指標を取得しました。")
        
        # 変更: 出力ディレクトリをファイルパスに含める
        csv_filename = os.path.join(OUTPUT_DIR, f"economic_indicators_{date_from.strftime('%Y%m%d')}-{date_to.strftime('%Y%m%d')}.csv")
        if not df_indicators.empty and existing_final_cols:
            df_indicators[existing_final_cols].to_csv(csv_filename, index=False, encoding='utf-8-sig')
            print(f"経済指標データを {csv_filename} に保存しました。")
        else:
            print(f"{csv_filename} への保存はスキップされました。")
    else:
        print("経済指標データは取得できませんでした。")