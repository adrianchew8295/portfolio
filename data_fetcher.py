# 文件名: data_fetcher.py
# 作用: 癸水 · OpenD 官方直連數據引擎 (QQQ 1H / 5M 零延遲高速通道)

import datetime
from datetime import timedelta
import pandas as pd
import pytz
from moomoo import *

tz_myt = pytz.timezone("Asia/Kuala_Lumpur")
tz_ny = pytz.timezone("America/New_York")

def fetch_raw_data_with_retry(period_5m="1mo", max_retries=2):
    """
    透過本地 OpenD 獲取 QQQ 的 1H 與 5M 歷史/實時 K 線數據
    """
    df_1h, df_5m = None, None
    err_log = []
    
    quote_ctx = None
    try:
        quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
    except Exception as e:
        err_log.append(f"無法連接本地 OpenD (127.0.0.1:11111): {str(e)}")
        return None, None, err_log

    today_ny = datetime.datetime.now(tz_ny).date()
    start_date_1h = (today_ny - timedelta(days=90)).strftime("%Y-%m-%d")
    start_date_5m = (today_ny - timedelta(days=35)).strftime("%Y-%m-%d")
    end_date_str = today_ny.strftime("%Y-%m-%d")

    # 1. 抓取 QQQ 1H (60分) K線
    try:
        ret_1h, data_1h, _ = quote_ctx.request_history_kline(
            code='US.QQQ',
            start=start_date_1h,
            end=end_date_str,
            ktype=KLType.K_60M,
            autype=AuType.QFQ,
            max_count=1000
        )
        if ret_1h == RET_OK and not data_1h.empty:
            df_t = data_1h.copy()
            df_t["time_key"] = pd.to_datetime(df_t["time_key"])
            df_t.set_index("time_key", inplace=True)
            df_t.rename(columns={
                "open": "Open", "high": "High", "low": "Low", 
                "close": "Close", "volume": "Volume"
            }, inplace=True)
            df_1h = df_t[["Open", "High", "Low", "Close", "Volume"]].sort_index()
            # 轉換為美東時區
            if df_1h.index.tz is None:
                df_1h.index = df_1h.index.tz_localize("America/New_York")
            else:
                df_1h.index = df_1h.index.tz_convert(tz_ny)
        else:
            err_log.append(f"OpenD 1H 數據抓取失敗: {data_1h}")
    except Exception as e:
        err_log.append(f"OpenD 1H 異常: {str(e)}")

    # 2. 抓取 QQQ 5M K線
    try:
        ret_5m, data_5m, _ = quote_ctx.request_history_kline(
            code='US.QQQ',
            start=start_date_5m,
            end=end_date_str,
            ktype=KLType.K_5M,
            autype=AuType.QFQ,
            max_count=3000
        )
        if ret_5m == RET_OK and not data_5m.empty:
            df_t5 = data_5m.copy()
            df_t5["time_key"] = pd.to_datetime(df_t5["time_key"])
            df_t5.set_index("time_key", inplace=True)
            df_t5.rename(columns={
                "open": "Open", "high": "High", "low": "Low", 
                "close": "Close", "volume": "Volume"
            }, inplace=True)
            df_5m = df_t5[["Open", "High", "Low", "Close", "Volume"]].sort_index()
            if df_5m.index.tz is None:
                df_5m.index = df_5m.index.tz_localize("America/New_York")
            else:
                df_5m.index = df_5m.index.tz_convert(tz_ny)
        else:
            err_log.append(f"OpenD 5M 數據抓取失敗: {data_5m}")
    except Exception as e:
        err_log.append(f"OpenD 5M 異常: {str(e)}")

    if quote_ctx:
        quote_ctx.close()

    return df_1h, df_5m, err_log
