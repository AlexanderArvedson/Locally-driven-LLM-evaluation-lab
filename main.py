
"""
Main entry point for task execution and evaluation.

Usage:
    python main.py task_01 qwen2.5-coder [--iterations 3]
    python main.py task_01 qwen2.5-coder [--model-timeout 300]
    python main.py --list-tasks
"""

import sys
import argparse
from pathlib import Path

from loguru import logger

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)


def main():
    parser = argparse.ArgumentParser(
        description="Task execution and evaluation harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py task_01 qwen2.5-coder              Run task_01 with qwen2.5-coder
  python main.py task_01 qwen2.5-coder --iterations 3  Run with 3 iterations
  python main.py --list-tasks                       List available tasks
  python main.py --list-results                     List recent results
        """
    )
    
    parser.add_argument(
        "task_id",
        nargs="?",
        help="Task identifier (e.g., task_01)"
    )
    
    parser.add_argument(
        "model",
        nargs="?",
        help="Model name (e.g., qwen2.5-coder)"
    )
    
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="Maximum iterations (default: from task spec)"
    )

    parser.add_argument(
        "--model-timeout",
        type=int,
        default=300,
        help="Timeout in seconds for each model API request"
    )
    
    parser.add_argument(
        "--list-tasks",
        action="store_true",
        help="List available tasks"
    )
    
    parser.add_argument(
        "--list-results",
        action="store_true",
        help="List recent results"
    )
    
    args = parser.parse_args()
    
    # Import here to avoid circular imports
    from evaluation_suite.runner import TaskRunner
    from evaluation_suite.task_loader import TaskLoader
    from evaluation_suite.result_store import ResultStore
    
    try:
        # List tasks
        if args.list_tasks:
            task_loader = TaskLoader()
            tasks = task_loader.list_available_tasks()
            print(f"\nAvailable tasks ({len(tasks)}):")
            for task_id in tasks:
                try:
                    task = task_loader.load_task(task_id)
                    print(f"  {task_id:<15} - {task.metadata.name}")
                except Exception as e:
                    print(f"  {task_id:<15} - [ERROR: {str(e)[:50]}]")
            return 0
        
        # List results
        if args.list_results:
            result_store = ResultStore()
            results = result_store.list_results(limit=10)
            print(f"\nRecent results ({len(results)}):")
            for run_id in results:
                print(f"  {run_id}")
            return 0
        
        # Run task
        if not args.task_id or not args.model:
            parser.print_help()
            return 1
        
        runner = TaskRunner(model_timeout_seconds=args.model_timeout)
        ctx = runner.run_task(
            task_id=args.task_id,
            model_name=args.model,
            max_iterations=args.iterations
        )
        
        print(f"\n✓ Run complete: {ctx.run_id}")
        print(f"  Iterations: {ctx.final_iteration}")
        if ctx.attempts:
            print(f"  Success: {ctx.attempts[-1].success}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())