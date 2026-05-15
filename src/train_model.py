import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error
import pickle

def train():
    print("Loading features...")
    df = pd.read_parquet("data/features.parquet")

    df = df.dropna(subset=["spread_abs", "total", "gei_normalized"])

    print(f"Training on {len(df)} games")

    train = df[df["date"] < "2022-10-01"]
    val = df[df["date"] >= "2022-10-01"]

    print(f"Train: {len(train)}, Val: {len(val)}")

    feature_cols = [
        "spread_abs", "total", "home_win_pct", "home_avg_pts",
        "home_rest_days", "home_b2b", "late_season", "month"
    ]

    X_train = train[feature_cols]
    y_train = train["gei_normalized"]
    X_val = val[feature_cols]
    y_val = val["gei_normalized"]

    mean_baseline_mae = mean_absolute_error(y_val, np.full(len(y_val), y_train.mean()))
    print(f"Mean baseline MAE: {mean_baseline_mae:.4f}")

    spread_model = np.polyfit(train["spread_abs"], y_train, 1)
    spread_preds = np.polyval(spread_model, val["spread_abs"])
    spread_baseline_mae = mean_absolute_error(y_val, spread_preds)
    print(f"Spread-only baseline MAE: {spread_baseline_mae:.4f}")

    model = xgb.XGBRegressor(
        n_estimators=500,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        early_stopping_rounds=20,
        verbosity=0,
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    val_preds = model.predict(X_val)
    model_mae = mean_absolute_error(y_val, val_preds)
    print(f"XGBoost MAE: {model_mae:.4f}")
    print(f"Improvement over mean baseline: {((mean_baseline_mae - model_mae) / mean_baseline_mae * 100):.1f}%")
    print(f"Improvement over spread baseline: {((spread_baseline_mae - model_mae) / spread_baseline_mae * 100):.1f}%")

    importance = pd.Series(model.feature_importances_, index=feature_cols)
    print(f"\nFeature importance:\n{importance.sort_values(ascending=False)}")

    with open("data/model.pkl", "wb") as f:
        pickle.dump(model, f)
    print("\nModel saved to data/model.pkl")

if __name__ == "__main__":
    train()