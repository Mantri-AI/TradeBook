# Mantri Trade Book v2.0

A comprehensive Python/Flask application for managing multiple trading accounts with advanced analytics, CSV import capabilities, and cross-provider support.

## 🚀 New Features in v2.0

### Multi-Provider Support
- **Multiple Brokers**: Support for Robinhood, Fidelity, WeBull, and Charles Schwab
- **Flexible Authentication**: Option for API authentication or manual data entry
- **Provider-Specific Features**: Tailored integration for each supported provider

### CSV Import Functionality
- **Robinhood CSV Import**: Direct import of Robinhood transaction history
- **Deduplication**: Automatic detection and prevention of duplicate transactions
- **Format Support**: Standardized CSV format with activity date, trans codes, and amounts
- **Batch Processing**: Import thousands of transactions efficiently

### Enhanced Analytics
- **Cross-Account Analysis**: Compare performance across multiple accounts and providers
- **Instrument-Specific Analytics**: Deep dive into individual stock/option performance
- **P&L Over Time**: Detailed profit/loss tracking with daily, monthly, and yearly views
- **Transaction Code Analysis**: BTO, STO, BTC, STC breakdown and analytics
- **Multi-Account Filtering**: Filter analytics by specific accounts or providers

### Advanced Features
- **Manual Account Creation**: Create accounts without API credentials for CSV-only workflows
- **Enhanced Trade Tracking**: Activity date, process date, settle date, and transaction codes
- **Improved UI**: Modern interface with provider badges, transaction code display, and import status
- **Better Filtering**: Filter by transaction codes, providers, and import sources

## 🛠️ Technology Stack

- **Backend**: Python 3.8+, Flask, SQLAlchemy
- **Database**: SQLite (easily upgradeable to PostgreSQL/MySQL)
- **Frontend**: Bootstrap 5, jQuery, Chart.js
- **Data Processing**: Pandas for CSV import and analytics
- **API Integration**: robin-stocks for Robinhood API (extensible for other providers)
- **Security**: Cryptography for credential encryption
- **Analytics**: NumPy for advanced calculations

## 📋 Prerequisites

- Python 3.12 or higher
- pip (Python package installer)
- Trading account(s) with any supported provider

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd mantri_trade_book

# Make setup script executable
chmod +x setup.sh

# Run setup script
./setup.sh
```

### 2. Initialize Database (Fresh Installation)

```bash
# Initialize fresh database
python init_db.py
```

### 3. Database Management (Optional)

```bash
# Use the database manager for various operations
python db_manager.py init     # Initialize fresh database
python db_manager.py backup   # Create database backup
python db_manager.py verify   # Verify database integrity
```

### 4. Run the Application

```bash
# Start the application
python app.py

# Or use the quick start script
python run.py
```

### 5. Access the Application

Open your browser and navigate to: `http://localhost:5000`

## 🎯 Usage Guide

### Adding Accounts

#### Option 1: API Authentication
1. Navigate to the **Accounts** page
2. Click **"Add Trading Account"**
3. Select your provider (Robinhood, Fidelity, WeBull, Schwab)
4. Choose **"API Authentication"**
5. Enter credentials and test connection
6. Save the account

#### Option 2: Manual Entry (CSV Import)
1. Navigate to the **Accounts** page
2. Click **"Add Trading Account"**
3. Select your provider
4. Choose **"Manual Entry"**
5. Enter account name only
6. Save the account
7. Import CSV data (see below)

### CSV Import Process

#### For Robinhood Users:
1. Download transaction history from Robinhood
2. In the account creation modal, select your CSV file
3. Preview the data to ensure proper formatting
4. Click "Import Data" to process transactions
5. Review import results (imported count, duplicates skipped)

#### CSV Format Requirements:
```csv
Activity Date,Process Date,Settle Date,Instrument,Description,Trans Code,Quantity,Price,Amount
10/14/2025,10/14/2025,10/15/2025,YOU,YOU 11/21/2025 Put $27.00,STO,2,$0.78,$155.91
```

### Advanced Analytics

#### Cross-Account Analysis
1. Navigate to **Analytics** > **Cross-Account** tab
2. Select specific accounts or view all
3. Compare volume, trades, and performance across accounts
4. View account-specific charts and breakdowns

