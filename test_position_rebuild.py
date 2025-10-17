#!/usr/bin/env python3
"""
Test script for position rebuilding functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models.database import db, Account, Position, Trade
from services.data_analyzer import DataAnalyzer
from datetime import datetime, date

def create_test_data():
    """Create some test trade data"""
    with app.app_context():
        # Create test account if it doesn't exist
        test_account = Account.query.filter_by(name='Test Account').first()
        if not test_account:
            test_account = Account(
                name='Test Account',
                provider='test',
                is_active=True
            )
            db.session.add(test_account)
            db.session.commit()
        
        # Clear existing test trades and positions
        Trade.query.filter_by(account_id=test_account.id).delete()
        Position.query.filter_by(account_id=test_account.id).delete()
        db.session.commit()
        
        # Create test trades
        test_trades = [
            # AAPL stock trades
            {
                'account_id': test_account.id,
                'symbol': 'AAPL',
                'instrument_type': 'stock',
                'activity_date': date(2024, 1, 15),
                'trans_code': 'BTO',
                'side': 'buy',
                'quantity': 100,
                'price': 150.00,
                'total_amount': 15000.00,
                'executed_at': datetime(2024, 1, 15, 10, 30),
                'state': 'filled',
                'import_source': 'test'
            },
            {
                'account_id': test_account.id,
                'symbol': 'AAPL',
                'instrument_type': 'stock',
                'activity_date': date(2024, 2, 1),
                'trans_code': 'BTO',
                'side': 'buy',
                'quantity': 50,
                'price': 160.00,
                'total_amount': 8000.00,
                'executed_at': datetime(2024, 2, 1, 14, 15),
                'state': 'filled',
                'import_source': 'test'
            },
            {
                'account_id': test_account.id,
                'symbol': 'AAPL',
                'instrument_type': 'stock',
                'activity_date': date(2024, 2, 15),
                'trans_code': 'STC',
                'side': 'sell',
                'quantity': 25,
                'price': 165.00,
                'total_amount': 4125.00,
                'executed_at': datetime(2024, 2, 15, 11, 45),
                'state': 'filled',
                'import_source': 'test'
            },
            # MSFT option trades
            {
                'account_id': test_account.id,
                'symbol': 'MSFT',
                'instrument_type': 'option',
                'activity_date': date(2024, 1, 20),
                'trans_code': 'BTO',
                'side': 'buy',
                'quantity': 5,
                'price': 2.50,
                'total_amount': 1250.00,  # 5 * 2.50 * 100
                'option_type': 'call',
                'strike_price': 400.00,
                'expiration_date': date(2024, 3, 15),
                'executed_at': datetime(2024, 1, 20, 9, 30),
                'state': 'filled',
                'import_source': 'test'
            },
            {
                'account_id': test_account.id,
                'symbol': 'MSFT',
                'instrument_type': 'option',
                'activity_date': date(2024, 2, 5),
                'trans_code': 'STC',
                'side': 'sell',
                'quantity': 2,
                'price': 3.00,
                'total_amount': 600.00,  # 2 * 3.00 * 100
                'option_type': 'call',
                'strike_price': 400.00,
                'expiration_date': date(2024, 3, 15),
                'executed_at': datetime(2024, 2, 5, 15, 45),
                'state': 'filled',
                'import_source': 'test'
            },
            # TSLA fully sold position (should not create position)
            {
                'account_id': test_account.id,
                'symbol': 'TSLA',
                'instrument_type': 'stock',
                'activity_date': date(2024, 1, 10),
                'trans_code': 'BTO',
                'side': 'buy',
                'quantity': 10,
                'price': 200.00,
                'total_amount': 2000.00,
                'executed_at': datetime(2024, 1, 10, 13, 20),
                'state': 'filled',
                'import_source': 'test'
            },
            {
                'account_id': test_account.id,
                'symbol': 'TSLA',
                'instrument_type': 'stock',
                'activity_date': date(2024, 1, 25),
                'trans_code': 'STC',
                'side': 'sell',
                'quantity': 10,
                'price': 220.00,
                'total_amount': 2200.00,
                'executed_at': datetime(2024, 1, 25, 10, 10),
                'state': 'filled',
                'import_source': 'test'
            },
        ]
        
        for trade_data in test_trades:
            trade = Trade(**trade_data)
            db.session.add(trade)
        
        db.session.commit()
        print(f"Created {len(test_trades)} test trades for account {test_account.id}")
        return test_account.id

def test_position_rebuild(account_id):
    """Test the position rebuilding functionality"""
    with app.app_context():
        analyzer = DataAnalyzer()
        
        print("\n--- Testing Position Rebuild ---")
        
        # Check positions before rebuild
        positions_before = Position.query.filter_by(account_id=account_id).all()
        print(f"Positions before rebuild: {len(positions_before)}")
        
        # Rebuild positions
        result = analyzer.rebuild_positions_from_trades(account_id=account_id)
        print(f"Rebuild result: {result}")
        
        # Check positions after rebuild
        positions_after = Position.query.filter_by(account_id=account_id).all()
        print(f"Positions after rebuild: {len(positions_after)}")
        
        # Display created positions
        for position in positions_after:
            print(f"  Position: {position.symbol} ({position.instrument_type})")
            print(f"    Quantity: {position.quantity}")
            print(f"    Avg Buy Price: ${position.average_buy_price:.2f}")
            if position.instrument_type == 'option':
                print(f"    Option: {position.option_type} {position.strike_price} exp {position.expiration_date}")
        
        # Verify expected positions
        expected_positions = {
            'AAPL': {'quantity': 125, 'type': 'stock'},  # 100 + 50 - 25 = 125
            'MSFT': {'quantity': 3, 'type': 'option'},   # 5 - 2 = 3 options
            # TSLA should not have a position (fully sold)
        }
        
        actual_positions = {pos.symbol: {'quantity': pos.quantity, 'type': pos.instrument_type} 
                          for pos in positions_after}
        
        print("\n--- Verification ---")
        for symbol, expected in expected_positions.items():
            if symbol in actual_positions:
                actual = actual_positions[symbol]
                if actual['quantity'] == expected['quantity'] and actual['type'] == expected['type']:
                    print(f"✓ {symbol}: Expected {expected['quantity']} {expected['type']}, got {actual['quantity']} {actual['type']}")
                else:
                    print(f"✗ {symbol}: Expected {expected['quantity']} {expected['type']}, got {actual['quantity']} {actual['type']}")
            else:
                print(f"✗ {symbol}: Expected position but none found")
        
        # Check that TSLA position was not created
        tsla_positions = [pos for pos in positions_after if pos.symbol == 'TSLA']
        if not tsla_positions:
            print("✓ TSLA: Correctly no position created (fully sold)")
        else:
            print(f"✗ TSLA: Unexpected position found with quantity {tsla_positions[0].quantity}")

if __name__ == '__main__':
    print("Testing Position Rebuilding Functionality")
    
    try:
        # Create test data
        account_id = create_test_data()
        
        # Test rebuild
        test_position_rebuild(account_id)
        
        print("\n✓ Position rebuilding test completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()