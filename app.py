
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import json
import logging
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///mantri_trade_book.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
from models.database import db

# Initialize with app
db.init_app(app)

# Import models and services after db initialization
from models.database import Account, Position, Trade, StockData, OptionData
from services.robinhood_service import RobinhoodService
from services.data_analyzer import DataAnalyzer
from services.csv_import_service import CSVImportService

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
        
        # Validate required fields
        name = data.get('name')
        provider = data.get('provider', 'robinhood')
        auth_type = data.get('authentication_type', 'manual')
        username = data.get('username')
        password = data.get('password')
        mfa_code = data.get('mfa_code', '')
        
        if not name or not provider:
            return jsonify({'success': False, 'message': 'Name and provider are required'}), 400
        
        if auth_type == 'api_auth' and (not username or not password):
            return jsonify({'success': False, 'message': 'Username and password are required for API authentication'}), 400
        
        # Check if account name already exists
        existing_account_by_name = Account.query.filter_by(name=name).first()
        if existing_account_by_name:
            return jsonify({'success': False, 'message': f'An account with the name "{name}" already exists'}), 400
        
        # Check if username already exists for this provider (if username provided)
        if username:
            existing_account_by_username = Account.query.filter_by(provider=provider, username=username).first()
            if existing_account_by_username:
                return jsonify({'success': False, 'message': f'An account with this username already exists for {provider}'}), 400
        
        # Create new account
        account = Account(
            name=name,
            provider=provider,
            username=username,
            authentication_type=auth_type,
            is_active=True
        )
        
        # Encrypt and store credentials if provided
        if auth_type == 'api_auth' and username and password:
            credentials = {
                'username': username,
                'password': password,
                'mfa_code': mfa_code
            }
            account.encrypt_credentials(credentials)
        
        try:
            db.session.add(account)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Account added successfully', 'account_id': account.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400
    
    # GET request
    accounts = Account.query.all()
    return jsonify([{
        'id': acc.id,
        'name': acc.name,
        'provider': acc.provider,
        'username': acc.username,
        'authentication_type': acc.authentication_type,
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

@app.route('/api/accounts/import-csv', methods=['POST'])
def api_import_csv():
    """Import CSV transaction data"""
    try:
        if 'csv_file' not in request.files:
            return jsonify({'success': False, 'message': 'No CSV file provided'}), 400
        
        csv_file = request.files['csv_file']
        account_name = request.form.get('account_name')
        provider = request.form.get('provider', 'robinhood')
        
        if not csv_file.filename:
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        if not account_name:
            return jsonify({'success': False, 'message': 'Account name is required'}), 400
        
        # Create account if it doesn't exist
        account = Account.query.filter_by(name=account_name, provider=provider).first()
        if not account:
            account = Account(
                name=account_name,
                provider=provider,
                authentication_type='manual',
                is_active=True
            )
            db.session.add(account)
            db.session.commit()
        
        # Read CSV content
        csv_content = csv_file.read().decode('utf-8')
        
        # Import based on provider
        csv_service = CSVImportService()
        
        if provider == 'robinhood':
            result = csv_service.import_robinhood_csv(csv_content, account)
        elif provider == 'fidelity':
            result = csv_service.import_fidelity_csv(csv_content, account)
        else:
            # For other providers, use generic import (future enhancement)
            return jsonify({'success': False, 'message': f'CSV import for {provider} not yet supported'}), 400
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in CSV import: {str(e)}")
        return jsonify({'success': False, 'message': f'Import error: {str(e)}'}), 500

@app.route('/api/accounts/<int:account_id>/import-csv', methods=['POST'])
def api_import_csv_to_account(account_id):
    """Import CSV data to existing account"""
    try:
        account = Account.query.get_or_404(account_id)
        
        if 'csv_file' not in request.files:
            return jsonify({'success': False, 'message': 'No CSV file provided'}), 400
        
        csv_file = request.files['csv_file']
        
        if not csv_file.filename:
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        # Read CSV content
        csv_content = csv_file.read().decode('utf-8')
        
        # Import based on provider
        csv_service = CSVImportService()
        
        if account.provider == 'robinhood':
            result = csv_service.import_robinhood_csv(csv_content, account)
        elif account.provider == 'fidelity':
            result = csv_service.import_fidelity_csv(csv_content, account)
        else:
            return jsonify({'success': False, 'message': f'CSV import for {account.provider} not yet supported'}), 400
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in CSV import: {str(e)}")
        return jsonify({'success': False, 'message': f'Import error: {str(e)}'}), 500

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

@app.route('/api/trades/<int:trade_id>')
def api_trade_detail(trade_id):
    """Get individual trade details"""
    trade = Trade.query.get_or_404(trade_id)
    
    # Convert trade to dictionary with all details
    trade_dict = trade.to_dict()
    
    # Add account name for convenience
    trade_dict['account_name'] = trade.account.name
    
    return jsonify(trade_dict)

@app.route('/api/trades', methods=['POST'])
def api_create_trade():
    """Create a new trade manually"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['account_id', 'symbol', 'side', 'quantity', 'price', 'activity_date', 'trans_code']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        # Validate account exists
        account = Account.query.get(data['account_id'])
        if not account:
            return jsonify({'success': False, 'message': 'Invalid account ID'}), 400
        
        # Parse dates
        from datetime import datetime
        try:
            activity_date = datetime.strptime(data['activity_date'], '%Y-%m-%d').date()
            executed_at = datetime.strptime(data.get('executed_at', data['activity_date']), '%Y-%m-%d')
            if 'executed_time' in data and data['executed_time']:
                time_part = datetime.strptime(data['executed_time'], '%H:%M').time()
                executed_at = datetime.combine(executed_at.date(), time_part)
        except ValueError as e:
            return jsonify({'success': False, 'message': f'Invalid date format: {str(e)}'}), 400
        
        # Create trade object
        trade = Trade(
            account_id=data['account_id'],
            symbol=data['symbol'].upper(),
            instrument_type=data.get('instrument_type', 'stock'),
            side=data['side'],
            quantity=float(data['quantity']),
            price=float(data['price']),
            total_amount=float(data['quantity']) * float(data['price']),
            activity_date=activity_date,
            executed_at=executed_at,
            trans_code=data['trans_code'],
            description=data.get('description', ''),
            fees=float(data.get('fees', 0)),
            import_source='manual'
        )
        
        # Handle options specific fields
        if data.get('instrument_type') == 'option':
            trade.option_type = data.get('option_type')
            if data.get('strike_price'):
                trade.strike_price = float(data['strike_price'])
            if data.get('expiration_date'):
                trade.expiration_date = datetime.strptime(data['expiration_date'], '%Y-%m-%d').date()
        
        # Handle process and settle dates if provided
        if data.get('process_date'):
            trade.process_date = datetime.strptime(data['process_date'], '%Y-%m-%d').date()
        if data.get('settle_date'):
            trade.settle_date = datetime.strptime(data['settle_date'], '%Y-%m-%d').date()
        
        # Save to database
        db.session.add(trade)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Trade created successfully',
            'trade': trade.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating trade: {str(e)}")
        return jsonify({'success': False, 'message': f'Error creating trade: {str(e)}'}), 500

@app.route('/api/trades/<int:trade_id>', methods=['PUT'])
def api_update_trade(trade_id):
    """Update an existing trade"""
    try:
        trade = Trade.query.get_or_404(trade_id)
        data = request.get_json()
        
        # Update fields if provided
        if 'symbol' in data:
            trade.symbol = data['symbol'].upper()
        if 'side' in data:
            trade.side = data['side']
        if 'quantity' in data:
            trade.quantity = float(data['quantity'])
        if 'price' in data:
            trade.price = float(data['price'])
        if 'trans_code' in data:
            trade.trans_code = data['trans_code']
        if 'description' in data:
            trade.description = data['description']
        if 'fees' in data:
            trade.fees = float(data['fees'])
        if 'instrument_type' in data:
            trade.instrument_type = data['instrument_type']
        
        # Recalculate total amount
        if 'quantity' in data or 'price' in data:
            trade.total_amount = trade.quantity * trade.price
        
        # Handle dates
        if 'activity_date' in data:
            trade.activity_date = datetime.strptime(data['activity_date'], '%Y-%m-%d').date()
        if 'executed_at' in data:
            trade.executed_at = datetime.strptime(data['executed_at'], '%Y-%m-%d')
            if 'executed_time' in data and data['executed_time']:
                time_part = datetime.strptime(data['executed_time'], '%H:%M').time()
                trade.executed_at = datetime.combine(trade.executed_at.date(), time_part)
        
        # Handle options specific fields
        if trade.instrument_type == 'option':
            if 'option_type' in data:
                trade.option_type = data['option_type']
            if 'strike_price' in data:
                trade.strike_price = float(data['strike_price']) if data['strike_price'] else None
            if 'expiration_date' in data:
                trade.expiration_date = datetime.strptime(data['expiration_date'], '%Y-%m-%d').date() if data['expiration_date'] else None
        
        # Save changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Trade updated successfully',
            'trade': trade.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating trade: {str(e)}")
        return jsonify({'success': False, 'message': f'Error updating trade: {str(e)}'}), 500

@app.route('/api/trades/<int:trade_id>', methods=['DELETE'])
def api_delete_trade(trade_id):
    """Delete a trade"""
    try:
        trade = Trade.query.get_or_404(trade_id)
        
        # Only allow deletion of manually created trades for safety
        if trade.import_source not in ['manual', 'csv_import']:
            return jsonify({'success': False, 'message': 'Cannot delete API-synced trades'}), 400
        
        db.session.delete(trade)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Trade deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting trade: {str(e)}")
        return jsonify({'success': False, 'message': f'Error deleting trade: {str(e)}'}), 500

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

# Enhanced Analytics API Endpoints
@app.route('/api/analytics/cross-account')
def api_cross_account_analytics():
    """Get cross-account analytics"""
    account_ids_param = request.args.get('account_ids')
    account_ids = None
    
    if account_ids_param:
        try:
            account_ids = [int(x) for x in account_ids_param.split(',')]
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid account IDs format'}), 400
    
    analyzer = DataAnalyzer()
    result = analyzer.get_cross_account_analytics(account_ids)
    return jsonify(result)

@app.route('/api/analytics/instrument/<symbol>')
def api_instrument_analytics(symbol):
    """Get analytics for a specific instrument"""
    account_ids_param = request.args.get('account_ids')
    account_ids = None
    
    if account_ids_param:
        try:
            account_ids = [int(x) for x in account_ids_param.split(',')]
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid account IDs format'}), 400
    
    analyzer = DataAnalyzer()
    result = analyzer.get_instrument_analytics(symbol, account_ids)
    return jsonify(result)

@app.route('/api/analytics/pnl-over-time')
def api_pnl_over_time():
    """Get P&L over time analytics"""
    account_ids_param = request.args.get('account_ids')
    start_date_param = request.args.get('start_date')
    end_date_param = request.args.get('end_date')
    
    account_ids = None
    start_date = None
    end_date = None
    
    if account_ids_param:
        try:
            account_ids = [int(x) for x in account_ids_param.split(',')]
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid account IDs format'}), 400
    
    if start_date_param:
        try:
            start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid start_date format. Use YYYY-MM-DD'}), 400
    
    if end_date_param:
        try:
            end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid end_date format. Use YYYY-MM-DD'}), 400
    
    analyzer = DataAnalyzer()
    result = analyzer.get_pnl_over_time(account_ids, start_date, end_date)
    return jsonify(result)

@app.route('/api/analytics/trans-codes')
def api_trans_code_analytics():
    """Get transaction code analytics"""
    account_ids_param = request.args.get('account_ids')
    account_ids = None
    
    if account_ids_param:
        try:
            account_ids = [int(x) for x in account_ids_param.split(',')]
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid account IDs format'}), 400
    
    analyzer = DataAnalyzer()
    result = analyzer.get_trans_code_analytics(account_ids)
    return jsonify(result)

@app.route('/api/analytics/symbols')
def api_symbols_list():
    """Get list of all traded symbols"""
    account_ids_param = request.args.get('account_ids')
    
    query = db.session.query(Trade.symbol).distinct().join(Account)
    
    if account_ids_param:
        try:
            account_ids = [int(x) for x in account_ids_param.split(',')]
            query = query.filter(Account.id.in_(account_ids))
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid account IDs format'}), 400
    
    symbols = query.filter(Account.is_active == True).all()
    
    return jsonify({
        'symbols': [symbol[0] for symbol in symbols],
        'count': len(symbols)
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