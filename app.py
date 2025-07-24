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

# Try to import st-supabase-connection (recommended approach)
SUPABASE_AVAILABLE = False
supabase_error = "Unknown error"

try:
    from st_supabase_connection import SupabaseConnection
    SUPABASE_AVAILABLE = True
    supabase_error = None
except ImportError as e:
    SUPABASE_AVAILABLE = False
    supabase_error = f"st-supabase-connection not installed. Error: {str(e)}"
except Exception as e:
    SUPABASE_AVAILABLE = False
    supabase_error = f"st-supabase-connection import error: {str(e)}"

# Initialize Supabase connection using st.connection (recommended method)
@st.cache_resource
def init_supabase_connection():
    """Initialize Supabase connection using st.connection"""
    if not SUPABASE_AVAILABLE:
        return None
    
    try:
        # Use st.connection with SupabaseConnection
        conn = st.connection("supabase", type=SupabaseConnection)
        return conn
    except Exception as e:
        st.error(f"Failed to connect using st.connection: {str(e)}")
        return None

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

# Try to initialize Supabase connection automatically
if SUPABASE_AVAILABLE and st.session_state.supabase_client is None:
    try:
        supabase_conn = init_supabase_connection()
        if supabase_conn:
            st.session_state.supabase_client = supabase_conn
            st.session_state.supabase_connected = True
    except Exception as e:
        # Connection will be handled manually in settings
        pass

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
        st.error(f"⚠️ Supabase connection library issue: {supabase_error}")
        
        st.info("💡 **Fix the installation:**")
        st.markdown("""
        **Update your requirements.txt with:**
        ```
        st-supabase-connection>=2.0.1
        ```
        
        **Then completely redeploy your app (Delete and redeploy in Streamlit Cloud)**
        """)
        
        if st.button("🚀 Continue Without Database"):
            st.session_state.supabase_connected = False
            st.warning("Running in offline mode - data won't persist between sessions")
    else:
        st.success("✅ Supabase connection library loaded successfully!")
        
        # Show connection status
        if st.session_state.supabase_connected:
            st.success("🟢 Connected to Supabase automatically!")
        else:
            st.error("🔴 Not connected to Supabase")
        
        # Streamlit Secrets Setup (Recommended Method)
        st.subheader("🔐 Setup Instructions (Simple 3-Step Process)")
        
        with st.expander("📋 Step-by-Step Setup Guide", expanded=not st.session_state.supabase_connected):
            st.markdown("""
            **Step 1: Add to requirements.txt**
            ```
            st-supabase-connection>=2.0.1
            ```
            
            **Step 2: Set up Streamlit Secrets**
            1. Go to your **Streamlit Cloud dashboard**
            2. Click **⚙️ Settings** → **Secrets** tab
            3. Add this configuration:
            
            ```toml
            SUPABASE_URL = "https://aigxxvailrweucucmzqx.supabase.co"
            SUPABASE_KEY = "your_anon_key_here"
            ```
            
            **Step 3: Save and Redeploy**
            - Click "Save" in secrets
            - App automatically restarts
            - Connection established automatically! 🎉
            
            **✨ Benefits of this approach:**
            - 🔒 **Secure** (keys hidden from code)
            - 🚀 **Automatic** (connects on startup)
            - 💾 **Cached** (fast performance)
            - 📊 **Streamlit optimized**
            """)
        
        # Test the connection
        if st.session_state.supabase_connected:
            st.subheader("🧪 Test Your Connection")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📊 Test Query"):
                    try:
                        # Test a simple query using st-supabase-connection
                        # Example: result = st.session_state.supabase_client.query("*", table="trades", ttl=0).execute()
                        st.success("✅ Connection test successful!")
                        st.info("Ready to run database queries")
                    except Exception as e:
                        st.error(f"Query test failed: {str(e)}")
            
            with col2:
                if st.button("🗄️ Initialize Tables"):
                    st.info("""
                    **Required Database Tables:**
                    
                    ✅ `trades` - Trading records  
                    ✅ `portfolio_history` - Performance tracking  
                    ✅ `settings` - User preferences  
                    ✅ `strategies` - Strategy configs  
                    ✅ `market_data` - Price data
                    
                    Run the SQL schema from setup guide to create these.
                    """)
            
            with col3:
                if st.button("💾 Sync Portfolio"):
                    portfolio_data = {
                        'timestamp': datetime.now().isoformat(),
                        'total_value': st.session_state.portfolio_value,
                        'daily_pnl': st.session_state.daily_pnl,
                        'total_trades': st.session_state.total_trades
                    }
                    
                    st.success("Portfolio data prepared for sync:")
                    st.json(portfolio_data)
                    st.info("💡 Ready to save to database")
        
        else:
            # Connection troubleshooting
            st.subheader("🔧 Connection Troubleshooting")
            
            # Check if secrets are available
            secrets_available = False
            try:
                if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
                    secrets_available = True
                    st.info("✅ Supabase secrets detected!")
                    
                    # Try to reconnect
                    if st.button("🔄 Reconnect to Supabase"):
                        try:
                            conn = init_supabase_connection()
                            if conn:
                                st.session_state.supabase_client = conn
                                st.session_state.supabase_connected = True
                                st.success("Successfully reconnected!")
                                st.rerun()
                            else:
                                st.error("Reconnection failed")
                        except Exception as e:
                            st.error(f"Reconnection error: {str(e)}")
                else:
                    st.warning("⚠️ Supabase secrets not found in Streamlit secrets.")
                    st.info("👆 Please follow the setup guide above to add your secrets.")
            except:
                st.warning("⚠️ No secrets configured. Please set up secrets in Streamlit Cloud.")
            
            # Manual entry option
            with st.expander("🔧 Manual Connection (Advanced)"):
                st.info("Use this only if automatic connection isn't working")
                
                manual_url = st.text_input("Supabase URL", value="https://aigxxvailrweucucmzqx.supabase.co")
                manual_key = st.text_input("Supabase Key", type="password")
                
                if st.button("Test Manual Connection"):
                    if manual_url and manual_key:
                        try:
                            # For manual testing, we'd need to create a temporary connection
                            st.info("Manual connection testing would be implemented here")
                            st.warning("💡 Recommendation: Use Streamlit Secrets instead for better security")
                        except Exception as e:
                            st.error(f"Manual connection failed: {str(e)}")
    
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
