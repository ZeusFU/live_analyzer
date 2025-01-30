import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import re

# Function to extract root symbol (e.g., NQZ5 → NQ)
def extract_root_symbol(symbol):
    return re.sub(r'\d+[A-Za-z]*$', '', symbol)

# Function to clean and convert pnl values
def clean_pnl(pnl):
    if isinstance(pnl, str):
        # Remove $ and commas
        pnl = pnl.replace('$', '').replace(',', '')
        # Check if the value is in parentheses (negative)
        if '(' in pnl and ')' in pnl:
            pnl = pnl.replace('(', '').replace(')', '')
            return -float(pnl)
        return float(pnl)
    return pnl

# Function to analyze a single trader's CSV
def analyze_trader(trades):
    # Extract root symbol
    trades['Root Symbol'] = trades['symbol'].apply(extract_root_symbol)
    
    # Clean pnl column
    trades['pnl'] = trades['pnl'].apply(clean_pnl)
    
    # Calculate account age (in days)
    first_trade_date = trades['boughtTimestamp'].min()
    last_trade_date = trades['boughtTimestamp'].max()
    account_age = (last_trade_date - first_trade_date).days
    
    # Calculate metrics
    metrics = {
        'Avg Loss per Asset': trades[trades['pnl'] < 0].groupby('Root Symbol')['pnl'].mean().to_dict(),
        'Avg Win per Asset': trades[trades['pnl'] > 0].groupby('Root Symbol')['pnl'].mean().to_dict(),
        'Avg Size per Trade per Asset': trades.groupby('Root Symbol')['qty'].mean().to_dict(),
        'Winning Days': trades[trades['pnl'] > 0].groupby(trades['boughtTimestamp'].dt.date)['pnl'].sum().mean(),
        'Losing Days': trades[trades['pnl'] < 0].groupby(trades['boughtTimestamp'].dt.date)['pnl'].sum().mean(),
        'Account Age': account_age
    }
    return metrics

# Streamlit App
def main():
    st.title("Multi-Trader Performance Analyzer")
    st.markdown("Upload CSV files for multiple traders to analyze performance by asset.")

    # File upload (multiple files)
    uploaded_files = st.file_uploader("Upload CSV files", type=["csv"], accept_multiple_files=True)
    if uploaded_files:
        all_metrics = []
        for uploaded_file in uploaded_files:
            try:
                # Load CSV
                trades = pd.read_csv(uploaded_file, parse_dates=['boughtTimestamp', 'soldTimestamp'])
                
                # Analyze trader
                metrics = analyze_trader(trades)
                all_metrics.append(metrics)
            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {str(e)}")
        
        if all_metrics:
            # Aggregate metrics across all traders
            aggregated = {
                'Avg Loss per Asset': {},
                'Avg Win per Asset': {},
                'Avg Size per Trade per Asset': {},
                'Avg Winning Days': np.mean([m['Winning Days'] for m in all_metrics if not np.isnan(m['Winning Days'])]),
                'Avg Losing Days': np.mean([m['Losing Days'] for m in all_metrics if not np.isnan(m['Losing Days'])]),
                'Avg Account Age': np.mean([m['Account Age'] for m in all_metrics])
            }
            
            # Combine metrics for each asset
            for metrics in all_metrics:
                for asset, loss in metrics['Avg Loss per Asset'].items():
                    if asset not in aggregated['Avg Loss per Asset']:
                        aggregated['Avg Loss per Asset'][asset] = []
                    aggregated['Avg Loss per Asset'][asset].append(loss)
                
                for asset, win in metrics['Avg Win per Asset'].items():
                    if asset not in aggregated['Avg Win per Asset']:
                        aggregated['Avg Win per Asset'][asset] = []
                    aggregated['Avg Win per Asset'][asset].append(win)
                
                for asset, size in metrics['Avg Size per Trade per Asset'].items():
                    if asset not in aggregated['Avg Size per Trade per Asset']:
                        aggregated['Avg Size per Trade per Asset'][asset] = []
                    aggregated['Avg Size per Trade per Asset'][asset].append(size)
            
            # Calculate averages for each asset
            for asset in aggregated['Avg Loss per Asset']:
                aggregated['Avg Loss per Asset'][asset] = np.mean(aggregated['Avg Loss per Asset'][asset])
            for asset in aggregated['Avg Win per Asset']:
                aggregated['Avg Win per Asset'][asset] = np.mean(aggregated['Avg Win per Asset'][asset])
            for asset in aggregated['Avg Size per Trade per Asset']:
                aggregated['Avg Size per Trade per Asset'][asset] = np.mean(aggregated['Avg Size per Trade per Asset'][asset])
            
            # Display results
            st.header("Aggregated Analysis")
            
            # Avg Loss per Asset
            st.subheader("Average Loss per Asset")
            for asset, loss in aggregated['Avg Loss per Asset'].items():
                st.write(f"**{asset}**: ${loss:.2f}")
            
            # Avg Win per Asset
            st.subheader("Average Win per Asset")
            for asset, win in aggregated['Avg Win per Asset'].items():
                st.write(f"**{asset}**: ${win:.2f}")
            
            # Avg Size per Trade per Asset
            st.subheader("Average Size per Trade per Asset")
            for asset, size in aggregated['Avg Size per Trade per Asset'].items():
                st.write(f"**{asset}**: {size:.2f} contracts")
            
            # Avg Winning Days and Losing Days
            st.subheader("Average Winning and Losing Days")
            st.write(f"**Avg Winning Days**: ${aggregated['Avg Winning Days']:.2f}")
            st.write(f"**Avg Losing Days**: ${aggregated['Avg Losing Days']:.2f}")
            
            # Avg Account Age
            st.subheader("Average Account Age")
            st.write(f"**Avg Account Age**: {aggregated['Avg Account Age']:.2f} days")

# Run the app
if __name__ == "__main__":
    main()
