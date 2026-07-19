"""Placeholder for a future ML-based classifier.

Per this project's own anti-sycophancy rules: an ML classifier is only
shipped once it is independently shown to beat the rule-based baseline on a
real, honestly-reported test set (see the execution plan's Assumption 3).
No such model exists yet -- arXiv:2606.19262's trained weights and dataset
were not released, and this project's build environment has no GPU to
collect real training data on. Shipping a stub that returns fabricated
predictions would misrepresent accuracy that was never measured, so
`--experimental` fails loudly instead.
"""

from __future__ import annotations

from typing import Any, NoReturn


class ExperimentalClassifierUnavailable(RuntimeError):
    pass


def classify_experimental(*_args: Any, **_kwargs: Any) -> NoReturn:
    raise ExperimentalClassifierUnavailable(
        "The experimental ML classifier is not available in this release. "
        "workloadtruth ships only the rule-based classifier (see "
        "classifier/rules.py) until an ML classifier is trained and "
        "independently benchmarked against it on a real, disclosed test "
        "set. Run `workloadtruth classify` without --experimental."
    )
