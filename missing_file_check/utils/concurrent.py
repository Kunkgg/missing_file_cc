"""
Concurrent execution utilities for parallel processing.

Provides thread pool and process pool executors for I/O and CPU intensive tasks.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, TypeVar, Optional, Dict, Any

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ParallelExecutor:
    """
    Parallel task executor using thread pools.

    Optimized for I/O-bound tasks like API calls and file operations.
    """

    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize parallel executor.

        Args:
            max_workers: Maximum number of worker threads.
                        None = defaults to min(32, cpu_count + 4)
        """
        self.max_workers = max_workers

    def execute_tasks(
        self,
        func: Callable[[T], Any],
        items: List[T],
        task_name: str = "task",
        show_progress: bool = True,
    ) -> List[Any]:
        """
        Execute a function on multiple items in parallel.

        Args:
            func: Function to execute on each item
            items: List of items to process
            task_name: Name for logging/progress (e.g., "fetching projects")
            show_progress: Whether to log progress

        Returns:
            List of results in the same order as items

        Raises:
            Exception: If any task fails, the first exception is raised
        """
        if not items:
            logger.info(f"No items to process for {task_name}")
            return []

        total = len(items)

        # Single item - no need for parallel execution
        if total == 1:
            logger.info(f"Processing single {task_name}")
            return [func(items[0])]

        # Multiple items - use thread pool
        logger.info(f"Processing {total} {task_name}(s) in parallel")

        results = [None] * total
        errors = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_index = {
                executor.submit(func, item): idx for idx, item in enumerate(items)
            }

            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                completed += 1

                try:
                    result = future.result()
                    results[idx] = result

                    if show_progress and completed % max(1, total // 10) == 0:
                        logger.info(
                            f"Progress: {completed}/{total} {task_name}(s) completed"
                        )

                except Exception as e:
                    item_repr = str(items[idx])[:50]
                    error_msg = f"Failed to process {task_name} {idx} ({item_repr}): {e}"
                    logger.error(error_msg)
                    errors.append((idx, e))

            if show_progress:
                logger.info(f"Completed all {total} {task_name}(s)")

        # Raise first error if any occurred
        if errors:
            idx, error = errors[0]
            raise RuntimeError(
                f"Parallel execution failed for {task_name} at index {idx}: {error}"
            ) from error

        return results

    def execute_dict_tasks(
        self,
        tasks: Dict[str, Callable[[], Any]],
        task_name: str = "task",
        show_progress: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute multiple named tasks in parallel.

        Args:
            tasks: Dictionary of task_name -> task_function
            task_name: Category name for logging
            show_progress: Whether to log progress

        Returns:
            Dictionary of task_name -> result

        Example:
            tasks = {
                'target1': lambda: fetch_target_project(config1),
                'target2': lambda: fetch_target_project(config2),
            }
            results = executor.execute_dict_tasks(tasks, 'projects')
        """
        if not tasks:
            return {}

        total = len(tasks)
        task_names = list(tasks.keys())

        if total == 1:
            name = task_names[0]
            return {name: tasks[name]()}

        logger.info(f"Executing {total} {task_name}(s) in parallel")

        results = {}
        errors = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_name = {
                executor.submit(task_func): name for name, task_func in tasks.items()
            }

            completed = 0
            for future in as_completed(future_to_name):
                name = future_to_name[future]
                completed += 1

                try:
                    result = future.result()
                    results[name] = result

                    if show_progress:
                        logger.info(
                            f"Progress: {completed}/{total} - '{name}' completed"
                        )

                except Exception as e:
                    logger.error(f"Failed to execute '{name}': {e}")
                    errors.append((name, e))

        if errors:
            name, error = errors[0]
            raise RuntimeError(
                f"Parallel execution failed for '{name}': {error}"
            ) from error

        return results


# Global singleton executor
_default_executor: Optional[ParallelExecutor] = None


def get_default_executor(max_workers: Optional[int] = None) -> ParallelExecutor:
    """
    Get or create the default parallel executor.

    Args:
        max_workers: Maximum worker threads (only used on first call)

    Returns:
        ParallelExecutor instance
    """
    global _default_executor

    if _default_executor is None:
        _default_executor = ParallelExecutor(max_workers=max_workers)

    return _default_executor


def parallel_map(
    func: Callable[[T], Any],
    items: List[T],
    max_workers: Optional[int] = None,
    task_name: str = "task",
) -> List[Any]:
    """
    Convenient function to map a function over items in parallel.

    Args:
        func: Function to apply
        items: List of items
        max_workers: Maximum worker threads
        task_name: Name for logging

    Returns:
        List of results

    Example:
        results = parallel_map(fetch_project, project_configs, task_name='projects')
    """
    executor = get_default_executor(max_workers)
    return executor.execute_tasks(func, items, task_name=task_name)
