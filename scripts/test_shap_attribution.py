"""
Verify SHAP TreeExplainer on Frozen Isolation Forest Model
"""
import joblib
import numpy as np
import pandas as pd
import shap

def test_shap_on_frozen_if():
    print("Loading frozen model and config...")
    config = joblib.load("models/D2_v2_no_acceleration_config.pkl")
    bundle = joblib.load("models/D2_v2_no_acceleration_frozen_model.pkl")
    
    if isinstance(bundle, dict):
        model = bundle.get("model", bundle)
    else:
        model = bundle
        
    feature_names = config.get("model_features", [])
    print(f"Loaded frozen model with {len(feature_names)} features.")
    
    # Create sample synthetic background/test data matching feature dimensions
    X_sample = np.random.randn(5, len(feature_names))
    df_sample = pd.DataFrame(X_sample, columns=feature_names)
    
    print("Initializing shap.TreeExplainer...")
    explainer = shap.TreeExplainer(model)
    print("Computing shap values on 5 sample components...")
    shap_vals = explainer.shap_values(df_sample.values)
    print(f"SHAP values computed successfully! Shape: {shap_vals.shape}")
    
    # Feature attributions for row 0
    row0_shap = pd.Series(shap_vals[0], index=feature_names)
    top_pos = row0_shap.sort_values(ascending=False).head(5)
    top_neg = row0_shap.sort_values(ascending=True).head(5)
    print("\nTop positive SHAP contributors (pushing toward anomaly):")
    for feat, val in top_pos.items():
        print(f"  {feat}: {val:+.4f}")
    print("\nTop negative SHAP contributors (pushing toward normal):")
    for feat, val in top_neg.items():
        print(f"  {feat}: {val:+.4f}")

if __name__ == "__main__":
    test_shap_on_frozen_if()
