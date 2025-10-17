"""
Database models for Mantri Trade Book application
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from sqlalchemy import Index, UniqueConstraint
from cryptography.fernet import Fernet
import json
import os

# This will be initialized from the main app
db = SQLAlchemy()

class Account(db.Model):
    """Robinhood account model"""
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    encrypted_credentials = db.Column(db.Text)  # Encrypted JSON with credentials
    robinhood_account_id = db.Column(db.String(100), unique=True)
    
    # Status and metadata
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sync = db.Column(db.DateTime)
    
    # Account details from Robinhood
    account_number = db.Column(db.String(50))
    buying_power = db.Column(db.Float)
    total_portfolio_value = db.Column(db.Float)
    day_trade_buying_power = db.Column(db.Float)
    max_ach_early_access_amount = db.Column(db.Float)
    
    # Relationships
    positions = db.relationship('Position', backref='account', lazy='dynamic', cascade='all, delete-orphan')
    trades = db.relationship('Trade', backref='account', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Account {self.name} ({self.username})>'
    
    def encrypt_credentials(self, credentials_dict):
        """Encrypt and store credentials"""
        try:
            # Use a consistent key derived from environment or a default
            key_material = os.environ.get('ENCRYPTION_KEY', 'mantri-trade-book-default-key-32-chars!')
            # Ensure key is exactly 32 bytes and base64 url-safe encoded
            key_bytes = key_material.encode()[:32].ljust(32, b'0')
            import base64
            key = base64.urlsafe_b64encode(key_bytes)
            f = Fernet(key)
            encrypted_data = f.encrypt(json.dumps(credentials_dict).encode())
            self.encrypted_credentials = base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            # Fallback to simple encoding (not secure, for development only)
            import base64
            self.encrypted_credentials = base64.b64encode(json.dumps(credentials_dict).encode()).decode()
    
    def decrypt_credentials(self):
        """Decrypt and return credentials"""
        if not self.encrypted_credentials:
            return {}
        try:
            # Try Fernet decryption first
            key_material = os.environ.get('ENCRYPTION_KEY', 'mantri-trade-book-default-key-32-chars!')
            key_bytes = key_material.encode()[:32].ljust(32, b'0')
            import base64
            key = base64.urlsafe_b64encode(key_bytes)
            f = Fernet(key)
            encrypted_data = base64.urlsafe_b64decode(self.encrypted_credentials.encode())
            decrypted_data = f.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except:
            try:
                # Fallback to simple base64 decoding
                import base64
                decrypted_data = base64.b64decode(self.encrypted_credentials.encode())
                return json.loads(decrypted_data.decode())
            except:
                return {}
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'username': self.username,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'buying_power': self.buying_power,
            'total_portfolio_value': self.total_portfolio_value,
            'positions_count': self.positions.count(),
            'trades_count': self.trades.count()
        }


class Position(db.Model):
    """Stock/Options position model"""
    __tablename__ = 'positions'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    
    # Position identifiers
    symbol = db.Column(db.String(20), nullable=False, index=True)
    instrument_type = db.Column(db.String(20), nullable=False)  # 'stock' or 'option'
    robinhood_position_id = db.Column(db.String(100), unique=True)
    
    # Position data
    quantity = db.Column(db.Float, nullable=False)
    average_buy_price = db.Column(db.Float)
    current_price = db.Column(db.Float)
    current_value = db.Column(db.Float)
    day_change = db.Column(db.Float)
    day_change_percent = db.Column(db.Float)
    total_return = db.Column(db.Float)
    total_return_percent = db.Column(db.Float)
    
    # Options specific fields
    option_type = db.Column(db.String(10))  # 'call' or 'put'
    strike_price = db.Column(db.Float)
    expiration_date = db.Column(db.Date)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_updated_price = db.Column(db.DateTime)
    
    # Constraints and indexes
    __table_args__ = (
        Index('idx_account_symbol', 'account_id', 'symbol'),
        Index('idx_symbol_type', 'symbol', 'instrument_type'),
        UniqueConstraint('account_id', 'symbol', 'instrument_type', 'strike_price', 'expiration_date', 
                        name='uq_position_identifier'),
    )
    
    def __repr__(self):
        return f'<Position {self.symbol} ({self.instrument_type}) - {self.quantity} shares>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'account_id': self.account_id,
            'account_name': self.account.name,
            'symbol': self.symbol,
            'instrument_type': self.instrument_type,
            'quantity': self.quantity,
            'average_buy_price': self.average_buy_price,
            'current_price': self.current_price,
            'current_value': self.current_value,
            'day_change': self.day_change,
            'day_change_percent': self.day_change_percent,
            'total_return': self.total_return,
            'total_return_percent': self.total_return_percent,
            'option_type': self.option_type,
            'strike_price': self.strike_price,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'updated_at': self.updated_at.isoformat()
        }


class Trade(db.Model):
    """Trading history model"""
    __tablename__ = 'trades'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    
    # Trade identifiers
    symbol = db.Column(db.String(20), nullable=False, index=True)
    instrument_type = db.Column(db.String(20), nullable=False)  # 'stock' or 'option'
    robinhood_trade_id = db.Column(db.String(100), unique=True)
    
    # Trade details
    side = db.Column(db.String(10), nullable=False)  # 'buy' or 'sell'
    quantity = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    fees = db.Column(db.Float, default=0)
    
    # Options specific
    option_type = db.Column(db.String(10))  # 'call' or 'put'
    strike_price = db.Column(db.Float)
    expiration_date = db.Column(db.Date)
    
    # Timing
    executed_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Trade state
    state = db.Column(db.String(20), default='filled')  # filled, cancelled, rejected, etc.
    
    # Indexes
    __table_args__ = (
        Index('idx_account_symbol_date', 'account_id', 'symbol', 'executed_at'),
        Index('idx_executed_at_desc', 'executed_at', postgresql_ops={'executed_at': 'DESC'}),
    )
    
    def __repr__(self):
        return f'<Trade {self.side} {self.quantity} {self.symbol} @ {self.price}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'account_id': self.account_id,
            'account_name': self.account.name,
            'symbol': self.symbol,
            'instrument_type': self.instrument_type,
            'side': self.side,
            'quantity': self.quantity,
            'price': self.price,
            'total_amount': self.total_amount,
            'fees': self.fees,
            'option_type': self.option_type,
            'strike_price': self.strike_price,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'executed_at': self.executed_at.isoformat(),
            'state': self.state
        }


class StockData(db.Model):
    """Historical stock price data"""
    __tablename__ = 'stock_data'
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    
    # OHLCV data
    open_price = db.Column(db.Float)
    high_price = db.Column(db.Float)
    low_price = db.Column(db.Float)
    close_price = db.Column(db.Float, nullable=False)
    volume = db.Column(db.BigInteger)
    
    # Additional metrics
    market_cap = db.Column(db.BigInteger)
    pe_ratio = db.Column(db.Float)
    dividend_yield = db.Column(db.Float)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('symbol', 'date', name='uq_stock_data_symbol_date'),
        Index('idx_symbol_date_desc', 'symbol', 'date', postgresql_ops={'date': 'DESC'}),
    )
    
    def __repr__(self):
        return f'<StockData {self.symbol} {self.date} ${self.close_price}>'


class OptionData(db.Model):
    """Historical options data"""
    __tablename__ = 'option_data'
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False, index=True)
    option_type = db.Column(db.String(10), nullable=False)  # 'call' or 'put'
    strike_price = db.Column(db.Float, nullable=False)
    expiration_date = db.Column(db.Date, nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    
    # Options pricing data
    bid_price = db.Column(db.Float)
    ask_price = db.Column(db.Float)
    last_price = db.Column(db.Float)
    volume = db.Column(db.Integer)
    open_interest = db.Column(db.Integer)
    
    # Greeks
    delta = db.Column(db.Float)
    gamma = db.Column(db.Float)
    theta = db.Column(db.Float)
    vega = db.Column(db.Float)
    rho = db.Column(db.Float)
    implied_volatility = db.Column(db.Float)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('symbol', 'option_type', 'strike_price', 'expiration_date', 'date',
                        name='uq_option_data_identifier'),
        Index('idx_symbol_exp_date', 'symbol', 'expiration_date', 'date'),
    )
    
    def __repr__(self):
        return f'<OptionData {self.symbol} {self.option_type} ${self.strike_price} exp:{self.expiration_date}>'


class TradingSession(db.Model):
    """Trading session tracking for analytics"""
    __tablename__ = 'trading_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    
    session_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    
    # Session metrics
    total_trades = db.Column(db.Integer, default=0)
    total_volume = db.Column(db.Float, default=0)
    realized_pnl = db.Column(db.Float, default=0)
    fees_paid = db.Column(db.Float, default=0)
    
    # Session notes
    notes = db.Column(db.Text)
    tags = db.Column(db.String(200))  # Comma-separated tags
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('account_id', 'session_date', name='uq_trading_session'),
        Index('idx_account_date', 'account_id', 'session_date'),
    )
    
    def __repr__(self):
        return f'<TradingSession {self.session_date} - {self.total_trades} trades>'