#### Instrument Analysis
1. Go to **Analytics** > **Instruments** tab
2. Search for or select a symbol
3. View detailed P&L, transaction history, and price analytics
4. Analyze transaction codes and trading patterns

#### P&L Over Time
1. Access **Analytics** > **P&L Analysis** tab
2. Set date ranges and account filters
3. View daily, monthly, and cumulative P&L charts
4. Identify best and worst performing periods

#### Transaction Code Analytics
1. Visit **Analytics** > **Transaction Codes** tab
2. Analyze BTO, STO, BTC, STC patterns
3. View volume and frequency by transaction type
4. Compare across accounts and time periods

## 🔍 Features Deep Dive

### Enhanced Trade Tracking
- **Activity Date**: The actual trade execution date
- **Process Date**: When the trade was processed by the broker
- **Settle Date**: Settlement date for the transaction
- **Transaction Codes**: BTO (Buy to Open), STO (Sell to Open), etc.
- **Import Source**: Track whether data came from API or CSV import
- **Deduplication**: Prevent duplicate imports based on symbol, date, code, and amount

### Multi-Provider Support
- **Provider-Specific Logic**: Different authentication and data processing for each provider
- **Unified Interface**: Consistent UI regardless of the underlying provider
- **Extensible Architecture**: Easy to add new providers in the future

### Advanced Filtering
- **Multi-Account Filtering**: Filter analytics across selected accounts
- **Transaction Code Filtering**: Filter trades by BTO, STO, BTC, STC
- **Provider Filtering**: View data from specific brokers only
- **Date Range Filtering**: Custom date ranges for analysis
- **Import Source Filtering**: Separate API vs. CSV imported data

## 🚀 Production Deployment

### Security Checklist
- [ ] Set strong SECRET_KEY and ENCRYPTION_KEY
- [ ] Use PostgreSQL/MySQL instead of SQLite
- [ ] Enable HTTPS with SSL certificates
- [ ] Configure proper firewall rules
- [ ] Regular database backups
- [ ] Monitor application logs
- [ ] Validate CSV uploads for security

### Database Setup for Production
```bash
# Initialize production database
python init_db.py

# Or use the database manager
python db_manager.py init

# Verify database integrity
python db_manager.py verify
```

## 🔄 Fresh Installation

For a completely fresh installation on a new system:

1. **Clone and setup**: Follow the Quick Start guide above
2. **Initialize database**: `python init_db.py` or `python db_manager.py init`
3. **Start application**: `python app.py` or `python run.py`
4. **Access application**: Open `http://localhost:5000` in your browser

Your application will start with a clean database and sample demo account (inactive by default).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Update documentation
6. Submit a pull request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Run linting
flake8 app.py services/ models/
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This application is for educational and personal use only. Please ensure compliance with your broker's Terms of Service and API usage policies. Trading involves risk, and past performance does not guarantee future results.

## 🆘 Support & Troubleshooting

### Common Issues

**CSV Import Fails**
- Ensure CSV format matches expected structure
- Check for special characters in data
- Verify dates are in MM/DD/YYYY format

**Database Initialization Issues**
- Ensure Python 3.8+ is installed
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Try force initialization: `python init_db.py --force`
- Use database manager: `python db_manager.py init`

**Account Connection Problems**
- Verify credentials are correct
- Check MFA requirements
- Ensure API access is enabled

### Getting Help
1. Check the existing issues on GitHub
2. Search documentation for common solutions
3. Create a new issue with detailed description
4. Include relevant logs and error messages

## 🎉 Acknowledgments

- Robinhood for providing API access
- robin-stocks library for Python integration
- Chart.js for beautiful visualizations
- Bootstrap for responsive UI components
- Pandas for powerful data processing
- SQLAlchemy for robust ORM capabilities

## 🗺️ Roadmap

### Upcoming Features
- [ ] Additional provider integrations (TD Ameritrade, E*TRADE)
- [ ] Real-time price updates and alerts
- [ ] Advanced options strategies analysis
- [ ] Mobile app development
- [ ] API rate limiting and optimization
- [ ] Enhanced portfolio optimization tools
- [ ] Automated report generation
- [ ] Integration with tax software

---

**Happy Trading! 📈**

*TradeBook v2.0 - Empowering traders with comprehensive multi-provider portfolio management*