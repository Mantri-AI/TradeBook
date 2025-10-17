"""
Data analysis and analytics service
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import func, and_, or_
from models.database import db, Account, Position, Trade, StockData, OptionData, TradingSession
import logging

logger = logging.getLogger(__name__)

class DataAnalyzer:
    """Service for analyzing trading data and generating insights"""
    
    def __init__(self):
        pass
    
    def get_portfolio_summary(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get comprehensive portfolio summary
        
        Args:
            account_id: Optional account ID to filter by
            
        Returns:
            Dictionary with portfolio metrics
        """
        try:
            # Base query for positions
            query = db.session.query(Position).join(Account)
            if account_id:
                query = query.filter(Account.id == account_id)
            
            positions = query.filter(Account.is_active == True).all()
            
            # Calculate metrics
            total_value = sum([p.current_value for p in positions if p.current_value])
            total_day_change = sum([p.day_change for p in positions if p.day_change])
            total_return = sum([p.total_return for p in positions if p.total_return])
            
            # Position breakdown
            stock_positions = [p for p in positions if p.instrument_type == 'stock']
            option_positions = [p for p in positions if p.instrument_type == 'option']
            
            stock_value = sum([p.current_value for p in stock_positions if p.current_value])
            option_value = sum([p.current_value for p in option_positions if p.current_value])
            
            # Top positions
            top_positions = sorted(positions, key=lambda x: x.current_value or 0, reverse=True)[:10]
            
            # Sector analysis (simplified)
            sector_breakdown = self._get_sector_breakdown(positions)
            
            return {
                'total_value': total_value,
                'total_day_change': total_day_change,
                'total_return': total_return,
                'day_change_percent': (total_day_change / total_value * 100) if total_value > 0 else 0,
                'total_return_percent': (total_return / total_value * 100) if total_value > 0 else 0,
                'position_count': len(positions),
                'stock_count': len(stock_positions),
                'option_count': len(option_positions),
                'stock_value': stock_value,
                'option_value': option_value,
                'stock_percentage': (stock_value / total_value * 100) if total_value > 0 else 0,
                'option_percentage': (option_value / total_value * 100) if total_value > 0 else 0,
                'top_positions': [p.to_dict() for p in top_positions],
                'sector_breakdown': sector_breakdown
            }
            
        except Exception as e:
            logger.error(f"Error generating portfolio summary: {str(e)}")
            return {}
    
    def get_trading_performance(self, account_id: Optional[int] = None, days: int = 30) -> Dict[str, Any]:
        """
        Analyze trading performance over a period
        
        Args:
            account_id: Optional account ID to filter by
            days: Number of days to analyze
            
        Returns:
            Dictionary with performance metrics
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Base query for trades
            query = db.session.query(Trade).join(Account)
            if account_id:
                query = query.filter(Account.id == account_id)
            
            trades = query.filter(
                and_(
                    Trade.executed_at >= start_date,
                    Account.is_active == True
                )
            ).all()
            
            if not trades:
                return {}
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame([t.to_dict() for t in trades])
            
            # Basic metrics
            total_trades = len(trades)
            total_volume = df['total_amount'].sum()
            total_fees = df['fees'].sum()
            
            # Buy/Sell analysis
            buy_trades = df[df['side'] == 'buy']
            sell_trades = df[df['side'] == 'sell']
            
            buy_volume = buy_trades['total_amount'].sum() if len(buy_trades) > 0 else 0
            sell_volume = sell_trades['total_amount'].sum() if len(sell_trades) > 0 else 0
            
            # Symbol analysis
            symbol_stats = df.groupby('symbol').agg({
                'total_amount': 'sum',
                'quantity': 'sum',
                'fees': 'sum'
            }).reset_index()
            
            top_symbols = symbol_stats.nlargest(10, 'total_amount').to_dict('records')
            
            # Daily trading analysis
            df['date'] = pd.to_datetime(df['executed_at']).dt.date
            daily_stats = df.groupby('date').agg({
                'total_amount': 'sum',
                'fees': 'sum',
                'quantity': 'count'
            }).reset_index()
            
            # Calculate realized P&L (simplified)
            realized_pnl = self._calculate_realized_pnl(trades)
            
            return {
                'period_days': days,
                'total_trades': total_trades,
                'total_volume': total_volume,
                'total_fees': total_fees,
                'buy_trades': len(buy_trades),
                'sell_trades': len(sell_trades),
                'buy_volume': buy_volume,
                'sell_volume': sell_volume,
                'net_volume': sell_volume - buy_volume,
                'average_trade_size': total_volume / total_trades if total_trades > 0 else 0,
                'daily_avg_trades': total_trades / days,
                'top_symbols': top_symbols,
                'daily_stats': daily_stats.to_dict('records'),
                'realized_pnl': realized_pnl,
                'win_rate': self._calculate_win_rate(trades),
                'avg_hold_time': self._calculate_avg_hold_time(trades)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trading performance: {str(e)}")
            return {}
    
    def get_position_analytics(self, symbol: Optional[str] = None, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get detailed position analytics
        
        Args:
            symbol: Optional symbol to filter by
            account_id: Optional account ID to filter by
            
        Returns:
            Dictionary with position analytics
        """
        try:
            # Base query
            query = db.session.query(Position).join(Account)
            
            if account_id:
                query = query.filter(Account.id == account_id)
            if symbol:
                query = query.filter(Position.symbol == symbol)
            
            positions = query.filter(Account.is_active == True).all()
            
            if not positions:
                return {}
            
            # Convert to DataFrame
            df = pd.DataFrame([p.to_dict() for p in positions])
            
            # Analytics by symbol
            symbol_analytics = df.groupby('symbol').agg({
                'current_value': 'sum',
                'total_return': 'sum',
                'day_change': 'sum',
                'quantity': 'sum'
            }).reset_index()
            
            # Risk metrics
            portfolio_value = df['current_value'].sum()
            symbol_analytics['weight'] = symbol_analytics['current_value'] / portfolio_value * 100
            symbol_analytics['return_pct'] = symbol_analytics['total_return'] / symbol_analytics['current_value'] * 100
            
            # Concentration analysis
            concentration_risk = {
                'max_position_weight': symbol_analytics['weight'].max(),
                'top_5_weight': symbol_analytics.nlargest(5, 'weight')['weight'].sum(),
                'top_10_weight': symbol_analytics.nlargest(10, 'weight')['weight'].sum(),
                'herfindahl_index': (symbol_analytics['weight'] ** 2).sum() / 100
            }
            
            # Performance analysis
            winners = symbol_analytics[symbol_analytics['return_pct'] > 0]
            losers = symbol_analytics[symbol_analytics['return_pct'] < 0]
            
            performance_metrics = {
                'total_positions': len(symbol_analytics),
                'winners': len(winners),
                'losers': len(losers),
                'win_rate': len(winners) / len(symbol_analytics) * 100 if len(symbol_analytics) > 0 else 0,
                'avg_return': symbol_analytics['return_pct'].mean(),
                'best_performer': symbol_analytics.loc[symbol_analytics['return_pct'].idxmax()].to_dict() if len(symbol_analytics) > 0 else {},
                'worst_performer': symbol_analytics.loc[symbol_analytics['return_pct'].idxmin()].to_dict() if len(symbol_analytics) > 0 else {}
            }
            
            return {
                'symbol_analytics': symbol_analytics.to_dict('records'),
                'concentration_risk': concentration_risk,
                'performance_metrics': performance_metrics,
                'portfolio_value': portfolio_value
            }
            
        except Exception as e:
            logger.error(f"Error analyzing positions: {str(e)}")
            return {}
    
    def get_options_analytics(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get options-specific analytics
        
        Args:
            account_id: Optional account ID to filter by
            
        Returns:
            Dictionary with options analytics
        """
        try:
            # Get options positions
            query = db.session.query(Position).join(Account).filter(Position.instrument_type == 'option')
            
            if account_id:
                query = query.filter(Account.id == account_id)
            
            positions = query.filter(Account.is_active == True).all()
            
            if not positions:
                return {}
            
            # Convert to DataFrame
            df = pd.DataFrame([p.to_dict() for p in positions])
            
            # Options breakdown
            call_positions = df[df['option_type'] == 'call']
            put_positions = df[df['option_type'] == 'put']
            
            # Expiration analysis
            df['expiration_date'] = pd.to_datetime(df['expiration_date'])
            df['days_to_expiry'] = (df['expiration_date'] - pd.Timestamp.now()).dt.days
            
            # Categorize by expiration
            df['expiry_category'] = pd.cut(
                df['days_to_expiry'],
                bins=[-float('inf'), 7, 30, 90, float('inf')],
                labels=['< 1 week', '1-4 weeks', '1-3 months', '> 3 months']
            )
            
            expiry_breakdown = df.groupby('expiry_category')['current_value'].sum().to_dict()
            
            # Strike analysis
            current_prices = {}  # Would need to fetch current stock prices
            
            # Greeks analysis (if available)
            greeks_summary = {
                'total_positions': len(positions),
                'call_positions': len(call_positions),
                'put_positions': len(put_positions),
                'call_value': call_positions['current_value'].sum() if len(call_positions) > 0 else 0,
                'put_value': put_positions['current_value'].sum() if len(put_positions) > 0 else 0,
                'expiry_breakdown': expiry_breakdown,
                'avg_days_to_expiry': df['days_to_expiry'].mean(),
                'near_expiry_count': len(df[df['days_to_expiry'] <= 7]),
                'far_expiry_count': len(df[df['days_to_expiry'] > 90])
            }
            
            return greeks_summary
            
        except Exception as e:
            logger.error(f"Error analyzing options: {str(e)}")
            return {}
    
    def _get_sector_breakdown(self, positions: List[Position]) -> Dict[str, float]:
        """
        Get sector breakdown for positions (simplified mapping)
        This is a basic implementation - in production you'd use a proper sector mapping service
        """
        sector_map = {
            # Tech stocks
            'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 'GOOG': 'Technology',
            'AMZN': 'Technology', 'TSLA': 'Technology', 'META': 'Technology', 'NVDA': 'Technology',
            # Finance
            'JPM': 'Finance', 'BAC': 'Finance', 'WFC': 'Finance', 'GS': 'Finance',
            # Healthcare
            'JNJ': 'Healthcare', 'PFE': 'Healthcare', 'ABBV': 'Healthcare', 'MRK': 'Healthcare',
            # Consumer
            'KO': 'Consumer Goods', 'PEP': 'Consumer Goods', 'WMT': 'Consumer Goods', 'PG': 'Consumer Goods'
        }
        
        sector_values = {}
        total_value = sum([p.current_value for p in positions if p.current_value])
        
        for position in positions:
            sector = sector_map.get(position.symbol, 'Other')
            if sector not in sector_values:
                sector_values[sector] = 0
            sector_values[sector] += position.current_value or 0
        
        # Convert to percentages
        sector_percentages = {
            sector: (value / total_value * 100) if total_value > 0 else 0
            for sector, value in sector_values.items()
        }
        
        return sector_percentages
    
    def _calculate_realized_pnl(self, trades: List[Trade]) -> float:
        """
        Calculate realized P&L from trades (simplified)
        This is a basic implementation - proper P&L calculation requires FIFO/LIFO accounting
        """
        pnl = 0
        symbol_positions = {}
        
        for trade in sorted(trades, key=lambda x: x.executed_at):
            symbol = trade.symbol
            if symbol not in symbol_positions:
                symbol_positions[symbol] = {'quantity': 0, 'cost_basis': 0}
            
            if trade.side == 'buy':
                # Add to position
                total_cost = symbol_positions[symbol]['cost_basis'] + trade.total_amount
                total_quantity = symbol_positions[symbol]['quantity'] + trade.quantity
                symbol_positions[symbol] = {
                    'quantity': total_quantity,
                    'cost_basis': total_cost
                }
            elif trade.side == 'sell':
                # Reduce position and calculate P&L
                if symbol_positions[symbol]['quantity'] > 0:
                    avg_cost = symbol_positions[symbol]['cost_basis'] / symbol_positions[symbol]['quantity']
                    realized_gain = (trade.price - avg_cost) * trade.quantity
                    pnl += realized_gain
                    
                    # Update position
                    symbol_positions[symbol]['quantity'] -= trade.quantity
                    symbol_positions[symbol]['cost_basis'] -= avg_cost * trade.quantity
        
        return pnl
    
    def _calculate_win_rate(self, trades: List[Trade]) -> float:
        """Calculate win rate from completed trades"""
        # This is a simplified implementation
        # Proper win rate calculation requires matching buy/sell pairs
        return 0.0  # Placeholder
    
    def _calculate_avg_hold_time(self, trades: List[Trade]) -> float:
        """Calculate average holding time"""
        # This is a simplified implementation
        # Proper calculation requires matching buy/sell pairs
        return 0.0  # Placeholder