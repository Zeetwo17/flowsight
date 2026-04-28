from .hawkes import HawkesDetector

__all__ = ["HawkesDetector", "NeuralHawkesDetector", "DCRNNForecaster"]


def __getattr__(name):
    """Lazy-load PyTorch-dependent classes so the package imports without torch."""
    if name == "NeuralHawkesDetector":
        from .neural_hawkes import NeuralHawkesDetector
        return NeuralHawkesDetector
    if name == "DCRNNForecaster":
        from .dcrnn import DCRNNForecaster
        return DCRNNForecaster
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
