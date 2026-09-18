"""Feature engineering and preprocessing modules for fraud detection."""
from .transformers import (
    FraudDomainFeatureEngineer,
    SparseMissingIndicator,
    MatchFlagEncoder,
    EmailDomainGrouper,
)
from .pipeline import (
    FraudFeaturePipeline,
    build_feature_pipeline,
    fit_and_save_pipeline,
)

__all__ = [
    "FraudDomainFeatureEngineer",
    "SparseMissingIndicator",
    "MatchFlagEncoder",
    "EmailDomainGrouper",
    "FraudFeaturePipeline",
    "build_feature_pipeline",
    "fit_and_save_pipeline",
]
