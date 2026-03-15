import numpy as np
import pandas as pd
import ta
import os
import keras
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
import joblib
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from keras.saving import register_keras_serializable
from fundamental import get_fundamentals

@register_keras_serializable(package="Custom")
class CompatibleLSTM(tf.keras.layers.LSTM):
    def __init__(self, *args, **kwargs):
        kwargs.pop('time_major', None)
        kwargs.pop('implementation', None)
        super().__init__(*args, **kwargs)


def load_model_safely(ticker):
    # Define all custom objects needed for loading
    custom_objects = {
        'CompatibleLSTM': CompatibleLSTM,
        'Bidirectional': tf.keras.layers.Bidirectional,
        # Add any other custom layers used in your models
    }
    
    # Try loading from different formats
    model_paths = [
        f"models/{ticker}.keras",
        f"models/{ticker}.h5",
    ]
    
    for path in model_paths:
        if os.path.exists(path):
            try:
                return tf.keras.models.load_model(
                    f"models/{ticker}.h5",
                    custom_objects=custom_objects,
                    compile=False
                )
            except Exception as e:
                print(f"Failed to load {path}: {str(e)}")
    raise ValueError(f"Could not load model for {ticker}")

FEATURES = ['Close', 'SMA_50', 'SMA_26', 'SMA_12', 'RSI', 'STOCH', 'MACD_SIGNAL',
            'ATR', 'BB_UPPER', 'BB_LOWER', 'OBV', '52_WEEK_HIGH', '52_WEEK_LOW',
            'Price_Change', 'Price_Change_Direction']

def calculate_technical_indicators(df):
    """Calculate all technical indicators"""
    # Trend Indicators
    df['SMA_50'] = df['Close'].squeeze().rolling(window=50).mean()
    df['SMA_26'] = df['Close'].squeeze().rolling(window=26).mean()
    df['SMA_12'] = df['Close'].squeeze().rolling(window=12).mean()

    # Momentum Indicators
    df['RSI'] = ta.momentum.RSIIndicator(df['Close'].squeeze()).rsi()
    df['STOCH'] = ta.momentum.StochasticOscillator(df['High'].squeeze(), df['Low'].squeeze(), df['Close'].squeeze()).stoch()
    df['MACD_SIGNAL'] = ta.trend.MACD(df['Close'].squeeze()).macd_signal()

    # Volatility Indicators
    df['ATR'] = ta.volatility.AverageTrueRange(df['High'].squeeze(), df['Low'].squeeze(), df['Close'].squeeze(), window=14).average_true_range()
    
    bb = ta.volatility.BollingerBands(close=df['Close'].squeeze(), window=20, window_dev=2)
    df['BB_UPPER'] = bb.bollinger_hband()
    df['BB_MIDDLE'] = bb.bollinger_mavg()
    df['BB_LOWER'] = bb.bollinger_lband()

    # Volume Indicators
    df['OBV'] = ta.volume.OnBalanceVolumeIndicator(df['Close'].squeeze(), df['Volume'].squeeze()).on_balance_volume()

    # Custom Features
    df['52_WEEK_HIGH'] = df['High'].squeeze().rolling(window=52).max()
    df['52_WEEK_LOW'] = df['Low'].squeeze().rolling(window=52).min()
    df['Price_Change'] = df['Close'].squeeze().pct_change()
    df['Price_Change_Direction'] = np.where(df['Price_Change'] > 0, 1, 0)
    
    # Add additional indicators for 3D visualization
    df['Log_Returns'] = np.log(df['Close'].squeeze()/df['Close'].squeeze().shift(1))
    df['Volatility'] = df['Log_Returns'].rolling(window=20).std() * np.sqrt(252)
    
    return df.dropna()

