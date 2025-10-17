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
    
    # New enhanced analytics methods
    def get_cross_account_analytics(self, account_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Get analytics across multiple accounts
        
        Args:
            account_ids: Optional list of account IDs to include
            
        Returns:
            Dictionary with cross-account analytics
        """
        try:
            # Base query for trades
            query = db.session.query(Trade).join(Account)
            if account_ids:
                query = query.filter(Account.id.in_(account_ids))
            
            trades = query.filter(Account.is_active == True).all()
            
            # Group by account
            accounts_data = {}
            for trade in trades:
                account_name = trade.account.name
                if account_name not in accounts_data:
                    accounts_data[account_name] = {
                        'trades': [],
                        'total_volume': 0,
                        'buy_volume': 0,
                        'sell_volume': 0,
                        'symbols': set()
                    }
                
                accounts_data[account_name]['trades'].append(trade)
                accounts_data[account_name]['total_volume'] += abs(trade.total_amount)
                accounts_data[account_name]['symbols'].add(trade.symbol)
                
                if trade.side == 'buy':
                    accounts_data[account_name]['buy_volume'] += abs(trade.total_amount)
                else:
                    accounts_data[account_name]['sell_volume'] += abs(trade.total_amount)
            
            # Convert sets to counts
            for account_name in accounts_data:
                accounts_data[account_name]['unique_symbols'] = len(accounts_data[account_name]['symbols'])
                del accounts_data[account_name]['symbols']
            
            return {
                'success': True,
                'accounts_data': accounts_data,
                'total_accounts': len(accounts_data),
                'combined_volume': sum([acc['total_volume'] for acc in accounts_data.values()]),
                'combined_trades': len(trades)
            }
            
        except Exception as e:
            logger.error(f"Error in cross-account analytics: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    def get_instrument_analytics(self, symbol: str, account_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Get detailed analytics for a specific instrument
        
        Args:
            symbol: Stock/option symbol to analyze
            account_ids: Optional list of account IDs to include
            
        Returns:
            Dictionary with instrument analytics
        """
        try:
            # Base query for trades
            query = db.session.query(Trade).join(Account).filter(Trade.symbol == symbol.upper())
            if account_ids:
                query = query.filter(Account.id.in_(account_ids))
            
            trades = query.filter(Account.is_active == True).order_by(Trade.activity_date).all()
            
            if not trades:
                return {'success': False, 'message': f'No trades found for {symbol}'}
            
            # Calculate metrics
            total_quantity_bought = sum([t.quantity for t in trades if t.side == 'buy'])
            total_quantity_sold = sum([t.quantity for t in trades if t.side == 'sell'])
            total_buy_amount = sum([t.total_amount for t in trades if t.side == 'buy'])
            total_sell_amount = sum([t.total_amount for t in trades if t.side == 'sell'])
            
            avg_buy_price = total_buy_amount / total_quantity_bought if total_quantity_bought > 0 else 0
            avg_sell_price = total_sell_amount / total_quantity_sold if total_quantity_sold > 0 else 0
            
            # P&L calculation (simplified)
            realized_pnl = total_sell_amount - total_buy_amount
            
            # Transaction code analysis
            trans_code_stats = {}
            for trade in trades:
                if trade.trans_code not in trans_code_stats:
                    trans_code_stats[trade.trans_code] = {
                        'count': 0,
                        'total_amount': 0,
                        'total_quantity': 0
                    }
                trans_code_stats[trade.trans_code]['count'] += 1
                trans_code_stats[trade.trans_code]['total_amount'] += trade.total_amount
                trans_code_stats[trade.trans_code]['total_quantity'] += trade.quantity
            
            # Time series data for charts
            daily_data = {}
            for trade in trades:
                date_str = trade.activity_date.isoformat()
                if date_str not in daily_data:
                    daily_data[date_str] = {
                        'date': date_str,
                        'trades': 0,
                        'volume': 0,
                        'buy_volume': 0,
                        'sell_volume': 0
                    }
                daily_data[date_str]['trades'] += 1
                daily_data[date_str]['volume'] += trade.total_amount
                if trade.side == 'buy':
                    daily_data[date_str]['buy_volume'] += trade.total_amount
                else:
                    daily_data[date_str]['sell_volume'] += trade.total_amount
            
            return {
                'success': True,
                'symbol': symbol.upper(),
                'total_trades': len(trades),
                'date_range': {
                    'start': trades[0].activity_date.isoformat(),
                    'end': trades[-1].activity_date.isoformat()
                },
                'quantity_metrics': {
                    'total_bought': total_quantity_bought,
                    'total_sold': total_quantity_sold,
                    'net_position': total_quantity_bought - total_quantity_sold
                },
                'price_metrics': {
                    'avg_buy_price': round(avg_buy_price, 2),
                    'avg_sell_price': round(avg_sell_price, 2),
                    'price_improvement': round(avg_sell_price - avg_buy_price, 2) if avg_buy_price > 0 and avg_sell_price > 0 else 0
                },
                'pnl_metrics': {
                    'total_buy_amount': round(total_buy_amount, 2),
                    'total_sell_amount': round(total_sell_amount, 2),
                    'realized_pnl': round(realized_pnl, 2),
                    'pnl_percentage': round((realized_pnl / total_buy_amount * 100), 2) if total_buy_amount > 0 else 0
                },
                'trans_code_breakdown': trans_code_stats,
                'daily_data': list(daily_data.values()),
                'accounts_involved': list(set([t.account.name for t in trades]))
            }
            
        except Exception as e:
            logger.error(f"Error in instrument analytics: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    def get_pnl_over_time(self, account_ids: Optional[List[int]] = None, 
                         start_date: Optional[date] = None, 
                         end_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Get P&L analysis over time
        
        Args:
            account_ids: Optional list of account IDs to include
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            Dictionary with P&L over time data
        """
        try:
            # Default date range
            if not end_date:
                end_date = date.today()
            if not start_date:
                start_date = end_date - timedelta(days=365)  # Last year
            
            # Base query for trades
            query = db.session.query(Trade).join(Account)
            if account_ids:
                query = query.filter(Account.id.in_(account_ids))
            
            query = query.filter(
                Trade.activity_date >= start_date,
                Trade.activity_date <= end_date,
                Account.is_active == True
            ).order_by(Trade.activity_date)
            
            trades = query.all()
            
            # Calculate daily P&L
            daily_pnl = {}
            cumulative_pnl = 0
            
            for trade in trades:
                date_str = trade.activity_date.isoformat()
                
                if date_str not in daily_pnl:
                    daily_pnl[date_str] = {
                        'date': date_str,
                        'trades': 0,
                        'buy_amount': 0,
                        'sell_amount': 0,
                        'daily_pnl': 0,
                        'cumulative_pnl': 0
                    }
                
                daily_pnl[date_str]['trades'] += 1
                
                if trade.side == 'buy':
                    daily_pnl[date_str]['buy_amount'] += trade.total_amount
                    daily_pnl[date_str]['daily_pnl'] -= trade.total_amount  # Cost
                else:
                    daily_pnl[date_str]['sell_amount'] += trade.total_amount
                    daily_pnl[date_str]['daily_pnl'] += trade.total_amount  # Revenue
            
            # Calculate cumulative P&L
            for date_str in sorted(daily_pnl.keys()):
                cumulative_pnl += daily_pnl[date_str]['daily_pnl']
                daily_pnl[date_str]['cumulative_pnl'] = cumulative_pnl
            
            # Monthly aggregation
            monthly_pnl = {}
            for date_str, data in daily_pnl.items():
                month_key = date_str[:7]  # YYYY-MM
                if month_key not in monthly_pnl:
                    monthly_pnl[month_key] = {
                        'month': month_key,
                        'trades': 0,
                        'monthly_pnl': 0,
                        'buy_amount': 0,
                        'sell_amount': 0
                    }
                monthly_pnl[month_key]['trades'] += data['trades']
                monthly_pnl[month_key]['monthly_pnl'] += data['daily_pnl']
                monthly_pnl[month_key]['buy_amount'] += data['buy_amount']
                monthly_pnl[month_key]['sell_amount'] += data['sell_amount']
            
            return {
                'success': True,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'summary': {
                    'total_trades': len(trades),
                    'total_pnl': round(cumulative_pnl, 2),
                    'average_daily_pnl': round(cumulative_pnl / len(daily_pnl), 2) if daily_pnl else 0,
                    'best_day': max(daily_pnl.values(), key=lambda x: x['daily_pnl'])['date'] if daily_pnl else None,
                    'worst_day': min(daily_pnl.values(), key=lambda x: x['daily_pnl'])['date'] if daily_pnl else None
                },
                'daily_data': list(daily_pnl.values()),
                'monthly_data': list(monthly_pnl.values())
            }
            
        except Exception as e:
            logger.error(f"Error in P&L over time analysis: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    def rebuild_positions_from_trades(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Rebuild position holdings from trade data for instruments that are not fully sold
        
        Args:
            account_id: Optional account ID to rebuild positions for
            
        Returns:
            Dictionary with rebuild results
        """
        try:
            logger.info(f"Starting position rebuild for account_id: {account_id}")
            
            # Query trades
            query = db.session.query(Trade).join(Account)
            if account_id:
                query = query.filter(Account.id == account_id)
            
            trades = query.filter(Account.is_active == True).order_by(Trade.activity_date, Trade.executed_at).all()
            
            if not trades:
                return {'success': False, 'message': 'No trades found'}
            
            # Clear existing positions for the account(s)
            if account_id:
                Position.query.filter_by(account_id=account_id).delete()
            else:
                # Clear all positions for active accounts
                Position.query.join(Account).filter(Account.is_active == True).delete()
            
            # Group trades by account and instrument
            positions_data = {}
            
            for trade in trades:
                # Create unique key for position
                key_parts = [
                    str(trade.account_id),
                    trade.symbol,
                    trade.instrument_type
                ]
                
                # For options, include strike and expiration in key
                if trade.instrument_type == 'option':
                    key_parts.extend([
                        str(trade.strike_price or 0),
                        str(trade.expiration_date) if trade.expiration_date else 'no_exp',
                        trade.option_type or 'unknown'
                    ])
                
                position_key = '|'.join(key_parts)
                
                if position_key not in positions_data:
                    positions_data[position_key] = {
                        'account_id': trade.account_id,
                        'symbol': trade.symbol,
                        'instrument_type': trade.instrument_type,
                        'option_type': trade.option_type,
                        'strike_price': trade.strike_price,
                        'expiration_date': trade.expiration_date,
                        'quantity': 0.0,
                        'total_cost': 0.0,
                        'trades': []
                    }
                
                position = positions_data[position_key]
                position['trades'].append(trade)
                
                # Calculate position based on transaction codes and sides
                quantity_change = self._calculate_quantity_change(trade)
                cost_change = self._calculate_cost_change(trade, quantity_change)
                
                position['quantity'] += quantity_change
                position['total_cost'] += cost_change
            
            # Create Position records for non-zero positions
            created_positions = 0
            skipped_positions = 0
            
            for position_key, pos_data in positions_data.items():
                # Skip positions with zero or negative quantity
                if pos_data['quantity'] <= 0:
                    skipped_positions += 1
                    continue
                
                # Calculate average buy price
                avg_buy_price = pos_data['total_cost'] / pos_data['quantity'] if pos_data['quantity'] > 0 else 0
                
                # Create Position record
                position = Position(
                    account_id=pos_data['account_id'],
                    symbol=pos_data['symbol'],
                    instrument_type=pos_data['instrument_type'],
                    quantity=pos_data['quantity'],
                    average_buy_price=avg_buy_price,
                    option_type=pos_data['option_type'],
                    strike_price=pos_data['strike_price'],
                    expiration_date=pos_data['expiration_date']
                )
                
                db.session.add(position)
                created_positions += 1
            
            # Commit changes
            db.session.commit()
            
            logger.info(f"Position rebuild complete. Created: {created_positions}, Skipped: {skipped_positions}")
            
            return {
                'success': True,
                'created_positions': created_positions,
                'skipped_positions': skipped_positions,
                'total_trades_processed': len(trades),
                'message': f'Successfully rebuilt {created_positions} positions from {len(trades)} trades'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error rebuilding positions: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    def _calculate_quantity_change(self, trade: Trade) -> float:
        """
        Calculate the quantity change for a position based on trade
        
        Args:
            trade: Trade object
            
        Returns:
            Quantity change (positive for buys, negative for sells)
        """
        # Map transaction codes to quantity changes
        # This handles both Robinhood and Fidelity transaction codes
        
        buy_codes = {
            'BTO',    # Buy to Open (Options)
            'BTC',    # Buy to Close (Options) 
            'Buy',    # Generic Buy
            'PURCHASE',  # Fidelity Purchase
            'REINVESTMENT',  # Dividend Reinvestment
        }
        
        sell_codes = {
            'STO',    # Sell to Open (Options)
            'STC',    # Sell to Close (Options)
            'Sell',   # Generic Sell
            'SALE',   # Fidelity Sale
        }
        
        # Handle specific transaction codes
        trans_code = trade.trans_code.upper()
        
        if trans_code in buy_codes or trade.side == 'buy':
            return abs(trade.quantity)
        elif trans_code in sell_codes or trade.side == 'sell':
            return -abs(trade.quantity)
        elif trans_code in ['DIVIDEND', 'INTEREST', 'FEE']:
            # Non-position affecting trades
            return 0.0
        else:
            # Default to side-based logic
            return abs(trade.quantity) if trade.side == 'buy' else -abs(trade.quantity)
    
    def _calculate_cost_change(self, trade: Trade, quantity_change: float) -> float:
        """
        Calculate the cost basis change for a position
        
        Args:
            trade: Trade object
            quantity_change: Calculated quantity change
            
        Returns:
            Cost basis change
        """
        # Only add to cost basis for buys (positive quantity changes)
        if quantity_change > 0:
            return abs(trade.total_amount)
        elif quantity_change < 0:
            # For sells, we could implement FIFO/LIFO here, but for simplicity
            # we'll just return 0 (cost basis reduction would need more complex logic)
            return 0.0
        else:
            return 0.0
    
    def get_trans_code_analytics(self, account_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Get analytics by transaction code
        
        Args:
            account_ids: Optional list of account IDs to include
            
        Returns:
            Dictionary with transaction code analytics
        """
        try:
            # Base query for trades
            query = db.session.query(Trade).join(Account)
            if account_ids:
                query = query.filter(Account.id.in_(account_ids))
            
            trades = query.filter(Account.is_active == True).all()
            
            # Group by transaction code
            trans_code_stats = {}
            for trade in trades:
                code = trade.trans_code
                if code not in trans_code_stats:
                    trans_code_stats[code] = {
                        'trans_code': code,
                        'count': 0,
                        'total_amount': 0,
                        'total_quantity': 0,
                        'avg_price': 0,
                        'symbols': set(),
                        'accounts': set(),
                        'date_range': {'start': None, 'end': None}
                    }
                
                stats = trans_code_stats[code]
                stats['count'] += 1
                stats['total_amount'] += trade.total_amount
                stats['total_quantity'] += trade.quantity
                stats['symbols'].add(trade.symbol)
                stats['accounts'].add(trade.account.name)
                
                # Update date range
                if not stats['date_range']['start'] or trade.activity_date < stats['date_range']['start']:
                    stats['date_range']['start'] = trade.activity_date
                if not stats['date_range']['end'] or trade.activity_date > stats['date_range']['end']:
                    stats['date_range']['end'] = trade.activity_date
            
            # Finalize calculations
            for code in trans_code_stats:
                stats = trans_code_stats[code]
                stats['avg_price'] = stats['total_amount'] / stats['total_quantity'] if stats['total_quantity'] > 0 else 0
                stats['unique_symbols'] = len(stats['symbols'])
                stats['unique_accounts'] = len(stats['accounts'])
                stats['symbols'] = list(stats['symbols'])
                stats['accounts'] = list(stats['accounts'])
                
                # Convert dates to strings
                if stats['date_range']['start']:
                    stats['date_range']['start'] = stats['date_range']['start'].isoformat()
                if stats['date_range']['end']:
                    stats['date_range']['end'] = stats['date_range']['end'].isoformat()
            
            # Sort by total amount
            sorted_stats = sorted(trans_code_stats.values(), key=lambda x: x['total_amount'], reverse=True)
            
            return {
                'success': True,
                'trans_code_breakdown': sorted_stats,
                'summary': {
                    'total_trans_codes': len(trans_code_stats),
                    'total_trades': len(trades),
                    'most_active_code': sorted_stats[0]['trans_code'] if sorted_stats else None,
                    'highest_volume_code': sorted_stats[0]['trans_code'] if sorted_stats else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error in transaction code analytics: {str(e)}")
            return {'success': False, 'message': str(e)}