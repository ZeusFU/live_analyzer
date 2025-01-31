import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Configure page
st.set_page_config(page_title="Bonus Risk Analyzer", layout="wide")
st.title("Incentive Program Risk Calculator")

def analyze_trader(file, min_days=7, daily_threshold=0.04, total_threshold=0.5):
    """Analyze individual trader CSV and calculate bonus risk"""
    try:
        df = pd.read_csv(file)
        
        # Clean PnL and calculate metrics
        df['pnl'] = df['pnl'].str.replace('[$,()]', '', regex=True).astype(float)
        df['soldDate'] = pd.to_datetime(df['soldTimestamp']).dt.date
        
        # Estimate starting balance (max position size)
        df['position_size'] = df['qty'] * df['buyPrice']
        initial_balance = df['position_size'].max()
        
        # Daily performance analysis
        daily = df.groupby('soldDate').agg(
            daily_pnl=('pnl', 'sum'),
            trades=('pnl', 'count')
        ).reset_index()
        
        # Calculate qualification metrics
        required_daily_profit = initial_balance * daily_threshold
        daily['met_target'] = daily['daily_pnl'] >= required_daily_profit
        valid_days = daily[daily['met_target']]
        
        total_profit = daily['daily_pnl'].sum()
        qualifies = (
            len(valid_days) >= min_days and 
            total_profit >= initial_balance * total_threshold
        )
        
        # Calculate company exposure
        if qualifies:
            bonus_amount = total_profit * (st.session_state.bonus_pct / 100)
            company_profit_share = total_profit * 0.10  # 10% of total profits
            net_cost = bonus_amount - company_profit_share
        else:
            bonus_amount = 0
            company_profit_share = 0
            net_cost = 0
            
        return {
            'trader': file.name.split('.')[0],
            'initial_balance': initial_balance,
            'qualifies': qualifies,
            'total_profit': total_profit,
            'bonus_cost': bonus_amount,
            'company_profit': company_profit_share,
            'net_cost': net_cost,
            'roi': (company_profit_share - bonus_amount) / initial_balance * 100
        }
    
    except Exception as e:
        st.error(f"Error analyzing {file.name}: {str(e)}")
        return None

# File upload section
uploaded_files = st.file_uploader("Upload trader CSVs", 
                                 type=['csv'],
                                 accept_multiple_files=True)

# Configuration sidebar
with st.sidebar:
    st.header("Program Parameters")
    st.session_state.bonus_pct = st.slider("Bonus Percentage", 5, 50, 20)
    min_profit_days = st.slider("Minimum Profitable Days", 3, 20, 7)
    daily_profit_target = st.slider("Daily Profit Target (%)", 1.0, 10.0, 4.0) / 100
    total_profit_target = st.slider("Total Profit Target (%)", 10, 200, 50) / 100

if uploaded_files:
    results = []
    progress_bar = st.progress(0)
    
    # Process all files
    for i, file in enumerate(uploaded_files):
        result = analyze_trader(file, min_profit_days, daily_profit_target, total_profit_target)
        if result:
            results.append(result)
        progress_bar.progress((i+1)/len(uploaded_files))
    
    if results:
        df = pd.DataFrame(results)
        qualified = df[df['qualifies']]
        
        # Key metrics
        total_bonus = qualified['bonus_cost'].sum()
        total_profit_share = qualified['company_profit'].sum()
        net_exposure = total_bonus - total_profit_share
        avg_roi = qualified['roi'].mean()

        # Display metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Qualifying Traders", f"{len(qualified)}/{len(df)}")
        col2.metric("Total Bonus Liability", f"${total_bonus:,.0f}")
        col3.metric("Net Company Exposure", f"${net_exposure:,.0f}", 
                   delta_color="inverse" if net_exposure > 0 else "normal",
                   help="Negative values = Net Profit for Company")

        # Risk analysis
        st.subheader("Exposure Distribution")
        fig = px.histogram(qualified, x='net_cost', 
                          nbins=20,
                          labels={'net_cost': 'Net Cost per Trader'},
                          title="Distribution of Net Company Exposure per Qualifying Trader")
        st.plotly_chart(fig, use_container_width=True)

        # ROI analysis
        st.subheader("Return on Investment")
        fig = px.scatter(qualified, x='initial_balance', y='roi',
                        color='net_cost',
                        size='total_profit',
                        labels={'initial_balance': 'Account Size',
                                'roi': 'ROI (%)'},
                        title="Company ROI by Account Size")
        st.plotly_chart(fig, use_container_width=True)

        # Download results
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download Full Analysis",
            data=csv,
            file_name='risk_analysis.csv',
            mime='text/csv'
        )
