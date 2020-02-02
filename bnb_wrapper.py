import requests
import json
from datetime import datetime
import pandas as pd
from pandas import DataFrame as df
import hmac
import hashlib
from interval_enums import Interval
import time

class BinanceClient:

    def __init__(self, api_key, api_secret):
        self.key  = api_key
        self.secret = api_secret
        self.base = 'https://api.binance.com'
        self.endpoint = {
            'klines': '/api/v1/klines',
            'price_ticker': '/api/v3/ticker/price',
            '24hr_ticker': '/api/v3/ticker/24hr',
            'historical_trade': '/api/v3/historicalTrades',            # recent trades on the market
            'order': '/api/v3/order',
            'test_order': '/api/v3/order/test',
            'open_order': '/api/v3/openOrders',                        # all open orders
            'all_order': '/api/v3/allOrders',                          # all orders: active, cancelled, filler
            'my_trade': '/api/v3/myTrades'                             # all trades for a specific symbol on the account
        }


    '''
        return klines for a specified symbol
        @param
            required - symbol: str, interval: Interval
    '''
    def get_klines(self, symbol, interval):

        # specifying parameters for request body
        params = {
            'symbol': symbol,
            'interval': interval.value
        }
        # specifying url enpoint
        url = self.base + self.endpoint['klines']

        # get api response
        response = requests.get(url, params=params)
        # convert json to dict
        data = json.loads(response.text)

        # convert dict to data frame
        klines_df = df(data)

        # get open time and close time from klines_df
        o_timestamp_df = klines_df[0]      # open timestamp
        c_timestamp_df = klines_df[6]      # close timestamp

        # create empty arrays for formatted datetime
        o_time = []      # open time
        c_time = []      # close time
        
        # convert timestamps to datetime format
        for (o_timestamp, c_timestamp) in zip(o_timestamp_df, c_timestamp_df):
            o_time.append(datetime.fromtimestamp(int(o_timestamp/1000)))
            c_time.append(datetime.fromtimestamp(int(c_timestamp/1000)))

        # convert datetime to string datetime format for df
        o_time_df = df(o_time)
        c_time_df = df(c_time)

        # replacing the original timestamp with formatted datetime string
        klines_df[0] = o_time_df
        klines_df[6] = c_time_df

        # modifying dataframe
        klines_df.pop(11)
        klines_df.columns = ['open time', 'open', 'high', 'low', 'close',
                             'volume', 'close time', 'quote asset volume',
                             'no. of trades', 'taker buy base asset volume',
                             'taker buy quote asset volume']
        return klines_df


    '''
        return current price
            1. for a symbol if symbol is specified
            2. for all symbols
        @param
            optional - symbol: str
    '''
    def get_price(self, symbol=None):
        
        # specifying parameters for request body
        params = {
            'symbol': symbol
        }

        # specifying url endpoint
        url = self.base + self.endpoint['price_ticker']
        
        # get api response
        response = requests.get(url, params=params)
        # convert json to dict
        data = json.loads(response.text)

        # convert dict to dataframe
        if isinstance(data, list):
            price_df = df(data)
        else:
            price_df = df([data])

        return price_df


    '''
        return 24 hour ticker
            1. for a symbol if symbol is specified
            2. for all symbols
        @param
            optional - symbol: str
    '''       
    def get_24hr_ticker(self, symbol=None):

        # specify parameters for request body
        params = {
            'symbol': symbol
        }
        # specifying url endpoint
        url = self.base + self.endpoint['24hr_ticker']

        # request api response
        response = requests.get(url, params=params)
        # convert json to dict
        data = json.loads(response.text)
        
        # convert dict to dataframe
        if isinstance(data, list):
            ticker_df = df(data)
        else:
            ticker_df = df([data])

        return ticker_df


    '''
        return list of historical trades
            1. start from a specific trade if tradeId is specified upto
               the specified amount of trade records
            2. most recent trades if tradeId is not specified
                a. most recent 500 trades if limit is not specified
                b. the amount of trades specified by limit
        @param
            required - symbol: str
            optional - limit: int, tradeId: long
    '''
    def get_historical_trade(self, symbol, limit=None, tradeId=None):

        # specifying parameter for request body
        params = {
            'symbol': symbol,
            'limit': limit,
            'fromId': tradeId
        }
        # specifying url endpoint
        url = self.base + self.endpoint['historical_trade']

        # request api response
        response = requests.get(url, params=params, headers={'X-MBX-APIKEY': self.key})
        data = json.loads(response.text)

        # convert dict to dataframe
        trade_df = df(data)

        return trade_df


    '''
        get the status of an order
        @param 
            required - symbol: str, orderId: long
    '''
    def get_query_order(self, symbol, orderId):
        
        # specify parameters for request body
        params = {
            'symbol': symbol,
            'orderId': orderId,
            'timestamp': int(round(time.time()*1000))
        }
        # specify url endpoint
        url = self.base + self.endpoint['order']
        
        # sign request
        self.sign_request(params)

        # request api response
        response = requests.get(url, params=params, headers={'X-MBX-APIKEY': self.key})
        data = json.loads(response.text)

        return data


    '''
        return list of open orders
            1. of a symbol if symbol is specified
            2. of all symbols if symbol is not specified
        @param 
            optional - symbol: str
    '''
    def get_open_order(self, symbol=None):

        # specify parameters for request body
        if symbol != None:
            params = {
                'symbol': symbol,
                'timestamp': int(round(time.time()*1000))
            }
        else:
            params = {
                'timestamp': int(round(time.time()*1000))

            }
        # specify url endpoint
        url = self.base + self.endpoint['open_order']

        # sign request
        self.sign_request(params)

        # request api response
        response = requests.get(url, params=params, headers={'X-MBX-APIKEY': self.key})
        # convert json to dict
        data = json.loads(response.text)
        
        return data


    '''
        return all orders of the specified symbol: active, canceled, filled
            1. if orderId is specified, return orders with id >= orderId
            2. else, return most recent orders for this symbol 
        @param 
            required - symbol: str
            optional - orderId: long, limit: int
    '''
    def get_all_order(self, symbol, orderId=None, limit=None):

        # specify parameters for request body
        if limit == None:
            if orderId != None:
                params = {
                    'symbol': symbol,
                    'orderId': orderId,
                    'timestamp': int(round(time.time()*1000))
                }
            else: 
                params = {
                    'symbol': symbol,
                    'timestamp': int(round(time.time()*1000))
                }
        else:
            if orderId != None:
                params = {
                    'symbol': symbol,
                    'orderId': orderId,
                    'limit': limit,
                    'timestamp': int(round(time.time()*1000))
                }
            else: 
                params = {
                    'symbol': symbol,
                    'limit': limit,
                    'timestamp': int(round(time.time()*1000))
                }
        # specify url endpoint
        url = self.base + self.endpoint['all_order']

        # sign request
        self.sign_request(params)

        # request api response
        response = requests.get(url, params=params, headers={'X-MBX-APIKEY': self.key})
        # convert json to dict
        data = json.loads(response.text)

        # convert data to dataframe
        all_order_df = df(data)

        return all_order_df


    '''
        sign your request to Binance API
    '''
    def sign_request(self, params: dict):
        
        #make a query string
        query_string = '&'.join(["{}={}".format(d,params[d]) for d in params])
        
        #hashing secret
        signature = hmac.new(self.secret.encode('utf-8'), 
                             query_string.encode('utf-8'),
                             hashlib.sha256)
        
        # add your signature to the request body
        params['signature'] = signature.hexdigest()

