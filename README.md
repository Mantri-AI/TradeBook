# Mantri Trade Book

A comprehensive Python/Flask application for managing multiple Robinhood trading accounts with advanced analytics and visualization capabilities.

## 🚀 Features

### Core Functionality
- **Multi-Account Management**: Connect and manage multiple Trading accounts
- **Real-time Portfolio Tracking**: Monitor positions, values, and daily changes
- **Trading History**: Complete trade history with advanced filtering and search
- **Options Support**: Full options trading support with Greeks and analytics
- **Data Persistence**: SQLite database for reliable local data storage
- **Secure Credentials**: Encrypted local storage of account credentials

### Dashboard & Analytics
- **Interactive Dashboard**: Clean, modern interface with real-time updates
- **Portfolio Visualization**: Charts for allocation, performance, and trends
- **Risk Analytics**: Beta, Sharpe ratio, VaR, and other risk metrics
- **Trading Analytics**: Performance stats, win rates, and P&L analysis
- **Options Analytics**: Greeks tracking, expiration analysis, ITM/OTM positions
- **Sector Analysis**: Portfolio breakdown by industry sectors

### Advanced Features
- **Data Filtering**: Advanced search and filtering capabilities
- **Export Functions**: Export data to CSV/Excel formats
- **Responsive Design**: Mobile-friendly interface
- **Real-time Updates**: Auto-refresh of positions and prices
- **Batch Operations**: Sync multiple accounts simultaneously

## 🛠️ Technology Stack

- **Backend**: Python 3.8+, Flask, SQLAlchemy
- **Database**: SQLite (easily upgradeable to PostgreSQL/MySQL)
- **Frontend**: Bootstrap 5, jQuery, Chart.js
- **API Integration**: robin-stocks for Robinhood API
- **Security**: Cryptography for credential encryption
- **Analytics**: Pandas, NumPy for data analysis

## 📋 Prerequisites

- Python 3.12 or higher
- pip (Python package installer)
- Robinhood account(s) with API access

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

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your configuration
nano .env
```

### 3. Run the Application

```bash
# Activate virtual environment
source venv/bin/activate

# Start the application
python app.py
```

### 4. Access the Application

Open your browser and navigate to: `http://localhost:5000`


## 🎯 Usage Guide

### Adding Your First Account

1. Navigate to the **Accounts** page
2. Click **"Add Account"**
3. Enter your account details:
   - Account name (friendly name)
   - Robinhood username/email
   - Password
   - MFA code (if enabled)
4. Test the connection
5. Save the account

### Viewing Your Portfolio

1. The **Dashboard** provides an overview of all accounts
2. Use **Positions** page for detailed position analysis
3. **Trades** page shows complete trading history
4. **Analytics** page offers advanced portfolio analytics

### Filtering and Search

- Use account filters to view specific accounts
- Search by symbol across all views
- Filter trades by date range, side (buy/sell), and type
- Export filtered data to CSV

## 🔍 Features Deep Dive

### Options Trading Support
- Full options chain analysis
- Greeks calculation and tracking
- Expiration date monitoring
- ITM/OTM position analysis
- Options P&L tracking

### Risk Management
- Portfolio beta calculation
- Sharpe ratio analysis
- Maximum drawdown tracking
- Value at Risk (VaR) calculation
- Position concentration analysis

### Performance Analytics
- Win/loss ratio calculation
- Average holding periods
- Profit factor analysis
- Monthly/yearly returns
- Benchmark comparison (SPY)

## 🚀 Production Deployment

### Security Checklist
- [ ] Set strong SECRET_KEY and ENCRYPTION_KEY
- [ ] Use PostgreSQL/MySQL instead of SQLite
- [ ] Enable HTTPS with SSL certificates
- [ ] Set SESSION_COOKIE_SECURE=True
- [ ] Configure proper firewall rules
- [ ] Regular database backups
- [ ] Monitor application logs

### Recommended Production Setup
```bash
# Use Gunicorn for production
pip install gunicorn

# Run with multiple workers
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This application is for educational and personal use only. Please ensure compliance with Robinhood's Terms of Service and API usage policies. Trading involves risk, and past performance does not guarantee future results.

## 🆘 Support

For issues, questions, or feature requests:
1. Check the existing issues
2. Create a new issue with detailed description
3. Include relevant logs and error messages

## 🎉 Acknowledgments

- Robinhood for providing API access
- robin-stocks library for Python integration
- Chart.js for beautiful visualizations
- Bootstrap for responsive UI components

---

**Happy Trading! 📈**