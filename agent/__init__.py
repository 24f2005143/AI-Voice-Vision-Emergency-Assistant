"""Emergency reasoning agent package.

Re-exports the single public entry point so callers can use either

    from agent import analyze
    from agent.emergency_agent import analyze

Making this a regular package also lets ``python -m unittest discover -s agent``
load the agent-owned tests.
"""

from agent.emergency_agent import analyze

__all__ = ["analyze"]
