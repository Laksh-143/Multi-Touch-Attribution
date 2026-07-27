"""
02_run_attribution_models.py
Implements Phase 2 (Attribution Modeling) and Phase 3 (Budget & Scenario Layer).

Models:
- Heuristic Baselines: First-Click, Last-Click, Linear, Time-Decay
- Analytical Markov Chain: Absorbing Markov chain closed-form solution via (I - Q)^-1,
  routing removed channel edges to Null (drop-off)
- Exact Full-Dataset Shapley: Vectorized coalition enumeration across all visitors

Budget Layer:
- Spend figures are ILLUSTRATIVE ESTIMATES, not sourced from a published benchmark.
  We assume plausible CPC values by channel type to demonstrate the financial reconciliation
  methodology. If real spend data were available, it would replace these placeholders.
- AOV is computed directly from real revenue data in fact_conversions.csv, not assumed.
"""

import os
import re
import math
from itertools import combinations
from collections import defaultdict
import numpy as np
import pandas as pd

def run_models():
    print("Loading warehouse exports...")
    df_paths = pd.read_csv('data/exports/journey_paths.csv')
    df_trans = pd.read_csv('data/exports/fact_channel_transitions.csv')
    df_dim = pd.read_csv('data/exports/dim_channel.csv')
    df_conv = pd.read_csv('data/exports/fact_conversions.csv')
    
    all_channels = sorted(df_dim['channel_grouping'].tolist())
    n_channels = len(all_channels)
    
    # ---------------------------------------------------------
    # COMPUTE REAL AOV FROM ACTUAL REVENUE DATA (Fix #6)
    # ---------------------------------------------------------
    total_transactions = df_conv['transactions'].sum()
    total_revenue = df_conv['revenue'].sum()
    real_aov = total_revenue / total_transactions if total_transactions > 0 else 0
    print(f"Real AOV (from fact_conversions): ${real_aov:.2f}")
    print(f"  Total transactions: {total_transactions:,}")
    print(f"  Total revenue: ${total_revenue:,.2f}")
    
    # Isolate converting journeys for attribution distribution
    df_conv_paths = df_paths[df_paths['converted'] == 1].copy()
    total_conversions = len(df_conv_paths)
    print(f"Total Visitors: {len(df_paths):,} | Converting Visitors: {total_conversions:,}\n")
    
    # ---------------------------------------------------------
    # 1. HEURISTIC BASELINES
    # ---------------------------------------------------------
    print("Computing Heuristic Baselines (First-Click, Last-Click, Linear, Time-Decay)...")
    heuristics = {model: {ch: 0.0 for ch in all_channels} for model in ['First_Click', 'Last_Click', 'Linear', 'Time_Decay']}
    
    for _, row in df_conv_paths.iterrows():
        path = row['touchpoint_path'].split(' > ')
        n = len(path)
        
        heuristics['First_Click'][path[0]] += 1.0
        heuristics['Last_Click'][path[-1]] += 1.0
        
        credit = 1.0 / n
        for ch in path:
            heuristics['Linear'][ch] += credit
            
        weights = [2 ** ((i - n + 1) / 7.0) for i in range(n)]
        total_weight = sum(weights)
        for i, ch in enumerate(path):
            heuristics['Time_Decay'][ch] += weights[i] / total_weight
            
    df_models = pd.DataFrame(heuristics).fillna(0).round(2)
    df_models.index.name = 'Channel'
    
    # ---------------------------------------------------------
    # 2. ANALYTICAL MARKOV CHAIN (CLOSED-FORM)
    # ---------------------------------------------------------
    print("Computing Analytical Markov Chain via (I - Q)^-1 matrix inversion...")
    transient_states = ['Start'] + all_channels
    absorbing_states = ['Conversion', 'Null']
    all_states = transient_states + absorbing_states
    
    trans_matrix = pd.DataFrame(0.0, index=all_states, columns=all_states)
    for _, row in df_trans.iterrows():
        orig = row['from_channel']
        dest = row['to_channel']
        if orig in all_states and dest in all_states:
            trans_matrix.loc[orig, dest] = row['transition_count']
            
    row_sums = trans_matrix.sum(axis=1)
    for state in transient_states:
        if row_sums[state] > 0:
            trans_matrix.loc[state] /= row_sums[state]
    trans_matrix.loc['Conversion', 'Conversion'] = 1.0
    trans_matrix.loc['Null', 'Null'] = 1.0
    
    def get_absorption_prob(t_matrix):
        """Returns absorption probability from 'Start' to 'Conversion' using N = (I - Q)^-1."""
        Q = t_matrix.loc[transient_states, transient_states].values
        R = t_matrix.loc[transient_states, absorbing_states].values
        I = np.eye(len(transient_states))
        try:
            N = np.linalg.inv(I - Q)
            B = np.dot(N, R)
            start_idx = transient_states.index('Start')
            return B[start_idx, 0]
        except np.linalg.LinAlgError:
            return 0.0

    baseline_prob = get_absorption_prob(trans_matrix)
    print(f"  Baseline absorption probability (Start -> Conversion): {baseline_prob:.6f}")
    
    removal_effects = {}
    for ch in all_channels:
        mod_matrix = trans_matrix.copy()
        for state in transient_states:
            if state == ch:
                mod_matrix.loc[state] = 0.0
                mod_matrix.loc[state, 'Null'] = 1.0
            else:
                prob_to_ch = mod_matrix.loc[state, ch]
                mod_matrix.loc[state, ch] = 0.0
                mod_matrix.loc[state, 'Null'] += prob_to_ch
        
        rem_prob = get_absorption_prob(mod_matrix)
        effect = (baseline_prob - rem_prob) / baseline_prob if baseline_prob > 0 else 0.0
        removal_effects[ch] = max(effect, 0.0)
        
    total_effect = sum(removal_effects.values())
    markov_attr = {ch: (eff / total_effect) * total_conversions if total_effect > 0 else 0 for ch, eff in removal_effects.items()}
    df_models['Markov'] = pd.Series(markov_attr).round(2)
    
    # ---------------------------------------------------------
    # 3. EXACT FULL-DATASET SHAPLEY VALUE
    # ---------------------------------------------------------
    print("Computing Exact Full-Dataset Shapley Value...")
    bool_dict = {}
    for ch in all_channels:
        pattern = r'(?:^| > )' + re.escape(ch) + r'(?:$| > )'
        bool_dict[ch] = df_paths['touchpoint_path'].str.contains(pattern, regex=True)
    
    df_bool = pd.DataFrame(bool_dict)
    df_bool['converted'] = df_paths['converted'].values
    
    print(f"  Enumerating 2^{n_channels} = {2**n_channels} coalitions...")
    coalition_conversions = {}
    
    for r in range(n_channels + 1):
        for subset in combinations(all_channels, r):
            if r == 0:
                coalition_conversions[frozenset()] = 0.0
                continue
            outside_channels = [ch for ch in all_channels if ch not in subset]
            if not outside_channels:
                mask = pd.Series(True, index=df_bool.index)
            else:
                mask = ~df_bool[outside_channels].any(axis=1)
            
            conv_vis = df_bool.loc[mask, 'converted'].sum()
            coalition_conversions[frozenset(subset)] = float(conv_vis)

    shapley_vals = {ch: 0.0 for ch in all_channels}
    for ch in all_channels:
        others = [c for c in all_channels if c != ch]
        for r in range(len(others) + 1):
            for S in combinations(others, r):
                S_set = frozenset(S)
                S_with_ch = frozenset(S) | {ch}
                marginal = coalition_conversions[S_with_ch] - coalition_conversions[S_set]
                weight = (math.factorial(len(S)) * math.factorial(n_channels - len(S) - 1)) / math.factorial(n_channels)
                shapley_vals[ch] += weight * marginal
                
    df_models['Shapley'] = pd.Series(shapley_vals).round(2)
    
    df_models = df_models.reset_index()
    df_models = df_models.sort_values('Last_Click', ascending=False)
    print("\n=== ATTRIBUTION MODEL COMPARISON ===")
    print(df_models.to_string(index=False))
    df_models.to_csv('data/exports/model_comparison.csv', index=False)
    print("Saved: data/exports/model_comparison.csv\n")
    
    # ---------------------------------------------------------
    # 4. BUDGET LAYER (ILLUSTRATIVE CPC ESTIMATES)
    # ---------------------------------------------------------
    print("Computing illustrative financial reconciliation layer...")
    print("DISCLOSURE: The figures below are illustrative estimates, not sourced from a")
    print("specific published benchmark. GA4 sample data does not include actual ad spend.")
    print("The CPC values are plausible order-of-magnitude assumptions by channel type,")
    print("used solely to demonstrate the reconciliation methodology.\n")
    
    # These are illustrative CPC assumptions, NOT cited from a specific report.
    # In a production environment, real spend data would replace these placeholders.
    illustrative_cpc = {
        'Paid Search': 2.50,
        'Display': 0.60,
        'Social': 1.20,
        'Affiliates': 1.50,
        'Referral': 0.00,   # Earned / organic
        'Organic Search': 0.00,
        'Direct': 0.00,
        '(Other)': 0.00
    }
    
    session_counts = df_paths['touchpoint_path'].str.split(' > ').explode().value_counts()
    
    financial_rows = []
    total_spend = 0.0
    for ch in all_channels:
        clicks = session_counts.get(ch, 0)
        cpc = illustrative_cpc.get(ch, 0.0)
        spend = round(clicks * cpc, 2)
        total_spend += spend
        
        last_conv = df_models.loc[df_models['Channel'] == ch, 'Last_Click'].values[0]
        shap_conv = df_models.loc[df_models['Channel'] == ch, 'Shapley'].values[0]
        
        last_cpa = round(spend / last_conv, 2) if last_conv > 0 and spend > 0 else None
        shap_cpa = round(spend / shap_conv, 2) if shap_conv > 0 and spend > 0 else None
        
        financial_rows.append({
            'Channel': ch,
            'Session_Touchpoints': clicks,
            'Illustrative_CPC': cpc,
            'Illustrative_Spend': spend,
            'Last_Click_Conv': last_conv,
            'Shapley_Conv': shap_conv,
            'Last_Click_CPA': last_cpa,
            'Shapley_CPA': shap_cpa
        })
        
    df_fin = pd.DataFrame(financial_rows)
    print("=== FINANCIAL RECONCILIATION (ILLUSTRATIVE SPEND) ===")
    print(df_fin.to_string(index=False))
    df_fin.to_csv('data/exports/financial_reconciliation.csv', index=False)
    print(f"\nTotal Illustrative Spend: ${total_spend:,.2f}")
    print(f"Real AOV (from data): ${real_aov:.2f}")
    print("Saved: data/exports/financial_reconciliation.csv\n")
    
    # ---------------------------------------------------------
    # 5. BUDGET OPTIMIZER (SHAPLEY-PROPORTIONAL)
    # ---------------------------------------------------------
    print("Running Shapley-Proportional Budget Optimizer...")
    paid_channels = [ch for ch, cpc in illustrative_cpc.items() if cpc > 0]
    paid_spend = sum(df_fin.loc[df_fin['Channel'].isin(paid_channels), 'Illustrative_Spend'])
    paid_shap_sum = sum(df_fin.loc[df_fin['Channel'].isin(paid_channels), 'Shapley_Conv'])
    
    opt_rows = []
    for ch in paid_channels:
        curr_spend = df_fin.loc[df_fin['Channel'] == ch, 'Illustrative_Spend'].values[0]
        shap_conv = df_fin.loc[df_fin['Channel'] == ch, 'Shapley_Conv'].values[0]
        
        weight = (shap_conv / paid_shap_sum) if paid_shap_sum > 0 else (1.0 / len(paid_channels))
        opt_spend = round(paid_spend * weight, 2)
        delta = round(opt_spend - curr_spend, 2)
        
        opt_rows.append({
            'Channel': ch,
            'Current_Spend': curr_spend,
            'Optimal_Spend': opt_spend,
            'Spend_Delta': delta,
            'Shapley_Weight_Pct': round(weight * 100, 1)
        })
        
    df_opt = pd.DataFrame(opt_rows)
    print("\n=== BUDGET REALLOCATION RECOMMENDATION (ILLUSTRATIVE) ===")
    print("Constraint: Fixed total paid budget. Allocation proportional to Shapley contribution.")
    print(df_opt.to_string(index=False))
    df_opt.to_csv('data/exports/budget_optimizer.csv', index=False)
    print("Saved: data/exports/budget_optimizer.csv\n")
    
    # ---------------------------------------------------------
    # 6. WHAT-IF SCENARIO SIMULATOR (Uses real AOV)
    # ---------------------------------------------------------
    print("Running What-If Scenario Simulator...")
    print(f"Using real AOV: ${real_aov:.2f} (from SUM(revenue)/SUM(transactions))")
    
    scenarios = {
        'Paid Search': 0.70,  # Cut 30%
        'Display': 1.50,      # Increase 50%
        'Social': 0.50        # Cut 50%
    }
    
    sim_rows = []
    for ch, mult in scenarios.items():
        row = df_fin[df_fin['Channel'] == ch]
        if len(row) == 0:
            continue
        
        curr_spend = row['Illustrative_Spend'].values[0]
        new_spend = curr_spend * mult
        spend_change = new_spend - curr_spend
        
        shap_conv = row['Shapley_Conv'].values[0]
        efficiency = (shap_conv / curr_spend) if curr_spend > 0 else 0.0
        
        proj_conv = efficiency * new_spend
        conv_change = proj_conv - shap_conv
        rev_impact = conv_change * real_aov
        
        sim_rows.append({
            'Channel': ch,
            'Scenario': f"{mult:.0%} of current",
            'Current_Spend': round(curr_spend, 2),
            'Proposed_Spend': round(new_spend, 2),
            'Spend_Delta': round(spend_change, 2),
            'Current_Shapley_Conv': round(shap_conv, 2),
            'Projected_Conv': round(proj_conv, 2),
            'Conv_Delta': round(conv_change, 2),
            'Revenue_Impact': round(rev_impact, 2)
        })
    
    df_sim = pd.DataFrame(sim_rows)
    print("\n=== WHAT-IF SCENARIOS (LINEAR SCALING, ILLUSTRATIVE SPEND) ===")
    print("NOTE: Linear scaling ignores diminishing returns — directional guidance only.")
    print(df_sim.to_string(index=False))
    df_sim.to_csv('data/exports/what_if_scenarios.csv', index=False)
    print("Saved: data/exports/what_if_scenarios.csv\n")

if __name__ == '__main__':
    run_models()
