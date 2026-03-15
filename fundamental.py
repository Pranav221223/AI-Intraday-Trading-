import yfinance as yf
import pandas as pd

def get_fundamentals(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    
    return {
        'sector': info['sector'],
        'industry': info['industry'],
        'marketCap': info['marketCap'],
        'peRatio': info['trailingPE'],
        'pbRatio': info['priceToBook'],
        'dividendYield': info['dividendYield'],
        'beta': info['beta'],
        '52WeekHigh': info['fiftyTwoWeekHigh'],
        '52WeekLow': info['fiftyTwoWeekLow'],
        'avgVolume': info['averageVolume'],
        'website': info['website'],
        'currentPrice': info['currentPrice']
    }