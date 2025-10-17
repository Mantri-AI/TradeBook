"""
CSV Import service for trading data
"""
import pandas as pd
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
import re
from decimal import Decimal
from models.database import db, Account, Trade

logger = logging.getLogger(__name__)

class CSVImportService:
    """Service for importing trading data from CSV files"""
    
    def __init__(self):
        pass
    
    def import_robinhood_csv(self, csv_content: str, account: Account) -> Dict[str, Any]:
        """
        Import Robinhood CSV data
        
        Expected CSV format:
        Activity Date,Process Date,Settle Date,Instrument,Description,Trans Code,Quantity,Price,Amount
        """
        try:
            # Parse CSV content with error handling
            from io import StringIO
            
            # Read CSV with flexible parsing options
            df = pd.read_csv(
                StringIO(csv_content),
                on_bad_lines='skip',  # Skip malformed lines
                engine='python',  # Use Python engine for more flexibility
                skip_blank_lines=True,  # Skip blank lines
                skipinitialspace=True  # Skip spaces after delimiter
            )
            
            # Remove columns with empty/unnamed headers
            df = df.loc[:, ~df.columns.str.match('^Unnamed')]
            df = df.loc[:, df.columns.notna()]
            df = df.loc[:, df.columns.str.strip() != '']
            
            # Drop rows where all values are NaN
            df = df.dropna(how='all')
            
            # Drop columns where all values are NaN
            df = df.dropna(axis=1, how='all')
            
            # Strip whitespace from column names
            df.columns = df.columns.str.strip()
            
            # Validate required columns
            required_columns = ['Activity Date', 'Process Date', 'Settle Date', 'Instrument', 
                              'Description', 'Trans Code', 'Quantity', 'Price', 'Amount']
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return {
                    'success': False,
                    'message': f'Missing required columns: {", ".join(missing_columns)}'
                }
            
            imported_count = 0
            duplicates_count = 0
            errors = []
            skipped_rows = 0
            
            for index, row in df.iterrows():
                try:
                    # Skip rows with missing critical data
                    if pd.isna(row.get('Activity Date')) or pd.isna(row.get('Instrument')):
                        skipped_rows += 1
                        continue
                    
                    trade_data = self._parse_robinhood_row(row, account.id)
                    
                    # Check for duplicates
                    existing_trade = Trade.query.filter_by(
                        account_id=account.id,
                        symbol=trade_data['symbol'],
                        activity_date=trade_data['activity_date'],
                        trans_code=trade_data['trans_code'],
                        total_amount=trade_data['total_amount']
                    ).first()
                    
                    if existing_trade:
                        duplicates_count += 1
                        continue
                    
                    # Create new trade
                    trade = Trade(**trade_data)
                    db.session.add(trade)
                    imported_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {index + 2}: {str(e)}")
                    logger.error(f"Error processing row {index + 2}: {str(e)}")
            
            if errors and len(errors) >= len(df) * 0.5:  # If more than 50% errors
                db.session.rollback()
                return {
                    'success': False,
                    'message': f'Too many errors in CSV. First few errors: {"; ".join(errors[:3])}'
                }
            
            db.session.commit()
            
            result = {
                'success': True,
                'imported_count': imported_count,
                'duplicates_count': duplicates_count,
                'errors_count': len(errors),
                'errors': errors[:10]  # Return first 10 errors
            }
            
            if skipped_rows > 0:
                result['skipped_rows'] = skipped_rows
                result['message'] = f'Imported {imported_count} trades, {duplicates_count} duplicates, {skipped_rows} rows skipped (empty data)'
            
            return result
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error importing CSV: {str(e)}")
            return {
                'success': False,
                'message': f'Error processing CSV: {str(e)}'
            }
    
    def _parse_robinhood_row(self, row, account_id: int) -> Dict[str, Any]:
        """Parse a single row from Robinhood CSV"""
        
        # Parse dates
        activity_date = pd.to_datetime(row['Activity Date']).date()
        process_date = pd.to_datetime(row['Process Date']).date() if pd.notna(row['Process Date']) else None
        settle_date = pd.to_datetime(row['Settle Date']).date() if pd.notna(row['Settle Date']) else None
        
        # Parse instrument and description
        symbol = str(row['Instrument']).strip().upper()
        description = str(row['Description']).strip()
        trans_code = str(row['Trans Code']).strip().upper()
        
        # Parse financial data
        # Handle quantity: remove 'S' suffix if present
        quantity_str = str(row['Quantity']).strip().upper()
        if quantity_str.endswith('S'):
            quantity_str = quantity_str[:-1]
        quantity = abs(float(quantity_str)) if quantity_str and quantity_str != 'NAN' else 0
        
        # Handle price: remove '$' and clean up
        price_str = str(row['Price']).strip()
        price_str = price_str.replace('$', '').replace(',', '')
        price = abs(float(price_str)) if price_str and price_str != 'nan' else 0
        
        # Parse amount (remove '$', handle parentheses as negative)
        amount_str = str(row['Amount']).strip()
        amount_str = amount_str.replace('$', '').replace(',', '')
        # Handle parentheses as negative values
        if amount_str.startswith('(') and amount_str.endswith(')'):
            amount_str = '-' + amount_str[1:-1]
        total_amount = float(amount_str) if amount_str and amount_str != 'nan' else 0
        
        # Determine side based on trans code and amount
        side = self._determine_side(trans_code, total_amount)
        
        # Parse options data if applicable
        option_data = self._parse_option_description(description)
        instrument_type = 'option' if option_data['is_option'] else 'stock'
        
        return {
            'account_id': account_id,
            'symbol': symbol,
            'instrument_type': instrument_type,
            'activity_date': activity_date,
            'process_date': process_date,
            'settle_date': settle_date,
            'description': description,
            'trans_code': trans_code,
            'side': side,
            'quantity': quantity,
            'price': price,
            'total_amount': abs(total_amount),
            'fees': 0,  # Robinhood typically doesn't charge fees
            'option_type': option_data.get('option_type'),
            'strike_price': option_data.get('strike_price'),
            'expiration_date': option_data.get('expiration_date'),
            'executed_at': datetime.combine(activity_date, datetime.min.time()),
            'state': 'filled',
            'import_source': 'csv_import'
        }
    
    def _determine_side(self, trans_code: str, amount: float) -> str:
        """Determine buy/sell side based on transaction code and amount"""
        buy_codes = ['BTO', 'BTC']  # Buy to Open, Buy to Close
        sell_codes = ['STO', 'STC']  # Sell to Open, Sell to Close
        
        if trans_code in buy_codes:
            return 'buy'
        elif trans_code in sell_codes:
            return 'sell'
        else:
            # Fallback to amount sign
            return 'buy' if amount < 0 else 'sell'
    
    def _parse_option_description(self, description: str) -> Dict[str, Any]:
        """Parse option details from description"""
        result = {
            'is_option': False,
            'option_type': None,
            'strike_price': None,
            'expiration_date': None
        }
        
        # Look for option pattern: "SYMBOL MM/DD/YYYY Call/Put $XX.XX"
        option_pattern = r'(\w+)\s+(\d{1,2}/\d{1,2}/\d{4})\s+(Call|Put)\s+\$(\d+\.?\d*)'
        match = re.search(option_pattern, description, re.IGNORECASE)
        
        if match:
            result['is_option'] = True
            exp_date_str = match.group(2)
            result['option_type'] = match.group(3).lower()
            result['strike_price'] = float(match.group(4))
            
            # Parse expiration date
            try:
                result['expiration_date'] = datetime.strptime(exp_date_str, '%m/%d/%Y').date()
            except ValueError:
                pass
        
        return result
    
    def import_generic_csv(self, csv_content: str, account: Account, mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Import generic CSV with custom column mapping
        
        Args:
            csv_content: CSV file content
            account: Account to import to
            mapping: Dictionary mapping CSV columns to our fields
        """
        try:
            from io import StringIO
            
            # Read CSV with flexible parsing options
            df = pd.read_csv(
                StringIO(csv_content),
                on_bad_lines='skip',  # Skip malformed lines
                engine='python',  # Use Python engine for more flexibility
                skip_blank_lines=True,  # Skip blank lines
                skipinitialspace=True  # Skip spaces after delimiter
            )
            
            # Remove columns with empty/unnamed headers
            df = df.loc[:, ~df.columns.str.match('^Unnamed')]
            df = df.loc[:, df.columns.notna()]
            df = df.loc[:, df.columns.str.strip() != '']
            
            # Drop rows where all values are NaN
            df = df.dropna(how='all')
            
            # Drop columns where all values are NaN
            df = df.dropna(axis=1, how='all')
            
            # Strip whitespace from column names
            df.columns = df.columns.str.strip()
            
            # Validate mapped columns exist
            missing_columns = [col for col in mapping.values() if col and col not in df.columns]
            if missing_columns:
                return {
                    'success': False,
                    'message': f'Missing mapped columns: {", ".join(missing_columns)}'
                }
            
            imported_count = 0
            duplicates_count = 0
            errors = []
            skipped_rows = 0
            
            for index, row in df.iterrows():
                try:
                    # Skip rows with all NaN values
                    if row.isna().all():
                        skipped_rows += 1
                        continue
                        
                    trade_data = self._parse_generic_row(row, account.id, mapping)
                    
                    # Check for duplicates
                    existing_trade = Trade.query.filter_by(
                        account_id=account.id,
                        symbol=trade_data['symbol'],
                        activity_date=trade_data['activity_date'],
                        total_amount=trade_data['total_amount']
                    ).first()
                    
                    if existing_trade:
                        duplicates_count += 1
                        continue
                    
                    # Create new trade
                    trade = Trade(**trade_data)
                    db.session.add(trade)
                    imported_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {index + 2}: {str(e)}")
                    logger.error(f"Error processing row {index + 2}: {str(e)}")
            
            db.session.commit()
            
            result = {
                'success': True,
                'imported_count': imported_count,
                'duplicates_count': duplicates_count,
                'errors_count': len(errors),
                'errors': errors[:10]
            }
            
            if skipped_rows > 0:
                result['skipped_rows'] = skipped_rows
            
            return result
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error importing generic CSV: {str(e)}")
            return {
                'success': False,
                'message': f'Error processing CSV: {str(e)}'
            }
    
    def _parse_generic_row(self, row, account_id: int, mapping: Dict[str, str]) -> Dict[str, Any]:
        """Parse a row using generic mapping"""
        
        # Required fields with defaults
        trade_data = {
            'account_id': account_id,
            'symbol': 'UNKNOWN',
            'instrument_type': 'stock',
            'activity_date': date.today(),
            'trans_code': 'UNK',
            'side': 'buy',
            'quantity': 0,
            'price': 0,
            'total_amount': 0,
            'fees': 0,
            'executed_at': datetime.now(),
            'state': 'filled',
            'import_source': 'csv_import'
        }
        
        # Map fields from CSV
        for our_field, csv_column in mapping.items():
            if csv_column and csv_column in row and pd.notna(row[csv_column]):
                value = row[csv_column]
                
                if our_field == 'activity_date':
                    trade_data[our_field] = pd.to_datetime(value).date()
                elif our_field in ['quantity', 'price', 'total_amount', 'fees', 'strike_price']:
                    # Clean and convert numeric fields
                    if isinstance(value, str):
                        value = value.replace('$', '').replace(',', '').replace('(', '-').replace(')', '')
                    trade_data[our_field] = float(value) if value else 0
                else:
                    trade_data[our_field] = str(value).strip()
        
        # Set executed_at from activity_date
        trade_data['executed_at'] = datetime.combine(trade_data['activity_date'], datetime.min.time())
        
        return trade_data