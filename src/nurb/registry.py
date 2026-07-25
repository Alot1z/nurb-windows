"""Part registration. A part is a function; its defaults are its parameters."""

import inspect
from dataclasses import dataclass


@dataclass
class PartDef:
    fn: callable
    name: str
    params: dict
    accepts_draft: bool


def part(fn):
    """Mark a function as a part.

    The function's keyword defaults are the part's parameters. That's the whole
    convention -- one declaration feeds the CLI, the viewer sliders and the tests.

    An optional `draft` parameter is passed by the runtime, not the caller: when
    it's True the part should skip its polish pass (chamfers, fillets) so the
    live rebuild stays fast.
    """
    params = {}
    accepts_draft = False
    for name, p in inspect.signature(fn).parameters.items():
        if name == "draft":
            accepts_draft = True
            continue
        params[name] = None if p.default is inspect.Parameter.empty else p.default
    fn._nurb = PartDef(fn=fn, name=fn.__name__, params=params, accepts_draft=accepts_draft)
    return fn
