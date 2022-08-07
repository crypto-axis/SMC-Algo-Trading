import time, datetime
from enum import Enum
import pandas as pd
import pymt5adapter as mt5


class TF(Enum):
    s5 = 5
    s10 = 10
    s15 = 15
    s30 = 30
    m1 = 60
    m3 = 3 * 60
    m5 = 5 * 60
    m10 = 10 * 60
    m15 = 15 * 60
    m30 = 30 * 60
    m45 = 45 * 60
    h1 = 1 * 60 * 60
    h2 = 2 * 60 * 60
    h3 = 3 * 60 * 60
    h4 = 4 * 60 * 60
    h8 = 8 * 60 * 60
    h12 = 12 * 60 * 60
    d1 = 1 * 24 * 60 * 60
    w1 = 7 * 24 * 60 * 60


def mt5_get_tick(symbol, _from, _to):
    tick = mt5.copy_ticks_range(symbol, _from, _to, mt5.COPY_TICKS_INFO)
    tick = pd.DataFrame(tick)

    tick = tick[["time", "bid", "ask"]]
    tick['price'] = (tick['bid'] + tick['ask']) / 2

    tick = tick[['time', 'price']]

    tick = tick.to_dict('records')

    return tick


def candle_from_tick(ticks, timeframe):
    start_time = time.time()

    first = datetime.datetime.fromtimestamp(ticks[0]['time'])
    last = datetime.datetime.fromtimestamp(ticks[-1]['time'])

    # Build the starting point before the first tick
    start = first
    start = start.replace(second=0)

    if timeframe.value > 59:
        start = start.replace(minute=0)

    if timeframe.value > 3599:
        start = start.replace(hour=0)

    if timeframe.value > (7 * 24 * 60 * 60) - 1:
        delta = datetime.timedelta(days=start.isoweekday() - 1)
        start = start - delta

    # extract the empty 'tick blocks' that will be used for build candles later

    start = start.timestamp()
    last = last.timestamp()

    next = start + timeframe.value

    tick_block = []

    while next < last:
        data = {
            'open_time': start + 1,
            'close_time': next,
            'ticks': []
        }
        tick_block.append(data)
        next += timeframe.value
        start += timeframe.value

    data = {
        'open_time': start + 1,
        'close_time': next,
        'ticks': []
    }
    tick_block.append(data)

    i = 0

    # fill the 'tick blocks' with relevant ticks

    for candle in tick_block:
        while i < len(ticks) - 1:
            stop = False
            start = candle['open_time']
            end = candle['close_time']

            if start <= ticks[i]['time'] <= end:
                candle['ticks'].append(ticks[i])
                i += 1
            else:
                break

    # extract OHLC data from tick blocks and buils candle data

    candles = []

    _time, _open, high, low, close = None, None, None, None, None

    for candle in tick_block:
        _time = round(candle['open_time'] - 1)

        if len(candle['ticks']) > 0:
            _open = round(candle['ticks'][0]['price'], 5)
            close = round(candle['ticks'][-1]['price'], 5)
            high = round(max(candle['ticks'], key=lambda x: x['price'])['price'], 5)
            low = round(min(candle['ticks'], key=lambda x: x['price'])['price'], 5)

        else:
            _open, high, low = close, close, close

        data = {
            'time': _time,
            'open': _open,
            'high': high,
            'low': low,
            'close': close
        }

        candles.append(data)

    # remove the firsts 'empty' candles
    while True:
        if candles[0]['open'] is None:
            candles.pop(0)
        else:
            break

    # link open price to last close price
    for i in range(1, len(candles)):
        candles[i]['open'] = candles[i - 1]['close']
        if candles[i]['open'] < candles[i]['low']:
            candles[i]['low'] = candles[i]['open']
        if candles[i]['open'] > candles[i]['high']:
            candles[i]['high'] = candles[i]['open']

    return candles