def predict_price(ticker, historical_data):
    """Make prediction for given stock"""
    try:
        # Load model and scalers
        model = load_model_safely(ticker)
        feature_scaler = joblib.load(f'scalers/{ticker}_feature_scaler.save')
        target_scaler = joblib.load(f'scalers/{ticker}_target_scaler.save')
        
        # Calculate indicators
        processed = calculate_technical_indicators(historical_data)
        features = processed[FEATURES].tail(67)  # Last 60 days
        
        # Scale features
        scaled = feature_scaler.transform(features)
        
        # Predict
        prediction = []
        for i in range(0, 8):
            sequence = scaled[i:60+i]
            pred = model.predict(np.array([sequence]))
            inv_pred = target_scaler.inverse_transform(pred.reshape(-1, 1))[0][0]
            prediction.append(round(inv_pred, 2))

            
        # prediction = [round(temp[0], 2) for temp in prediction]  # Convert list of arrays to flat list of floats

        # test_pred = target_scaler.inverse_transform(prediction.reshape(-1,1)).flatten()
        test_actual = features['Close'].squeeze()
        
        accuracy_data = calculate_recent_accuracy(
            pd.Series(test_actual[-7:]), 
            pd.Series(prediction[-8:-1]))
        
        # Inverse transform
        return {
            'predicted': round(prediction[-1], 2),
            'accuracy_calc' : accuracy_data
        }
    
    except Exception as e:
        raise ValueError(f"Prediction failed: {str(e)}")

def generate_3d_plot(df):
    """Create interactive 3D price-velocity-acceleration plot"""
    df['Velocity'] = df['Close'].diff()
    df['Acceleration'] = df['Velocity'].diff()
    
    fig = go.Figure(data=[go.Scatter3d(
        x=df.index,
        y=df['Velocity'],
        z=df['Acceleration'],
        mode='markers',
        marker=dict(
            size=4,
            color=df['Close'],
            colorscale='Viridis',
            opacity=0.8
        ),
        text=df['Close']
    )])
    
    fig.update_layout(
        scene=dict(
            xaxis_title='Date',
            yaxis_title='Price Velocity',
            zaxis_title='Price Acceleration'
        ),
        title='3D Price Movement Analysis'
    )
    return fig.to_html(full_html=False)

def generate_recommendation(analysis):
    """AI-powered trading recommendation"""
    score = 0
    reasons = []
    
    # RSI Analysis
    if analysis['current_rsi'] < 30:
        score += 1.5
        reasons.append("Oversold (RSI < 30)")
    elif analysis['current_rsi'] > 70:
        score -= 1.5
        reasons.append("Overbought (RSI > 70)")
    
    # Price Position Analysis
    current_price = analysis['current_price']
    price_position = ((current_price - analysis['week_52_low']) / (analysis['week_52_high'] - analysis['week_52_low'])) * 100
    
    if price_position < 30:
        score += 1
        reasons.append("Near 52-week low")
    elif price_position > 70:
        score -= 1
        reasons.append("Near 52-week high")
    
    # Generate recommendation
    if score >= 2:
        return "STRONG BUY", reasons
    elif score >= 0.5:
        return "BUY", reasons
    elif score <= -2:
        return "STRONG SELL", reasons
    elif score <= -0.5:
        return "SELL", reasons
    else:
        return "HOLD", ["Neutral market conditions"]
    
def calculate_risk_assessment(analysis):
    """Enhanced risk scoring with multiple factors"""
    factors = {
        'volatility': min(analysis['volatility'] / 15, 1),  # Normalized to 0-1
        'rsi_risk': abs(analysis['current_rsi'] - 50) / 50,
        'liquidity_risk': 1 - min(analysis['fundamentals']["avgVolume"] / 500000, 1),
        'valuation_risk': min(analysis['fundamentals']["peRatio"] / 30, 1) if analysis['fundamentals']["peRatio"] else 0.5
    }
    
    # Weighted average
    weights = {
        'volatility': 0.4,
        'rsi_risk': 0.3,
        'liquidity_risk': 0.2,
        'valuation_risk': 0.1
    }
    
    risk_score = sum(factors[factor] * weights[factor] for factor in factors)
    return min(max(round(risk_score * 10, 1), 1), 10)  # 1-10 scale

def calculate_confidence_score(reasons, analysis):
    """Calculate confidence score based on signal strength"""
    score = 0
    
    # RSI impact
    if analysis['current_rsi'] < 30 or analysis['current_rsi'] > 70:
        score += 30
        
    # Volume trend
    if analysis['obv_trend'] == "Bullish":
        score += 15
        
    # Price position
    current = analysis['current_price']
    low = analysis['fundamentals']["52WeekLow"]
    high = analysis['fundamentals']["52WeekHigh"]
    position = (current - low) / (high - low) if high != low else 0.5
    if position < 0.3 or position > 0.7:
        score += 20
        
    # Number of supporting reasons
    score += min(len(reasons) * 10, 35)
    
    return min(max(score, 30), 95)  # Keep between 30-95%

