import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px

# Configure page
st.set_page_config(page_title="Trading Incentive Risk Analysis", layout="wide")
st.title("Prop Firm Incentive Program Risk Analyzer")

def clean_data(df):
    """Clean and preprocess raw trade data"""
    # Clean PnL column
    df['pnl'] = df['pnl'].str.replace('[$,()]', '', regex=True).astype(float)
    
    # Convert timestamps
    df['boughtTimestamp'] = pd.to_datetime(df['boughtTimestamp'], format='%m/%d/%Y %H:%M:%S')
    df['soldTimestamp'] = pd.to_datetime(df['soldTimestamp'], format='%m/%d/%Y %H:%M:%S')
    
    # Calculate trade duration in minutes
    df['duration_min'] = (df['soldTimestamp'] - df['boughtTimestamp']).dt.total_seconds() / 60
    
    # Calculate position size
    df['position_size'] = df['qty'] * df['buyPrice']
    
    return df

def calculate_daily_metrics(df):
    """Calculate daily risk metrics"""
    daily = df.resample('D', on='soldTimestamp').agg({
        'pnl': 'sum',
        'position_size': 'max',
        'duration_min': 'mean'
    }).reset_index()
    
    # Calculate daily risk metrics
    daily['daily_loss'] = daily['pnl'].apply(lambda x: abs(x) if x < 0 else 0)
    daily['drawdown'] = daily['pnl'].cumsum().sub(daily['pnl'].cumsum().cummax()).abs()
    
    return daily

def analyze_risk(daily_df, initial_capital):
    """Calculate key risk metrics"""
    max_drawdown = daily_df['drawdown'].max()
    worst_day = daily_df['daily_loss'].max()
    avg_position_size = daily_df['position_size'].mean()
    
    return {
        'max_drawdown_pct': (max_drawdown / initial_capital) * 100,
        'worst_day_loss_pct': (worst_day / initial_capital) * 100,
        'leverage_ratio': (daily_df['position_size'].max() / initial_capital),
        'avg_trade_duration': daily_df['duration_min'].mean(),
        'profit_factor': daily_df['pnl'][daily_df['pnl'] > 0].sum() / abs(daily_df['pnl'][daily_df['pnl'] < 0].sum())
    }

# File upload
uploaded_files = st.file_uploader("Upload trader CSV files", 
                                 type=['csv'],
                                 accept_multiple_files=True)

if uploaded_files:
    all_trades = []
    for file in uploaded_files:
        try:
            df = pd.read_csv(file)
            cleaned = clean_data(df)
            all_trades.append(cleaned)
        except Exception as e:
            st.error(f"Error processing {file.name}: {str(e)}")
    
    if all_trades:
        full_df = pd.concat(all_trades)
        daily_metrics = calculate_daily_metrics(full_df)
        
        # Risk analysis
        initial_capital = st.number_input("Firm Total Capital ($)", value=1_000_000)
        risk_metrics = analyze_risk(daily_metrics, initial_capital)
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Max Drawdown", f"{risk_metrics['max_drawdown_pct']:.2f}%")
            st.metric("Avg Trade Duration", f"{risk_metrics['avg_trade_duration']:.1f} mins")
        with col2:
            st.metric("Worst Daily Loss", f"{risk_metrics['worst_day_loss_pct']:.2f}%")
            st.metric("Profit Factor", f"{risk_metrics['profit_factor']:.2f}x")
        with col3:
            st.metric("Max Leverage", f"{risk_metrics['leverage_ratio']:.1f}x")
        
        # Visualizations
        st.subheader("Daily Performance Analysis")
        fig = px.line(daily_metrics, x='soldTimestamp', y='pnl', 
                     title="Daily P&L Trend")
        st.plotly_chart(fig, use_container_width=True)
        
        fig = px.histogram(full_df, x='duration_min', 
                          title="Trade Duration Distribution",
                          nbins=50)
        st.plotly_chart(fig, use_container_width=True)
