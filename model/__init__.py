"""Dixon-Coles match-prediction model (§4).

The model knows nothing about tournaments. It fits attack/defence strengths and
a home-advantage term by time-weighted maximum likelihood on historical results
and exposes a full scoreline-probability matrix per fixture.
"""

from model.dixon_coles import DixonColesModel

__all__ = ["DixonColesModel"]
