import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import requests
import json

# Try to import plotly, fallback to basic charts if not available
try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# Try to import supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# Supabase HTTP Client Class
class SupabaseConnector:
    def __init__(self):
        self.url = None
        self.anon_key = None
        self.service_key = None
        self.client = None
        self.connected = False
        
    def configure(self, url: str, anon_key: str, service_key: str = None):
        """Configure Supabase connection parameters"""
        self.url = url.rstrip('/')
        self.anon_key = anon_key
        self.service_key = service_key
        
    def connect(self):
        """Establish connection to Supabase"""
        try:
            if not self.url or not self.anon_key:
                raise ValueError("URL and anon key are required")
                
            if SUPABASE_AVAILABLE:
                # Use official Supabase client
                self.client = create_client(self.url, self.anon_key)
                self.connected = True
                return True, "Connected successfully using Supabase client"
            else:
                # Fallback to HTTP client
                self.connected = self._test_connection()
                if self.connected:
                    return True, "Connected successfully using HTTP client"
                else:
                    return False, "Connection failed - check credentials"
                    
        except Exception as e:
            self.connected = False
            return False, f"Connection error: {str(e)}"
    
    def _test_connection(self):
        """Test connection using direct HTTP call"""
        try:
            headers = {
                'apikey': self.anon_key,
                'Authorization': f'Bearer {self.anon_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.url}/rest/v1/",
                headers=headers,
                timeout=10
            )
            
            return response.status_code in [200, 404]  # 404 is OK, means connection works
        except Exception:
            return False
    
    def insert_trade(self, trade_data: dict):
        """Insert trade data into Supabase"""
        if not self.connected:
            return False, "Not connected to Supabase"
            
        try:
            if SUPABASE_AVAILABLE and self.client:
                # Use official client
                result = self.client.table('trades').insert(trade_data).execute()
                return True, "Trade inserted successfully"
            else:
                # Use HTTP client
                headers = {
                    'apikey': self.anon_key,
                    'Authorization': f'Bearer {self.anon_key}',
                    'Content-Type': 'application/json',
                    'Prefer': 'return=minimal'
                }
                
                response = requests.post(
                    f"{self.url}/rest/v1/trades",
                    headers=headers,
                    json=trade_data,
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    return True, "Trade inserted successfully"
                else:
                    return False, f"Insert failed: {response.text}"
                    
        except Exception as e:
            return False, f"Insert error: {str(e)}"
    
    def get_trades(self, limit: int = 100):
        """Fetch trades from Supabase"""
        if not self.connected:
            return [], "Not connected to Supabase"
            
        try:
            if SUPABASE_AVAILABLE and self.client:
                # Use official client
                result = self.client.table('trades').select('*').limit(limit).execute()
                return result.data, "Trades fetched successfully"
            else:
                # Use HTTP client
                headers = {
                    'apikey': self.anon_key,
                    'Authorization': f'Bearer {self.anon_key}',
                    'Content-Type': 'application/json'
                }
                
                response = requests.get(
                    f"{self.url}/rest/v1/trades?limit={limit}",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    return response.json(), "Trades fetched successfully"
                else:
                    return [], f"Fetch failed: {response.text}"
                    
        except Exception as e:
            return [], f"Fetch error: {str(e)}"
    
    def create_tables(self):
        """Create necessary tables (requires service key)"""
        if not self.service_key:
            return False, "Service key required for table creation"
            
        try:
            # SQL to create trades table
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS trades (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                side VARCHAR(10) NOT NULL,
                quantity DECIMAL(18,8) NOT NULL,
                price DECIMAL(18,8) NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                strategy VARCHAR(50),
                pnl DECIMAL(18,8),
                status VARCHAR(20) DEFAULT 'completed'
            );
            
            CREATE TABLE IF NOT EXISTS portfolio (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                quantity DECIMAL(18,8) NOT NULL,
                avg_price DECIMAL(18,8) NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
            
            headers = {
                'apikey': self.service_key,
                'Authorization': f'Bearer {self.service_key}',
                'Content-Type': 'application/json'
            }
            
            # Execute SQL using PostgREST
            response = requests.post(
                f"{self.url}/rest/v1/rpc/sql",
                headers=headers,
                json={"query": create_table_sql},
                timeout=30
            )
            
            if response.status_code in [200, 204]:
                return True, "Tables created successfully"
            else:
                return False, f"Table creation failed: {response.text}"
                
        except Exception as e:
            return False, f"Table creation error: {str(e)}"

# Page configuration
st.set_page_config(
    page_title="AutoTrader Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
    .status-active {
        color: #28a745;
        font-weight: bold;
    }
    .status-inactive {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'trading_active' not in st.session_state:
    st.session_state.trading_active = False
if 'portfolio_value' not in st.session_state:
    st.session_state.portfolio_value = 10000.0
if 'total_trades' not in st.session_state:
    st.session_state.total_trades = 0
if 'daily_pnl' not in st.session_state:
    st.session_state.daily_pnl = 0.0
if 'supabase_connector' not in st.session_state:
    st.session_state.supabase_connector = SupabaseConnector()
if 'supabase_connected' not in st.session_state:
    st.session_state.supabase_connected = False

# Header
st.markdown('<h1 class="main-header">AutoTrader Pro 📈</h1>', unsafe_allow_html=True)

# Sidebar - Trading Controls
st.sidebar.header("🎛️ Trading Controls")

# Trading Strategy Selection
strategy = st.sidebar.selectbox(
    "Select Trading Strategy",
    ["Moving Average Crossover", "RSI Oversold/Overbought", "Bollinger Bands", "MACD Signal"]
)

# Risk Management
st.sidebar.subheader("Risk Management")
max_position_size = st.sidebar.slider("Max Position Size (%)", 1, 50, 10)
stop_loss = st.sidebar.slider("Stop Loss (%)", 1, 20, 5)
take_profit = st.sidebar.slider("Take Profit (%)", 1, 50, 15)

# Trading Pairs
st.sidebar.subheader("Trading Pairs")
selected_pairs = st.sidebar.multiselect(
    "Select Trading Pairs",
    ["BTC/USD", "ETH/USD", "AAPL", "TSLA", "GOOGL", "AMZN", "MSFT"],
    default=["BTC/USD", "ETH/USD"]
)

# Trading Control Button
if st.sidebar.button("🚀 Start Trading" if not st.session_state.trading_active else "⏹️ Stop Trading"):
    st.session_state.trading_active = not st.session_state.trading_active
    if st.session_state.trading_active:
        st.sidebar.success("Trading Started!")
    else:
        st.sidebar.warning("Trading Stopped!")

# Main Dashboard
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Portfolio Value",
        value=f"${st.session_state.portfolio_value:,.2f}",
        delta=f"{st.session_state.daily_pnl:+.2f}"
    )

with col2:
    st.metric(
        label="Total Trades",
        value=st.session_state.total_trades,
        delta="Today"
    )

with col3:
    status_text = "ACTIVE" if st.session_state.trading_active else "INACTIVE"
    status_class = "status-active" if st.session_state.trading_active else "status-inactive"
    st.markdown(f'<p class="{status_class}">Status: {status_text}</p>', unsafe_allow_html=True)

with col4:
    st.metric(
        label="Active Strategy",
        value=strategy.split()[0],
        delta="Selected"
    )

# Create tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📊 Live Charts", "📋 Positions", "📈 Performance", "⚙️ Settings"])

with tab1:
    st.subheader("Live Market Data")
    
    # Generate sample data for demonstration
    dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='H')
    np.random.seed(42)
    
    # Sample price data
    price_data = []
    base_price = 50000 if "BTC" in str(selected_pairs) else 3000
    
    for i, date in enumerate(dates):
        price = base_price + np.cumsum(np.random.randn(1) * 100)[0]
        price_data.append({
            'timestamp': date,
            'price': max(price, base_price * 0.8),  # Prevent negative prices
            'volume': np.random.randint(100, 1000)
        })
    
    df = pd.DataFrame(price_data)
    
    # Create price chart
    if PLOTLY_AVAILABLE:
        fig = go.Figure(data=go.Scatter(
            x=df['timestamp'],
            y=df['price'],
            mode='lines',
            name='Price',
            line=dict(color='#1f77b4', width=2)
        ))
        
        fig.update_layout(
            title="Price Chart",
            xaxis_title="Time",
            yaxis_title="Price ($)",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Fallback to Streamlit's built-in line chart
        st.subheader("Price Chart")
        chart_df = df.set_index('timestamp')[['price']]
        st.line_chart(chart_df)
    
    # Real-time price ticker
    if st.session_state.trading_active:
        placeholder = st.empty()
        for i in range(5):
            current_price = df['price'].iloc[-1] + np.random.randn() * 50
            placeholder.metric(
                label="Current Price",
                value=f"${current_price:,.2f}",
                delta=f"{np.random.randn() * 2:+.2f}%"
            )
            time.sleep(1)

with tab2:
    st.subheader("Current Positions")
    
    # Add trade simulation if connected to Supabase
    if st.session_state.supabase_connected and st.session_state.trading_active:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("📝 Simulate Trade"):
                # Simulate a new trade
                trade_data = {
                    'symbol': np.random.choice(['BTC/USD', 'ETH/USD', 'AAPL', 'TSLA']),
                    'side': np.random.choice(['buy', 'sell']),
                    'quantity': round(np.random.uniform(0.1, 2.0), 4),
                    'price': round(np.random.uniform(100, 50000), 2),
                    'strategy': strategy,
                    'pnl': round(np.random.uniform(-100, 200), 2),
                    'timestamp': datetime.now().isoformat()
                }
                
                with st.spinner("Saving trade to database..."):
                    success, message = st.session_state.supabase_connector.insert_trade(trade_data)
                    if success:
                        st.success("✅ Trade saved to database!")
                        st.session_state.total_trades += 1
                    else:
                        st.error(f"❌ Failed to save trade: {message}")
    
    # Sample positions data
    positions_data = {
        'Symbol': ['BTC/USD', 'ETH/USD', 'AAPL'],
        'Side': ['Long', 'Short', 'Long'],
        'Size': [0.5, 2.0, 100],
        'Entry Price': [48500, 3200, 175.50],
        'Current Price': [49200, 3150, 178.25],
        'PnL': [350, -100, 275],
        'PnL %': [1.44, -1.56, 1.57]
    }
    
    positions_df = pd.DataFrame(positions_data)
    
    # Color code PnL
    def color_pnl(val):
        color = 'green' if val > 0 else 'red'
        return f'color: {color}'
    
    styled_df = positions_df.style.applymap(color_pnl, subset=['PnL', 'PnL %'])
    st.dataframe(styled_df, use_container_width=True)

with tab3:
    st.subheader("Performance Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Portfolio value over time
        portfolio_dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
        portfolio_values = np.cumsum(np.random.randn(len(portfolio_dates)) * 100) + 10000
        
        if PLOTLY_AVAILABLE:
            fig_portfolio = px.line(
                x=portfolio_dates,
                y=portfolio_values,
                title="Portfolio Value Over Time"
            )
            st.plotly_chart(fig_portfolio, use_container_width=True)
        else:
            st.subheader("Portfolio Value Over Time")
            portfolio_df = pd.DataFrame({
                'date': portfolio_dates,
                'value': portfolio_values
            }).set_index('date')
            st.line_chart(portfolio_df)
    
    with col2:
        # Win/Loss ratio
        if PLOTLY_AVAILABLE:
            win_loss_data = {'Outcome': ['Wins', 'Losses'], 'Count': [65, 35]}
            fig_pie = px.pie(
                values=win_loss_data['Count'],
                names=win_loss_data['Outcome'],
                title="Win/Loss Ratio"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.subheader("Win/Loss Ratio")
            st.write("Wins: 65 trades")
            st.write("Losses: 35 trades")
            st.progress(0.65)  # 65% win rate
    
    # Performance metrics
    st.subheader("Key Metrics")
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    
    with metric_col1:
        st.metric("Sharpe Ratio", "1.85")
        st.metric("Max Drawdown", "-5.2%")
    
    with metric_col2:
        st.metric("Win Rate", "65%")
        st.metric("Avg Win", "$125")
    
    with metric_col3:
        st.metric("Total Return", "18.5%")
        st.metric("Avg Loss", "-$75")

with tab4:
    st.subheader("🗄️ Supabase Database Configuration")
    
    # Supabase connection status
    status_color = "🟢" if st.session_state.supabase_connected else "🔴"
    status_text = "Connected" if st.session_state.supabase_connected else "Disconnected"
    st.markdown(f"{status_color} **Database Status:** {status_text}")
    
    # Supabase configuration form
    with st.form("supabase_config"):
        st.write("**Enter your Supabase credentials:**")
        
        supabase_url = st.text_input(
            "Supabase URL", 
            placeholder="https://your-project.supabase.co",
            help="Your Supabase project URL"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            anon_key = st.text_input(
                "Anon Key (Public)", 
                type="password",
                help="Your Supabase anon/public key"
            )
        with col2:
            service_key = st.text_input(
                "Service Key (Optional)", 
                type="password",
                help="Service key for admin operations (table creation)"
            )
        
        # Connection buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            connect_clicked = st.form_submit_button("🔌 Connect", type="primary")
        with col2:
            test_clicked = st.form_submit_button("🧪 Test Connection")
        with col3:
            create_tables_clicked = st.form_submit_button("📋 Create Tables")
    
    # Handle connection
    if connect_clicked:
        if supabase_url and anon_key:
            with st.spinner("Connecting to Supabase..."):
                st.session_state.supabase_connector.configure(
                    supabase_url, anon_key, service_key
                )
                success, message = st.session_state.supabase_connector.connect()
                
                if success:
                    st.session_state.supabase_connected = True
                    st.success(f"✅ {message}")
                else:
                    st.session_state.supabase_connected = False
                    st.error(f"❌ {message}")
        else:
            st.error("❌ Please provide both Supabase URL and Anon Key")
    
    # Handle test connection
    if test_clicked:
        if st.session_state.supabase_connected:
            with st.spinner("Testing database operations..."):
                # Test insert
                test_data = {
                    'symbol': 'TEST/USD',
                    'side': 'buy',
                    'quantity': 1.0,
                    'price': 100.0,
                    'strategy': 'test',
                    'timestamp': datetime.now().isoformat()
                }
                
                success, message = st.session_state.supabase_connector.insert_trade(test_data)
                if success:
                    st.success("✅ Database write test successful")
                    
                    # Test read
                    trades, read_message = st.session_state.supabase_connector.get_trades(5)
                    if trades:
                        st.success("✅ Database read test successful")
                        st.write(f"Found {len(trades)} recent trades")
                    else:
                        st.warning("⚠️ Read test: No trades found (this is normal for new databases)")
                else:
                    st.error(f"❌ Database test failed: {message}")
        else:
            st.error("❌ Please connect to Supabase first")
    
    # Handle table creation
    if create_tables_clicked:
        if service_key:
            with st.spinner("Creating database tables..."):
                success, message = st.session_state.supabase_connector.create_tables()
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ {message}")
        else:
            st.error("❌ Service key is required for table creation")
    
    # Display recent trades if connected
    if st.session_state.supabase_connected:
        st.subheader("📊 Recent Trades from Database")
        
        if st.button("🔄 Refresh Trades"):
            with st.spinner("Fetching trades..."):
                trades, message = st.session_state.supabase_connector.get_trades(10)
                if trades:
                    trades_df = pd.DataFrame(trades)
                    if not trades_df.empty:
                        # Format the dataframe for display
                        if 'timestamp' in trades_df.columns:
                            trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                        
                        st.dataframe(trades_df, use_container_width=True)
                    else:
                        st.info("📝 No trades found in database")
                else:
                    st.warning(f"⚠️ {message}")
    
    st.markdown("---")
    
    # Exchange API settings
    st.subheader("🏦 Exchange API Configuration")
    
    exchange = st.selectbox("Select Exchange", ["Binance", "Coinbase Pro", "Kraken", "Alpaca"])
    
    col1, col2 = st.columns(2)
    with col1:
        api_key = st.text_input("API Key", type="password")
    with col2:
        api_secret = st.text_input("API Secret", type="password")
    
    # Notification settings
    st.subheader("📢 Notifications")
    email_notifications = st.checkbox("Email Notifications")
    discord_webhook = st.text_input("Discord Webhook URL")
    
    # Advanced settings
    st.subheader("⚙️ Advanced Settings")
    update_frequency = st.slider("Update Frequency (seconds)", 1, 60, 5)
    max_daily_trades = st.number_input("Max Daily Trades", min_value=1, max_value=1000, value=50)
    
    if st.button("💾 Save Configuration"):
        st.success("Configuration saved successfully!")
    
    # Debug info
    with st.expander("🔧 Debug Information"):
        st.write("**Available Libraries:**")
        st.write(f"- Supabase: {'✅ Available' if SUPABASE_AVAILABLE else '❌ Not Available (using HTTP fallback)'}")
        st.write(f"- Plotly: {'✅ Available' if PLOTLY_AVAILABLE else '❌ Not Available (using Streamlit charts)'}")
        
        if st.session_state.supabase_connected:
            st.write("**Connection Details:**")
            st.write(f"- URL: {st.session_state.supabase_connector.url}")
            st.write(f"- Connected: {st.session_state.supabase_connector.connected}")
            st.write(f"- Client Type: {'Official Supabase' if SUPABASE_AVAILABLE else 'HTTP Client'}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        AutoTrader Pro v1.0 | Built with Streamlit | ⚠️ Use at your own risk - Trading involves substantial risk
    </div>
    """,
    unsafe_allow_html=True
)

# Auto-refresh for live data (when trading is active)
if st.session_state.trading_active:
    time.sleep(1)
    st.rerun()
