"""
Robinhood API integration service
"""
import robin_stocks.robinhood as rh
import requests
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
import logging
import time
from models.database import db, Account, Position, Trade, StockData, OptionData

logger = logging.getLogger(__name__)

class RobinhoodService:
    """Service for interacting with Robinhood API"""
    
    def __init__(self):
        self.session = requests.Session()
        self.rate_limit_delay = 1  # seconds between API calls
        
    def authenticate(self, username: str, password: str, mfa_code: str = None) -> Dict[str, Any]:
        """
        Authenticate with Robinhood
        
        Args:
            username: Robinhood username
            password: Robinhood password
            mfa_code: MFA code if required
            
        Returns:
            Dict with authentication status and token
        """
        try:
            login_result = rh.login(username, password, mfa_code=mfa_code)
            
            if login_result:
                return {
                    'success': True,
                    'message': 'Authentication successful',
                    'token': login_result.get('access_token')
                }
            else:
                return {
                    'success': False,
                    'message': 'Authentication failed'
                }
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return {
                'success': False,
                'message': f'Authentication error: {str(e)}'
            }
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information from Robinhood"""
        try:
            account_info = rh.profiles.load_account_profile()
            portfolio = rh.profiles.load_portfolio_profile()
            
            return {
                'account_number': account_info.get('account_number'),
                'buying_power': float(portfolio.get('buying_power', 0)),
                'total_portfolio_value': float(portfolio.get('total_return_today', 0)),
                'day_trade_buying_power': float(portfolio.get('day_trade_buying_power', 0)),
                'max_ach_early_access_amount': float(portfolio.get('max_ach_early_access_amount', 0))
            }
        except Exception as e:
            logger.error(f"Error fetching account info: {str(e)}")
            return {}
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get all positions from Robinhood"""
        try:
            positions = []
            
            # Get stock positions
            stock_positions = rh.account.build_holdings()
            for symbol, data in stock_positions.items():
                positions.append({
                    'symbol': symbol,
                    'instrument_type': 'stock',
                    'quantity': float(data.get('quantity', 0)),
                    'average_buy_price': float(data.get('average_buy_price', 0)),
                    'current_price': float(data.get('price', 0)),
                    'current_value': float(data.get('equity', 0)),
                    'day_change': float(data.get('equity_change', 0)),
                    'day_change_percent': float(data.get('percent_change', 0)),
                    'total_return': float(data.get('total_return_today', 0)),
                    'total_return_percent': float(data.get('percentage', 0))
                })
            
            # Get options positions
            options_positions = rh.options.get_open_option_positions()
            for option_data in options_positions:
                instrument = rh.options.get_option_instrument_data_by_id(
                    option_data['option']['instrument']['id']
                )
                
                positions.append({
                    'symbol': instrument['chain_symbol'],
                    'instrument_type': 'option',
                    'quantity': float(option_data.get('quantity', 0)),
                    'average_buy_price': float(option_data.get('average_price', 0)) if option_data.get('average_price') else 0,
                    'current_price': float(option_data.get('market_value', 0)) if option_data.get('market_value') else 0,
                    'current_value': float(option_data.get('market_value', 0)) if option_data.get('market_value') else 0,
                    'option_type': instrument['type'],
                    'strike_price': float(instrument['strike_price']),
                    'expiration_date': datetime.strptime(instrument['expiration_date'], '%Y-%m-%d').date()
                })
            
            return positions
            
        except Exception as e:
            logger.error(f"Error fetching positions: {str(e)}")
            return []
    
    def get_orders(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """Get trading history from Robinhood"""
        try:
            trades = []
            
            # Get stock orders
            stock_orders = rh.orders.get_all_stock_orders()
            for order in stock_orders:
                if order['state'] == 'filled':
                    instrument_data = rh.stocks.get_instrument_by_url(order['instrument'])
                    executed_at = datetime.fromisoformat(order['updated_at'].replace('Z', '+00:00'))
                    
                    # Filter by date
                    if executed_at >= datetime.now() - timedelta(days=days_back):
                        trades.append({
                            'symbol': instrument_data['symbol'],
                            'instrument_type': 'stock',
                            'side': order['side'],
                            'quantity': float(order['quantity']),
                            'price': float(order['price']) if order['price'] else 0,
                            'total_amount': float(order['quantity']) * float(order['price']) if order['price'] else 0,
                            'fees': float(order.get('fees', 0)),
                            'executed_at': executed_at,
                            'state': order['state'],
                            'robinhood_trade_id': order['id']
                        })
            
            # Get options orders
            options_orders = rh.options.get_all_option_orders()
            for order in options_orders:
                if order['state'] == 'filled':
                    for leg in order.get('legs', []):
                        instrument_data = rh.options.get_option_instrument_data_by_id(
                            leg['option']['instrument']['id']
                        )
                        executed_at = datetime.fromisoformat(order['updated_at'].replace('Z', '+00:00'))
                        
                        # Filter by date
                        if executed_at >= datetime.now() - timedelta(days=days_back):
                            trades.append({
                                'symbol': instrument_data['chain_symbol'],
                                'instrument_type': 'option',
                                'side': leg['side'],
                                'quantity': float(order['quantity']),
                                'price': float(order['price']) if order['price'] else 0,
                                'total_amount': float(order['quantity']) * float(order['price']) if order['price'] else 0,
                                'fees': float(order.get('fees', 0)),
                                'option_type': instrument_data['type'],
                                'strike_price': float(instrument_data['strike_price']),
                                'expiration_date': datetime.strptime(instrument_data['expiration_date'], '%Y-%m-%d').date(),
                                'executed_at': executed_at,
                                'state': order['state'],
                                'robinhood_trade_id': order['id']
                            })
            
            return sorted(trades, key=lambda x: x['executed_at'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error fetching orders: {str(e)}")
            return []
    
    def sync_account_data(self, account: Account) -> bool:
        """
        Sync all data for a specific account
        
        Args:
            account: Account model instance
            
        Returns:
            Boolean indicating success
        """
        try:
            # Decrypt credentials and authenticate
            credentials = account.decrypt_credentials()
            if not credentials:
                logger.error(f"No credentials found for account {account.id}")
                return False
            
            # Authenticate
            auth_result = self.authenticate(
                credentials.get('username'),
                credentials.get('password'),
                credentials.get('mfa_code')
            )
            
            if not auth_result['success']:
                logger.error(f"Authentication failed for account {account.id}")
                return False
            
            # Update account information
            account_info = self.get_account_info()
            if account_info:
                account.account_number = account_info.get('account_number')
                account.buying_power = account_info.get('buying_power')
                account.total_portfolio_value = account_info.get('total_portfolio_value')
                account.day_trade_buying_power = account_info.get('day_trade_buying_power')
                account.max_ach_early_access_amount = account_info.get('max_ach_early_access_amount')
            
            # Sync positions
            self._sync_positions(account)
            
            # Sync trades
            self._sync_trades(account)
            
            # Update last sync time
            account.last_sync = datetime.utcnow()
            db.session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error syncing account {account.id}: {str(e)}")
            db.session.rollback()
            return False
        finally:
            rh.logout()
    
    def _sync_positions(self, account: Account):
        """Sync positions for an account"""
        positions_data = self.get_positions()
        
        # Clear existing positions
        Position.query.filter_by(account_id=account.id).delete()
        
        # Add new positions
        for pos_data in positions_data:
            position = Position(
                account_id=account.id,
                symbol=pos_data['symbol'],
                instrument_type=pos_data['instrument_type'],
                quantity=pos_data['quantity'],
                average_buy_price=pos_data.get('average_buy_price'),
                current_price=pos_data.get('current_price'),
                current_value=pos_data.get('current_value'),
                day_change=pos_data.get('day_change'),
                day_change_percent=pos_data.get('day_change_percent'),
                total_return=pos_data.get('total_return'),
                total_return_percent=pos_data.get('total_return_percent'),
                option_type=pos_data.get('option_type'),
                strike_price=pos_data.get('strike_price'),
                expiration_date=pos_data.get('expiration_date'),
                last_updated_price=datetime.utcnow()
            )
            db.session.add(position)
    
    def _sync_trades(self, account: Account, days_back: int = 30):
        """Sync trades for an account"""
        trades_data = self.get_orders(days_back)
        
        for trade_data in trades_data:
            # Check if trade already exists
            existing_trade = Trade.query.filter_by(
                account_id=account.id,
                robinhood_trade_id=trade_data.get('robinhood_trade_id')
            ).first()
            
            if not existing_trade:
                trade = Trade(
                    account_id=account.id,
                    symbol=trade_data['symbol'],
                    instrument_type=trade_data['instrument_type'],
                    side=trade_data['side'],
                    quantity=trade_data['quantity'],
                    price=trade_data['price'],
                    total_amount=trade_data['total_amount'],
                    fees=trade_data.get('fees', 0),
                    option_type=trade_data.get('option_type'),
                    strike_price=trade_data.get('strike_price'),
                    expiration_date=trade_data.get('expiration_date'),
                    executed_at=trade_data['executed_at'],
                    state=trade_data['state'],
                    robinhood_trade_id=trade_data.get('robinhood_trade_id')
                )
                db.session.add(trade)
    
    def get_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """Get current stock quote"""
        try:
            quote = rh.stocks.get_latest_price(symbol)[0]
            return {
                'symbol': symbol,
                'price': float(quote),
                'timestamp': datetime.utcnow()
            }
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {str(e)}")
            return {}
    
    def get_historical_data(self, symbol: str, span: str = '1month', interval: str = 'day') -> List[Dict[str, Any]]:
        """Get historical stock data"""
        try:
            historical_data = rh.stocks.get_stock_historicals(symbol, interval=interval, span=span)
            return [
                {
                    'symbol': symbol,
                    'date': datetime.fromisoformat(item['begins_at'].replace('Z', '+00:00')).date(),
                    'open_price': float(item['open_price']),
                    'high_price': float(item['high_price']),
                    'low_price': float(item['low_price']),
                    'close_price': float(item['close_price']),
                    'volume': int(item['volume'])
                }
                for item in historical_data
            ]
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return []