def calculate_recent_accuracy(actual_prices, predicted_prices):
    """Calculate accuracy metrics with trend indicator"""
    errors = np.abs(np.array(actual_prices) - np.array(predicted_prices))
    accuracy_percent = 100 * (1 - errors/np.array(actual_prices))
    
    # Calculate trends (1=up, -1=down)
    trends = []
    for i in range(len(predicted_prices)):
        if i == 0:
            # Compare first prediction to previous actual
            trends.append(1 if predicted_prices[i] > actual_prices[i] else -1)
        else:
            # Compare current prediction to previous actual
            trends.append(1 if predicted_prices[i] > actual_prices[i-1] else -1)
    
    return {
        'dates': actual_prices.index.strftime('%Y-%m-%d').tolist(),
        'actual': actual_prices.round(2).tolist(),
        'predicted': predicted_prices.tolist(),
        'accuracy': accuracy_percent.round(2).tolist(),
        'avg_accuracy': round(np.mean(accuracy_percent), 2),
        'trends': trends
    }

def get_stock_analysis(ticker, df, accuracy_data):
    """Comprehensive analysis with 3D visualization"""
    df = calculate_technical_indicators(df)
        
    fundamentals = get_fundamentals(ticker)
    
    # Create subplots
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=False,
        vertical_spacing=0.15,
        specs=[[{"type": "scatter"}],
               [{"type": "scatter"}],
               [{"type": "scatter"}],
               [{"type": "scatter"}]],
        subplot_titles=(
            "Price with Bollinger Bands",
            "RSI (14-day)",
            "MACD (12,26,9)",
            "Actual vs Predicted (Last 7-Days)",
        ),
        row_heights=[0.4, 0.2, 0.2, 0.2]
    )
    
    # Price and Bollinger Bands
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'].squeeze(), name='Price',
        line=dict(color='#636EFA')), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=df.index, y=df['BB_UPPER'], name='Upper Band',
        line=dict(color='#EF553B', dash='dash')), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=df.index, y=df['BB_LOWER'], name='Lower Band',
        line=dict(color='#00CC96', dash='dash')), row=1, col=1)
    
    # RSI
    fig.add_trace(go.Scatter(
        x=df.index, y=df['RSI'], name='RSI',
        line=dict(color='#AB63FA')), row=2, col=1)
    
    fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)
    
    # MACD
    fig.add_trace(go.Scatter(
        x=df.index, y=df['MACD_SIGNAL'], name='MACD',
        line=dict(color='#FFA15A')), row=3, col=1)
    
    # Actual vs Predicted
    fig.add_trace(go.Scatter(
        x=accuracy_data['dates'], y=accuracy_data['actual'],
        mode='lines+markers', name='Actual'), row=4, col=1)

    fig.add_trace(go.Scatter(
        x=accuracy_data['dates'], y=accuracy_data['predicted'],
        mode='lines+markers', name='Predicted'), row=4, col=1)

    # Generate 3D plot
    plot_3d = generate_3d_plot(df)
    
    # Update layout
    fig.update_layout(
        height=1500,
        title=f"{ticker} Advanced Analysis",
        hovermode="x unified",
        template="plotly_dark"
    )
    
    # Generate recommendation
    current_price = fundamentals['currentPrice']
    recommendation, reasons = generate_recommendation({
        'current_rsi': df['RSI'].iloc[-1],
        'current_price': current_price,
        'week_52_high': fundamentals['52WeekHigh'],
        'week_52_low': fundamentals['52WeekLow']
    })
    
    return {
        'plot_html': fig.to_html(full_html=False),
        'plot_3d': plot_3d,
        'current_rsi': round(df['RSI'].iloc[-1], 2),
        'atr': round(df['ATR'].iloc[-1], 2),
        'volatility': round(df['Volatility'].iloc[-1] * 100, 2),
        'obv_trend': "Bullish" if df['OBV'].iloc[-1] > df['OBV'].iloc[-2] else "Bearish",
        'recommendation': recommendation,
        'reasons': reasons,
        'fundamentals': fundamentals,
        'current_price': round(current_price, 2)
    }