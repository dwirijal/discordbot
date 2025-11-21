import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
import talib

@dataclass
class IndicatorResult:
    """Container for indicator results"""
    value: float
    signal: str
    confidence: float
    description: str

class TechnicalIndicators:
    """Advanced technical indicators with enhanced calculations"""

    @staticmethod
    def sma(data: np.ndarray, period: int = 20) -> np.ndarray:
        """Simple Moving Average"""
        return talib.SMA(data, timeperiod=period)

    @staticmethod
    def ema(data: np.ndarray, period: int = 20) -> np.ndarray:
        """Exponential Moving Average"""
        return talib.EMA(data, timeperiod=period)

    @staticmethod
    def rsi(data: np.ndarray, period: int = 14) -> np.ndarray:
        """Relative Strength Index"""
        return talib.RSI(data, timeperiod=period)

    @staticmethod
    def macd(data: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """MACD - Returns (macd, signal, histogram)"""
        macd, signal_line, histogram = talib.MACD(data, fastperiod=fast, slowperiod=slow, signalperiod=signal)
        return macd, signal_line, histogram

    @staticmethod
    def bollinger_bands(data: np.ndarray, period: int = 20, std_dev: int = 2) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Bollinger Bands - Returns (upper, middle, lower)"""
        upper, middle, lower = talib.BBANDS(data, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
        return upper, middle, lower

    @staticmethod
    def stochastic_oscillator(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                            k_period: int = 14, d_period: int = 3) -> Tuple[np.ndarray, np.ndarray]:
        """Stochastic Oscillator - Returns (%K, %D)"""
        slowk, slowd = talib.STOCH(high, low, close, fastk_period=k_period,
                                  slowk_period=d_period, slowd_period=d_period)
        return slowk, slowd

    @staticmethod
    def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """Average True Range"""
        return talib.ATR(high, low, close, timeperiod=period)

    @staticmethod
    def vwap(high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Volume Weighted Average Price"""
        typical_price = (high + low + close) / 3
        return np.cumsum(typical_price * volume) / np.cumsum(volume)

    @staticmethod
    def cmf(high: np.ndarray, low: np.ndarray, close: np.ndarray,
            volume: np.ndarray, period: int = 20) -> np.ndarray:
        """Chaikin Money Flow"""
        mfv = ((close - low) - (high - close)) / (high - low)
        mfv = np.where((high - low) == 0, 0, mfv)
        mfv *= volume

        cmf_values = []
        for i in range(period - 1, len(mfv)):
            cmf_values.append(np.sum(mfv[i - period + 1:i + 1]) / np.sum(volume[i - period + 1:i + 1]))

        # Pad with NaN for initial values
        return np.array([np.nan] * (period - 1) + cmf_values)

    @staticmethod
    def williams_r(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """Williams %R"""
        return talib.WILLR(high, low, close, timeperiod=period)

    @staticmethod
    def cci(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 20) -> np.ndarray:
        """Commodity Channel Index"""
        return talib.CCI(high, low, close, timeperiod=period)

    @staticmethod
    def adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """Average Directional Index"""
        return talib.ADX(high, low, close, timeperiod=period)

    @staticmethod
    def ichimoku_cloud(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                     tenkan_period: int = 9, kijun_period: int = 26,
                     senkou_span_b_period: int = 52) -> Dict[str, np.ndarray]:
        """Ichimoku Cloud"""
        # Tenkan-sen (Conversion Line)
        tenkan_high = pd.Series(high).rolling(tenkan_period).max()
        tenkan_low = pd.Series(low).rolling(tenkan_period).min()
        tenkan_sen = (tenkan_high + tenkan_low) / 2

        # Kijun-sen (Base Line)
        kijun_high = pd.Series(high).rolling(kijun_period).max()
        kijun_low = pd.Series(low).rolling(kijun_period).min()
        kijun_sen = (kijun_high + kijun_low) / 2

        # Senkou Span A (Leading Span A)
        senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun_period)

        # Senkou Span B (Leading Span B)
        senkou_span_b_high = pd.Series(high).rolling(senkou_span_b_period).max()
        senkou_span_b_low = pd.Series(low).rolling(senkou_span_b_period).min()
        senkou_span_b = ((senkou_span_b_high + senkou_span_b_low) / 2).shift(kijun_period)

        # Chikou Span (Lagging Span)
        chikou_span = pd.Series(close).shift(-kijun_period)

        return {
            'tenkan_sen': tenkan_sen.values,
            'kijun_sen': kijun_sen.values,
            'senkou_span_a': senkou_span_a.values,
            'senkou_span_b': senkou_span_b.values,
            'chikou_span': chikou_span.values
        }

    @staticmethod
    def fibonacci_retracements(high: float, low: float) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels"""
        diff = high - low
        return {
            '0.0%': low,
            '23.6%': low + 0.236 * diff,
            '38.2%': low + 0.382 * diff,
            '50.0%': low + 0.5 * diff,
            '61.8%': low + 0.618 * diff,
            '78.6%': low + 0.786 * diff,
            '100.0%': high
        }

    @staticmethod
    def pivot_points(high: float, low: float, close: float) -> Dict[str, float]:
        """Calculate Pivot Points"""
        pp = (high + low + close) / 3
        return {
            'PP': pp,
            'R1': 2 * pp - low,
            'R2': pp + (high - low),
            'R3': high + 2 * (high - low),
            'S1': 2 * pp - high,
            'S2': pp - (high - low),
            'S3': low - 2 * (high - low)
        }

    @staticmethod
    def market_profile(prices: np.ndarray, bins: int = 20) -> Dict[str, any]:
        """Basic Market Profile Analysis"""
        hist, bin_edges = np.histogram(prices, bins=bins)
        max_bin = np.argmax(hist)

        return {
            'poc': (bin_edges[max_bin] + bin_edges[max_bin + 1]) / 2,  # Point of Control
            'value_area_high': np.percentile(prices, 80),
            'value_area_low': np.percentile(prices, 20),
            'distribution': hist
        }

class AdvancedAnalytics:
    """Advanced analytics and pattern recognition"""

    @staticmethod
    def detect_fractals(data: np.ndarray, lookback: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """Detect fractal highs and lows"""
        n = len(data)
        fractal_highs = np.zeros(n)
        fractal_lows = np.zeros(n)

        for i in range(lookback, n - lookback):
            # Check for fractal high
            is_high = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i and data[j] >= data[i]:
                    is_high = False
                    break
            if is_high:
                fractal_highs[i] = data[i]

            # Check for fractal low
            is_low = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i and data[j] <= data[i]:
                    is_low = False
                    break
            if is_low:
                fractal_lows[i] = data[i]

        return fractal_highs, fractal_lows

    @staticmethod
    def detect_swing_points(data: np.ndarray, swing_period: int = 10) -> Tuple[List[int], List[int]]:
        """Detect swing highs and lows"""
        swing_highs = []
        swing_lows = []

        for i in range(swing_period, len(data) - swing_period):
            # Swing high
            is_swing_high = True
            for j in range(i - swing_period, i + swing_period + 1):
                if j != i and data[j] >= data[i]:
                    is_swing_high = False
                    break
            if is_swing_high:
                swing_highs.append(i)

            # Swing low
            is_swing_low = True
            for j in range(i - swing_period, i + swing_period + 1):
                if j != i and data[j] <= data[i]:
                    is_swing_low = False
                    break
            if is_swing_low:
                swing_lows.append(i)

        return swing_highs, swing_lows

    @staticmethod
    def calculate_volatility(data: np.ndarray, period: int = 20) -> np.ndarray:
        """Calculate rolling volatility"""
        returns = np.diff(data) / data[:-1]
        log_returns = np.log(1 + returns)
        return pd.Series(log_returns).rolling(period).std() * np.sqrt(252)  # Annualized

    @staticmethod
    def detect_divergence(price: np.ndarray, indicator: np.ndarray,
                         lookback: int = 20) -> Dict[str, any]:
        """Detect bullish and bearish divergences"""
        n = len(price)
        divergences = {'bullish': [], 'bearish': []}

        # Find peaks and troughs
        from scipy.signal import find_peaks

        price_peaks, _ = find_peaks(price)
        price_troughs, _ = find_peaks(-price)

        ind_peaks, _ = find_peaks(indicator)
        ind_troughs, _ = find_peaks(-indicator)

        # Check for bearish divergence (price higher, indicator lower)
        for p in price_peaks[-5:]:  # Check last 5 peaks
            for ip in ind_peaks[-5:]:
                if abs(p - ip) < 5:  # Within 5 bars
                    if price[p] > price[p-5] and indicator[ip] < indicator[ip-5]:
                        divergences['bearish'].append((p, ip))

        # Check for bullish divergence (price lower, indicator higher)
        for t in price_troughs[-5:]:  # Check last 5 troughs
            for it in ind_troughs[-5:]:
                if abs(t - it) < 5:  # Within 5 bars
                    if price[t] < price[t-5] and indicator[it] > indicator[it-5]:
                        divergences['bullish'].append((t, it))

        return divergences

    @staticmethod
    def momentum_score(data: np.ndarray, period: int = 14) -> IndicatorResult:
        """Calculate momentum score with signal"""
        roc = talib.ROC(data, timeperiod=period)
        current_roc = roc[-1] if not np.isnan(roc[-1]) else 0

        if current_roc > 5:
            signal = "STRONG BULLISH"
            confidence = min(100, abs(current_roc) * 10)
            description = f"Momentum is strongly positive ({current_roc:.2f}%)"
        elif current_roc > 0:
            signal = "BULLISH"
            confidence = abs(current_roc) * 10
            description = f"Momentum is positive ({current_roc:.2f}%)"
        elif current_roc > -5:
            signal = "BEARISH"
            confidence = abs(current_roc) * 10
            description = f"Momentum is slightly negative ({current_roc:.2f}%)"
        else:
            signal = "STRONG BEARISH"
            confidence = min(100, abs(current_roc) * 10)
            description = f"Momentum is strongly negative ({current_roc:.2f}%)"

        return IndicatorResult(
            value=current_roc,
            signal=signal,
            confidence=confidence,
            description=description
        )