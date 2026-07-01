"""
hoare-agent Python SDK
======================
Formally verify Python functions using Hoare logic and the Z3 SMT solver.

Quick start
-----------
::

    from hoareagent import verify

    def add_positive(x, y):
        '''
        :pre:  x >= 0 and y >= 0
        :post: result >= 0
        '''
        return x + y

    result = verify(code=add_positive)
    print(result)  # ✓ VERIFIED

You can also supply conditions explicitly::

    result = verify(code=add_positive, pre="x >= 0 and y >= 0", post="result >= 0")

Or use the ``@verified`` decorator to verify at import time::

    from hoareagent import verified

    @verified(pre="x >= 0", post="result >= 0")
    def double(x):
        return x * 2
"""

from hoareagent._core import verify, verified, HoareResult

__all__ = ["verify", "verified", "HoareResult"]
__version__ = "0.1.0"
