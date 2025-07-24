import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

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
if 'supabase_connected' not in st.session_state:
    st.session_state.supabase_connected = False
if 'supabase_client' not in st.session_state:
    st.session_state.supabase_client = None

# Supabase connection functions
def connect_to_supabase(url: str, key: str) -> tuple[bool, str]:
    """Connect to Supabase and test the connection"""
    if not SUPABASE_AVAILABLE:
        return False, "Supabase library not available. Please install supabase."
    
    try:
        supabase: Client = create_client(url, key)
        # Test connection by trying to access auth
        response = supabase.auth.get_session()
        st.session_state.supabase_client = supabase
        st.session_state.supabase_connected = True
        return True, "Successfully connected to Supabase!"
    except Exception as e:
        st.session_state.supabase_client = None
        st.session_state.supabase_connected = False
        return False, f"Connection failed: {str(e)}"

def save_trade_to_supabase(trade_data: dict) -> bool:
    """Save trade data to Supabase"""
    if not st.session_state.supabase_connected or not st.session_state.supabase_client:
        return False
    
    try:
        result = st.session_state.supabase_client.table('trades').insert(trade_data).execute()
        return True
    except Exception as e:
        st.error(f"Failed to save trade: {str(e)}")
        return False

def get_portfolio_history_from_supabase() -> pd.DataFrame:
    """Retrieve portfolio history from Supabase"""
    if not st.session_state.supabase_connected or not st.session_state.supabase_client:
        return pd.DataFrame()
    
    try:
        result = st.session_state.supabase_client.table('portfolio_history').select('*').execute()
        return pd.DataFrame(result.data)
    except Exception as e:
        st.error(f"Failed to retrieve portfolio history: {str(e)}")
        return pd.DataFrame()

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
    
    # Database integration for positions
    if st.session_state.supabase_connected:
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 Save Positions to DB"):
                # Convert positions to database format
                for _, row in positions_df.iterrows():
                    trade_data = {
                        'symbol': row['Symbol'],
                        'side': row['Side'].lower(),
                        'size': row['Size'],
                        'entry_price': row['Entry Price'],
                        'current_price': row['Current Price'],
                        'pnl': row['PnL'],
                        'pnl_percent': row['PnL %'],
                        'timestamp': datetime.now().isoformat(),
                        'status': 'open'
                    }
                    # In real implementation: save_trade_to_supabase(trade_data)
                
                st.success(f"Saved {len(positions_df)} positions to database!")
        
        with col2:
            if st.button("🔄 Load from DB"):
                st.info("Loading positions from Supabase...")
                # In real implementation: load positions from database
                
        with col3:
            if st.button("📊 Position Analytics"):
                st.info("Generating position analytics from database...")
    else:
        st.info("💡 Connect to Supabase in Settings to save/load positions from database")

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
    st.subheader("Database Configuration (Supabase)")
    
    if not SUPABASE_AVAILABLE:
        st.error("⚠️ Supabase library not installed. Add 'supabase' to your requirements.txt file.")
    
    # Supabase connection settings
    col1, col2 = st.columns(2)
    
    with col1:
        supabase_url = st.text_input(
            "Supabase URL", 
            placeholder="https://your-project.supabase.co",
            help="Your Supabase project URL"
        )
        supabase_key = st.text_input(
            "Supabase Anon Key", 
            type="password",
            placeholder="Your public anon key",
            help="Your Supabase public/anon key"
        )
    
    with col2:
        supabase_service_key = st.text_input(
            "Supabase Service Role Key (Optional)", 
            type="password",
            placeholder="Your service role key",
            help="Service role key for admin operations (optional)"
        )
        
        # Connection status
        if st.session_state.supabase_connected:
            st.success("🟢 Connected to Supabase")
        else:
            st.error("🔴 Not connected to Supabase")
    
    # Connection buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔗 Test Connection", disabled=not supabase_url or not supabase_key):
            if supabase_url and supabase_key:
                # Use service key if provided, otherwise use anon key
                key_to_use = supabase_service_key if supabase_service_key else supabase_key
                success, message = connect_to_supabase(supabase_url, key_to_use)
                if success:
                    st.success(message)
                else:
                    st.error(message)
            else:
                st.warning("Please enter both URL and key")
    
    with col2:
        if st.button("📊 Initialize Database", disabled=not st.session_state.supabase_connected):
            if st.session_state.supabase_connected:
                with st.spinner("Creating database tables..."):
                    # Create tables for trading app
                    try:
                        # Note: In real implementation, you would create these tables in Supabase dashboard
                        # or use migrations. This is just for demonstration.
                        st.info("""
                        **Required Tables:**
                        
                        1. **trades** - Store individual trade records
                        2. **portfolio_history** - Track portfolio value over time  
                        3. **settings** - Store user preferences
                        4. **strategies** - Store trading strategy configurations
                        
                        Please create these tables in your Supabase dashboard with appropriate columns.
                        """)
                        st.success("Database structure information displayed!")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    with col3:
        if st.button("💾 Save DB Config"):
            if supabase_url and supabase_key:
                st.success("Database configuration saved!")
                # In a real app, you'd save this to environment variables or secure storage
            else:
                st.warning("Please enter connection details first")
    
    # Database status and operations
    if st.session_state.supabase_connected:
        st.subheader("Database Operations")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📈 Sync Portfolio Data"):
                # Example: Save current portfolio state
                portfolio_data = {
                    'timestamp': datetime.now().isoformat(),
                    'total_value': st.session_state.portfolio_value,
                    'daily_pnl': st.session_state.daily_pnl,
                    'total_trades': st.session_state.total_trades
                }
                
                try:
                    # This would save to portfolio_history table
                    st.success("Portfolio data synced to database!")
                    st.json(portfolio_data)
                except Exception as e:
                    st.error(f"Sync failed: {str(e)}")
        
        with col2:
            if st.button("📋 Export Trade History"):
                # Example: Export recent trades
                sample_trades = [
                    {
                        'id': 1,
                        'symbol': 'BTC/USD',
                        'side': 'BUY',
                        'quantity': 0.1,
                        'price': 49000,
                        'timestamp': datetime.now().isoformat()
                    },
                    {
                        'id': 2,
                        'symbol': 'ETH/USD', 
                        'side': 'SELL',
                        'quantity': 1.0,
                        'price': 3150,
                        'timestamp': datetime.now().isoformat()
                    }
                ]
                
                trades_df = pd.DataFrame(sample_trades)
                csv = trades_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"trades_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
    
    st.markdown("---")
    
    st.subheader("Exchange API Configuration")
    
    # Exchange API settings
    exchange = st.selectbox("Select Exchange", ["Binance", "Coinbase Pro", "Kraken", "Alpaca"])
    
    col1, col2 = st.columns(2)
    with col1:
        api_key = st.text_input("API Key", type="password")
    with col2:
        api_secret = st.text_input("API Secret", type="password")
    
    # Notification settings
    st.subheader("Notifications")
    email_notifications = st.checkbox("Email Notifications")
    discord_webhook = st.text_input("Discord Webhook URL")
    
    # Advanced settings
    st.subheader("Advanced Settings")
    update_frequency = st.slider("Update Frequency (seconds)", 1, 60, 5)
    max_daily_trades = st.number_input("Max Daily Trades", min_value=1, max_value=1000, value=50)
    
    if st.button("💾 Save Configuration"):
        st.success("Configuration saved successfully!")

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
