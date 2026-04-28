from .ppo_agent import PPOAgent

__all__ = ["PPOAgent", "make_cvar_ppo", "CVaRReturnTracker"]


def __getattr__(name):
    if name in {"make_cvar_ppo", "CVaRReturnTracker"}:
        from .cvar_ppo import make_cvar_ppo, CVaRReturnTracker
        return {"make_cvar_ppo": make_cvar_ppo, "CVaRReturnTracker": CVaRReturnTracker}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
