import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
from io import StringIO
import scipy.stats as stats

# Configure page
st.set_page_config(page_title="Incentive Risk Simulator", layout="wide")
st.title("Prop Firm Incentive Program Risk Analyzer")

# Initialize session state
if 'sim_results' not in st.session_state:
    st.session_state.sim_results = None

def calculate_risk_impact(base_data, params):
    """Simulate risk impact of incentive parameters"""
    # Convert parameters to multipliers
    bonus_multiplier = params['bonus_pct'] / 15  # Baseline 15%
    profit_days_multiplier = params['profit_days'] / 7  # Baseline 7 days
    
    # Simulate behavioral changes
    simulated = base_data.copy()
    
    # Increased position sizing (risk-seeking behavior)
    simulated['position_size'] *= (1 + (bonus_multiplier * 0.2))
    
    # Reduced risk management (probability of breaching limits)
    simulated['daily_risk'] *= (1 + (profit_days_multiplier * 0.15))
    
    # Calculate new risk metrics
    return {
        'var_95': calculate_var(simulated),
        'expected_shortfall': calculate_es(simulated),
        'max_drawdown': simulated['pnl'].min(),
        'leverage_exposure': simulated['position_size'].max() / params['initial_capital'],
        'concentration_risk': calculate_concentration(simulated)
    }

def monte_carlo_simulation(base_data, params, n_simulations=1000):
    results = []
    for _ in range(n_simulations):
        # Generate random parameter variations
        sim_params = {
            'bonus_pct': max(5, params['bonus_pct'] * np.random.normal(1, 0.1)),
            'profit_days': max(3, params['profit_days'] * np.random.normal(1, 0.15)),
            'initial_capital': params['initial_capital']
        }
        
        results.append(calculate_risk_impact(base_data, sim_params))
    
    return pd.DataFrame(results)

def calculate_var(data):
    returns = data['pnl'] / data['position_size']
    return np.percentile(returns, 5)

def calculate_es(data):
    returns = data['pnl'] / data['position_size']
    var = calculate_var(data)
    return returns[returns <= var].mean()

def calculate_concentration(data):
    top_3 = data.groupby('symbol')['position_size'].sum().nlargest(3).sum()
    total = data['position_size'].sum()
    return top_3 / total

# File upload and base parameters
uploaded_files = st.file_uploader("Upload historical trade data", 
                                 type=['csv'],
                                 accept_multiple_files=True)

if uploaded_files:
    all_data = []
    for file in uploaded_files:
        content = StringIO(file.getvalue().decode('utf-8'))
        try:
            df = pd.read_csv(content)
            # Clean and transform data
            df['pnl'] = df['pnl'].str.replace('[$,()]', '', regex=True).astype(float)
            df['position_size'] = df['qty'] * df['buyPrice']
            all_data.append(df)
        except Exception as e:
            st.error(f"Error processing {file.name}: {str(e)}")
    
    base_data = pd.concat(all_data)
    
    # Risk simulation controls
    st.sidebar.header("Incentive Parameters")
    bonus_pct = st.sidebar.slider("Bonus Percentage", 5, 50, 15, 
                                help="% of profits given as bonus")
    profit_days = st.sidebar.slider("Required Profitable Days", 3, 20, 7,
                                  help="Minimum successful days to qualify")
    min_daily = st.sidebar.number_input("Minimum Daily Profit (%)", 1.0, 10.0, 4.0,
                                      help="Daily profit target percentage")
    max_drawdown = st.sidebar.number_input("Max Allowed Drawdown (%)", 5.0, 30.0, 15.0,
                                         help="Maximum acceptable daily loss")
    
    # Run simulation
    if st.sidebar.button("Simulate Risk Impact"):
        params = {
            'bonus_pct': bonus_pct,
            'profit_days': profit_days,
            'initial_capital': base_data['position_size'].sum()
        }
        
        st.session_state.sim_results = monte_carlo_simulation(base_data, params)

# Display results
if st.session_state.sim_results is not None:
    st.header("Risk Simulation Results")
    
    # Key metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("95% VaR", f"{st.session_state.sim_results['var_95'].mean()*100:.1f}%",
                help="Potential loss with 95% confidence")
    with col2:
        st.metric("Expected Shortfall", f"{st.session_state.sim_results['expected_shortfall'].mean()*100:.1f}%",
                help="Average loss beyond VaR threshold")
    with col3:
        st.metric("Max Drawdown Probability", 
                f"{(st.session_state.sim_results['max_drawdown'] < -max_drawdown/100).mean()*100:.1f}%",
                help="Probability of exceeding max allowed drawdown")
    
    # Visualizations
    fig = px.histogram(st.session_state.sim_results, 
                     x='leverage_exposure',
                     title="Leverage Exposure Distribution",
                     labels={'leverage_exposure': 'Capital at Risk'})
    st.plotly_chart(fig, use_container_width=True)
    
    fig = px.scatter_matrix(st.session_state.sim_results,
                          dimensions=['var_95', 'expected_shortfall', 'concentration_risk'],
                          title="Risk Factor Relationships")
    st.plotly_chart(fig, use_container_width=True)
    
    # Parameter sensitivity
    st.subheader("Parameter Impact Analysis")
    param_impact = st.session_state.sim_results.copy()
    param_impact['bonus_pct'] = [p['bonus_pct'] for p in st.session_state.sim_params]
    param_impact['profit_days'] = [p['profit_days'] for p in st.session_state.sim_params]
    
    fig = px.parallel_coordinates(param_impact,
                                color="var_95",
                                dimensions=['bonus_pct', 'profit_days', 'var_95', 'expected_shortfall'],
                                color_continuous_scale=px.colors.diverging.Tealrose)
    st.plotly_chart(fig, use_container_width=True)

    # Recommendations
    st.subheader("Risk Mitigation Suggestions")
    var_threshold = np.percentile(st.session_state.sim_results['var_95'], 95)
    if var_threshold > 0.08:
        st.error("⚠️ High Risk Threshold Breached - Consider Reducing Bonus Percentage")
    elif var_threshold > 0.05:
        st.warning("⚠️ Moderate Risk Levels - Suggest Adding Drawdown Limits")
    else:
        st.success("✅ Current Parameters Within Safe Risk Bounds")
