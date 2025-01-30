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
        
        # Estimate starting balance (max of first 5 positions)
        initial_balance = (df.head(5)['qty'] * df.head(5)['buyPrice']).max()
        
        # Daily performance analysis
        daily = df.groupby('soldDate').agg(
            daily_pnl=('pnl', 'sum'),
            trades=('pnl', 'count')
        ).reset_index()
        
        # Calculate qualification metrics
        daily['met_daily_target'] = daily['daily_pnl'] >= initial_balance * daily_threshold
        valid_days = daily[daily['met_daily_target']]
        total_profit = daily['daily_pnl'].sum()
        
        qualifies = (
            len(valid_days) >= min_days and 
            total_profit >= initial_balance * total_threshold
        )
        
        # Calculate potential company liability
        bonus_amount = total_profit * st.session_state.bonus_pct / 100 if qualifies else 0
        company_profit_share = total_profit * 0.10  # 10% withdrawal fee
        net_cost = bonus_amount - company_profit_share
        
        return {
            'trader': file.name.split('.')[0],
            'initial_balance': initial_balance,
            'qualifies': qualifies,
            'valid_days': len(valid_days),
            'total_profit': total_profit,
            'bonus_cost': bonus_amount,
            'net_cost': max(net_cost, 0),  # Can't have negative cost
            'company_profit': company_profit_share
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
        total_risk = df['bonus_cost'].sum()
        total_profit_share = df['company_profit'].sum()
        net_company_cost = total_risk - total_profit_share
        
        # Key metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Qualifying Traders", f"{df['qualifies'].sum()}/{len(df)}")
        col2.metric("Total Bonus Risk", f"${total_risk:,.0f}")
        col3.metric("Net Company Cost", f"${net_company_cost:,.0f}", 
                   delta_color="inverse" if net_company_cost > 0 else "normal")
        
        # Risk distribution analysis
        st.subheader("Risk Distribution Across Account Sizes")
        fig = px.scatter(df[df['qualifies']], 
                        x='initial_balance', y='bonus_cost',
                        color='valid_days', size='total_profit',
                        labels={'initial_balance': 'Account Size',
                                'bonus_cost': 'Potential Bonus Cost'},
                        hover_data=['trader'])
        st.plotly_chart(fig, use_container_width=True)
        
        # Cost breakdown
        st.subheader("Cost Composition")
        cost_df = pd.DataFrame({
            'Type': ['Total Bonuses', 'Company Profit Share', 'Net Cost'],
            'Amount': [total_risk, total_profit_share, net_company_cost]
        })
        fig = px.bar(cost_df, x='Type', y='Amount', text='Amount',
                    labels={'Amount': 'USD'})
        fig.update_traces(texttemplate='$%{y:,.0f}')
        st.plotly_chart(fig, use_container_width=True)
        
        # Downloadable results
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Full Analysis",
            data=csv,
            file_name='bonus_risk_analysis.csv',
            mime='text/csv'
        )
