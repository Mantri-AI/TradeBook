
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta
import os
import json
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///mantri_trade_book.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
from models.database import db
migrate = Migrate()

# Initialize with app
db.init_app(app)
migrate.init_app(app, db)

# Import models and services after db initialization
from models.database import Account, Position, Trade, StockData, OptionData
from services.robinhood_service import RobinhoodService
from services.data_analyzer import DataAnalyzer

# Routes
@app.route('/')
def index():
    """Dashboard home page"""
    return render_template('dashboard.html', data={})

@app.route('/dashboard')
def dashboard():
    """Main dashboard with portfolio overview"""
    accounts = Account.query.filter_by(is_active=True).all()
    
    # Get aggregated data
    total_positions = Position.query.join(Account).filter(Account.is_active==True).count()
    total_accounts = len(accounts)
    
    # Calculate total portfolio value
    total_portfolio_value = 0
    total_day_change = 0
    
    for account in accounts:
        account_value = sum([pos.current_value for pos in account.positions if pos.current_value])
        total_portfolio_value += account_value
        
        account_day_change = sum([pos.day_change for pos in account.positions if pos.day_change])
        total_day_change += account_day_change
    
    dashboard_data = {
        'total_accounts': total_accounts,
        'total_positions': total_positions,
        'total_portfolio_value': total_portfolio_value,
        'total_day_change': total_day_change,
        'day_change_percent': (total_day_change / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
    }
    
    return render_template('dashboard.html', data=dashboard_data, accounts=accounts)

@app.route('/accounts')
def accounts():
    """Account management page"""
    accounts = Account.query.all()
    return render_template('accounts.html', accounts=accounts)

@app.route('/positions')
def positions():
    """View all positions"""
    account_id = request.args.get('account_id')
    position_type = request.args.get('type', 'all')  # all, stocks, options
    
    query = Position.query.join(Account)
    
    if account_id:
        query = query.filter(Account.id == account_id)
    
    if position_type == 'stocks':
        query = query.filter(Position.instrument_type == 'stock')
    elif position_type == 'options':
        query = query.filter(Position.instrument_type == 'option')
    
    positions = query.filter(Account.is_active == True).all()
    accounts = Account.query.filter_by(is_active=True).all()
    
    return render_template('positions.html', positions=positions, accounts=accounts, 
                         selected_account=account_id, selected_type=position_type)

@app.route('/trades')
def trades():
    """View trading history"""
    account_id = request.args.get('account_id')
    days = request.args.get('days', 30, type=int)
    search = request.args.get('search', '')
    
    query = Trade.query.join(Account)
    
    if account_id:
        query = query.filter(Account.id == account_id)
    
    # Filter by date range
    start_date = datetime.now() - timedelta(days=days)
    query = query.filter(Trade.executed_at >= start_date)
    
    # Search functionality
    if search:
        query = query.filter(Trade.symbol.ilike(f'%{search}%'))
    
    trades = query.filter(Account.is_active == True).order_by(Trade.executed_at.desc()).all()
    accounts = Account.query.filter_by(is_active=True).all()
    
    return render_template('trades.html', trades=trades, accounts=accounts,
                         selected_account=account_id, days=days, search=search)

@app.route('/analytics')
def analytics():
    """Advanced analytics and visualizations"""
    return render_template('analytics.html')

# API Endpoints
@app.route('/api/test-connection', methods=['POST'])
def api_test_connection():
    """Test Robinhood connection with provided credentials"""
    data = request.get_json()
    import ipdb; ipdb.set_trace()
    
    username = data.get('username')
    password = data.get('password')
    mfa_code = data.get('mfa_code')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password are required'}), 400
    
    try:
        rh_service = RobinhoodService()
        auth_result = rh_service.authenticate(username, password, mfa_code)
        
        if auth_result['success']:
            # Optionally get basic account info to verify connection
            try:
                account_info = rh_service.get_account_info()
                return jsonify({
                    'success': True, 
                    'message': 'Connection successful',
                    'account_info': {
                        'account_number': account_info.get('account_number', 'N/A'),
                        'buying_power': account_info.get('buying_power', 0)
                    }
                })
            except Exception as e:
                # Even if account info fails, authentication was successful
                return jsonify({'success': True, 'message': 'Connection successful'})
        else:
            return jsonify({'success': False, 'message': auth_result['message']})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Connection failed: {str(e)}'}), 500

@app.route('/api/accounts', methods=['GET', 'POST'])
def api_accounts():
    """API for account management"""
    if request.method == 'POST':
        data = request.get_json()
        import ipdb; ipdb.set_trace()
        # Validate required fields
        name = data.get('name')
        username = data.get('username')
        password = data.get('password')
        mfa_code = data.get('mfa_code', '')
        
        if not name or not username or not password:
            return jsonify({'success': False, 'message': 'Name, username, and password are required'}), 400
        
        # Check if username already exists
        existing_account = Account.query.filter_by(username=username).first()
        if existing_account:
            return jsonify({'success': False, 'message': 'An account with this username already exists'}), 400
        
        # Create new account
        account = Account(
            name=name,
            username=username,
            is_active=True
        )
        
        # Encrypt and store credentials
        credentials = {
            'username': username,
            'password': password,
            'mfa_code': mfa_code
        }
        account.encrypt_credentials(credentials)
        
        try:
            db.session.add(account)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Account added successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400
    
    # GET request
    accounts = Account.query.all()
    return jsonify([{
        'id': acc.id,
        'name': acc.name,
        'username': acc.username,
        'is_active': acc.is_active,
        'created_at': acc.created_at.isoformat(),
        'last_sync': acc.last_sync.isoformat() if acc.last_sync else None
    } for acc in accounts])

@app.route('/api/accounts/<int:account_id>', methods=['GET', 'PUT', 'DELETE'])
def api_account_detail(account_id):
    """API for specific account operations"""
    account = Account.query.get_or_404(account_id)
    
    if request.method == 'GET':
        return jsonify({
            'id': account.id,
            'name': account.name,
            'username': account.username,
            'is_active': account.is_active,
            'created_at': account.created_at.isoformat(),
            'last_sync': account.last_sync.isoformat() if account.last_sync else None,
            'buying_power': account.buying_power,
            'total_portfolio_value': account.total_portfolio_value
        })
    
    elif request.method == 'PUT':
        data = request.get_json()
        account.name = data.get('name', account.name)
        account.is_active = data.get('is_active', account.is_active)
        
        try:
            db.session.commit()
            return jsonify({'success': True, 'message': 'Account updated successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400
    
    elif request.method == 'DELETE':
        try:
            db.session.delete(account)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Account deleted successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/accounts/<int:account_id>/details')
def api_account_details(account_id):
    """Get detailed account information"""
    account = Account.query.get_or_404(account_id)
    
    # Get recent positions and trades
    recent_positions = Position.query.filter_by(account_id=account_id).limit(5).all()
    recent_trades = Trade.query.filter_by(account_id=account_id).order_by(Trade.executed_at.desc()).limit(5).all()
    
    return jsonify({
        'account': account.to_dict(),
        'recent_positions': [pos.to_dict() for pos in recent_positions],
        'recent_trades': [trade.to_dict() for trade in recent_trades],
        'summary': {
            'total_positions': Position.query.filter_by(account_id=account_id).count(),
            'total_trades': Trade.query.filter_by(account_id=account_id).count(),
            'portfolio_value': account.total_portfolio_value or 0,
            'buying_power': account.buying_power or 0
        }
    })

@app.route('/api/sync-all', methods=['POST'])
def api_sync_all():
    """Sync all active accounts"""
    accounts = Account.query.filter_by(is_active=True).all()
    
    if not accounts:
        return jsonify({'success': False, 'message': 'No active accounts found'})
    
    success_count = 0
    error_messages = []
    
    for account in accounts:
        try:
            rh_service = RobinhoodService()
            if rh_service.sync_account_data(account):
                success_count += 1
            else:
                error_messages.append(f"Failed to sync {account.name}")
        except Exception as e:
            error_messages.append(f"Error syncing {account.name}: {str(e)}")
    
    if success_count == len(accounts):
        return jsonify({'success': True, 'message': f'Successfully synced {success_count} accounts'})
    elif success_count > 0:
        return jsonify({
            'success': True, 
            'message': f'Synced {success_count}/{len(accounts)} accounts',
            'warnings': error_messages
        })
    else:
        return jsonify({
            'success': False, 
            'message': 'Failed to sync any accounts',
            'errors': error_messages
        }), 400

@app.route('/api/sync/<int:account_id>', methods=['POST'])
def api_sync_account(account_id):
    """Sync account data with Robinhood"""
    account = Account.query.get_or_404(account_id)
    
    try:
        rh_service = RobinhoodService()
        success = rh_service.sync_account_data(account)
        
        if success:
            account.last_sync = datetime.now()
            db.session.commit()
            return jsonify({'success': True, 'message': 'Account synced successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to sync account'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/portfolio/summary')
def api_portfolio_summary():
    """Get portfolio summary data for charts"""
    account_id = request.args.get('account_id')
    
    query = Position.query.join(Account)
    if account_id:
        query = query.filter(Account.id == account_id)
    
    positions = query.filter(Account.is_active == True).all()
    
    # Aggregate data
    portfolio_data = {}
    total_value = 0
    
    for position in positions:
        symbol = position.symbol
        if symbol not in portfolio_data:
            portfolio_data[symbol] = {
                'symbol': symbol,
                'total_value': 0,
                'total_quantity': 0,
                'positions': []
            }
        
        portfolio_data[symbol]['total_value'] += position.current_value or 0
        portfolio_data[symbol]['total_quantity'] += position.quantity or 0
        portfolio_data[symbol]['positions'].append({
            'account_name': position.account.name,
            'quantity': position.quantity,
            'current_value': position.current_value,
            'day_change': position.day_change,
            'type': position.instrument_type
        })
        
        total_value += position.current_value or 0
    
    return jsonify({
        'portfolio_data': list(portfolio_data.values()),
        'total_value': total_value
    })

@app.route('/api/trades/summary')
def api_trades_summary():
    """Get trading summary data"""
    days = request.args.get('days', 30, type=int)
    account_id = request.args.get('account_id')
    
    start_date = datetime.now() - timedelta(days=days)
    
    query = Trade.query.join(Account).filter(Trade.executed_at >= start_date)
    if account_id:
        query = query.filter(Account.id == account_id)
    
    trades = query.filter(Account.is_active == True).all()
    
    # Calculate summary stats
    total_trades = len(trades)
    total_volume = sum([trade.quantity * trade.price for trade in trades if trade.quantity and trade.price])
    
    buy_trades = [t for t in trades if t.side == 'buy']
    sell_trades = [t for t in trades if t.side == 'sell']
    
    return jsonify({
        'total_trades': total_trades,
        'total_volume': total_volume,
        'buy_trades': len(buy_trades),
        'sell_trades': len(sell_trades),
        'trades_by_day': _get_trades_by_day(trades),
        'trades_by_symbol': _get_trades_by_symbol(trades)
    })

@app.route('/api/trades/recent')
def api_trades_recent():
    """Get recent trades"""
    limit = request.args.get('limit', 10, type=int)
    account_id = request.args.get('account_id')
    
    query = Trade.query.join(Account)
    if account_id:
        query = query.filter(Account.id == account_id)
    
    trades = query.filter(Account.is_active == True).order_by(Trade.executed_at.desc()).limit(limit).all()
    
    return jsonify({
        'trades': [trade.to_dict() for trade in trades]
    })

@app.route('/api/positions/top')
def api_positions_top():
    """Get top positions by value"""
    limit = request.args.get('limit', 10, type=int)
    account_id = request.args.get('account_id')
    
    query = Position.query.join(Account)
    if account_id:
        query = query.filter(Account.id == account_id)
    
    positions = query.filter(Account.is_active == True).order_by(Position.current_value.desc()).limit(limit).all()
    
    return jsonify({
        'positions': [position.to_dict() for position in positions]
    })

def _get_trades_by_day(trades):
    """Helper function to group trades by day"""
    trades_by_day = {}
    for trade in trades:
        day = trade.executed_at.strftime('%Y-%m-%d')
        if day not in trades_by_day:
            trades_by_day[day] = {'count': 0, 'volume': 0}
        trades_by_day[day]['count'] += 1
        trades_by_day[day]['volume'] += trade.quantity * trade.price if trade.quantity and trade.price else 0
    
    return trades_by_day

def _get_trades_by_symbol(trades):
    """Helper function to group trades by symbol"""
    trades_by_symbol = {}
    for trade in trades:
        symbol = trade.symbol
        if symbol not in trades_by_symbol:
            trades_by_symbol[symbol] = {'count': 0, 'volume': 0}
        trades_by_symbol[symbol]['count'] += 1
        trades_by_symbol[symbol]['volume'] += trade.quantity * trade.price if trade.quantity and trade.price else 0
    
    return trades_by_symbol

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5001)