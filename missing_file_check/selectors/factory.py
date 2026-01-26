"""
Factory for creating baseline selector strategies.

Maps strategy names to concrete selector implementations.
"""

from typing import Dict, Optional, Type

from missing_file_check.selectors.base import BaselineSelector, SelectorError
from missing_file_check.selectors.strategies import (
    LatestSuccessWithCommitIdMatcher,
    LatestSuccessWithVersionMatcher,
    SpecificBaselineCommitIdMatcher,
    SpecificBaselineVersionMatcher,
    LatestSuccessMatcher,
    NoRestrictionSelector,
)


class BaselineSelectorFactory:
    """Factory for creating baseline selector instances."""

    _registry: Dict[str, Type[BaselineSelector]] = {
        "latest_success_commit_id": LatestSuccessWithCommitIdMatcher,
        "latest_success_version": LatestSuccessWithVersionMatcher,
        "specific_baseline_commit_id": SpecificBaselineCommitIdMatcher,
        "specific_baseline_version": SpecificBaselineVersionMatcher,
        "latest_success": LatestSuccessMatcher,
        "no_restriction": NoRestrictionSelector,
    }

    @classmethod
    def create(
        cls, strategy_name: str, params: Optional[Dict] = None
    ) -> BaselineSelector:
        """
        Create a baseline selector instance.

        Args:
            strategy_name: Name of the strategy to use
            params: Optional parameters for strategies that require them

        Returns:
            Instantiated baseline selector

        Raises:
            SelectorError: If strategy name is unknown
        """
        selector_class = cls._registry.get(strategy_name)

        if selector_class is None:
            raise SelectorError(
                f"Unknown baseline selector strategy: {strategy_name}. "
                f"Available strategies: {list(cls._registry.keys())}"
            )

        # Strategies 3 and 4 require parameters
        if strategy_name in ("specific_baseline_commit_id", "specific_baseline_version"):
            if not params:
                raise SelectorError(
                    f"Strategy '{strategy_name}' requires parameters: "
                    "baseline_project_id, target_project_id"
                )
            return selector_class(**params)

        # Other strategies don't need parameters
        return selector_class()

    @classmethod
    def register(cls, strategy_name: str, selector_class: Type[BaselineSelector]):
        """
        Register a custom baseline selector strategy.

        Args:
            strategy_name: Name to register the strategy under
            selector_class: Selector class to register
        """
        cls._registry[strategy_name] = selector_class
