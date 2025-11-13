"""
Environment Management module for API Testing

Handles storage and management of multiple API environments (dev, staging, prod).
Part of Phase 7 Enhancements.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional

from ccc.api_request import Environment, EnvironmentStore, VariableStore
from ccc.utils import get_branch_dir


def get_api_environments_path(branch_name: str) -> Path:
    """
    Get path to API environments file for a branch.

    Args:
        branch_name: Branch name

    Returns:
        Path to api-environments.yaml
    """
    return get_branch_dir(branch_name) / "api-environments.yaml"


def ensure_environments_file(branch_name: str):
    """
    Ensure API environments file exists for a branch.

    Args:
        branch_name: Branch name
    """
    path = get_api_environments_path(branch_name)

    if not path.exists():
        # Create default environment store with dev environment
        default_store = EnvironmentStore(
            current_environment="dev",
            environments={
                "dev": Environment(
                    name="dev",
                    variables={
                        "base_url": "http://localhost:3000",
                    }
                )
            }
        )
        save_environments(branch_name, default_store)


def load_environments(branch_name: str) -> EnvironmentStore:
    """
    Load environment store for a branch.

    Args:
        branch_name: Branch name

    Returns:
        EnvironmentStore with all environments
    """
    ensure_environments_file(branch_name)
    path = get_api_environments_path(branch_name)

    try:
        with open(path, 'r') as f:
            data = yaml.safe_load(f) or {}

        return EnvironmentStore.from_dict(data)

    except Exception:
        # Return default on error
        return EnvironmentStore(
            current_environment="dev",
            environments={
                "dev": Environment(name="dev", variables={})
            }
        )


def save_environments(branch_name: str, env_store: EnvironmentStore):
    """
    Save environment store for a branch.

    Args:
        branch_name: Branch name
        env_store: EnvironmentStore to save
    """
    path = get_api_environments_path(branch_name)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w') as f:
        yaml.dump(env_store.to_dict(), f, default_flow_style=False, sort_keys=False)


def get_current_environment(branch_name: str) -> str:
    """
    Get the current environment name for a branch.

    Args:
        branch_name: Branch name

    Returns:
        Current environment name
    """
    env_store = load_environments(branch_name)
    return env_store.current_environment


def switch_environment(branch_name: str, env_name: str) -> bool:
    """
    Switch to a different environment.

    Args:
        branch_name: Branch name
        env_name: Name of environment to switch to

    Returns:
        True if switched successfully, False if environment doesn't exist
    """
    env_store = load_environments(branch_name)

    if env_store.switch_environment(env_name):
        save_environments(branch_name, env_store)
        return True

    return False


def list_environments(branch_name: str) -> List[str]:
    """
    List all environment names for a branch.

    Args:
        branch_name: Branch name

    Returns:
        List of environment names
    """
    env_store = load_environments(branch_name)
    return list(env_store.environments.keys())


def get_environment(branch_name: str, env_name: str) -> Optional[Environment]:
    """
    Get a specific environment by name.

    Args:
        branch_name: Branch name
        env_name: Environment name

    Returns:
        Environment or None if not found
    """
    env_store = load_environments(branch_name)
    return env_store.environments.get(env_name)


def add_environment(branch_name: str, env_name: str, variables: Dict[str, str]):
    """
    Add or update an environment.

    Args:
        branch_name: Branch name
        env_name: Environment name
        variables: Dictionary of variables for this environment
    """
    env_store = load_environments(branch_name)

    environment = Environment(name=env_name, variables=variables)
    env_store.add_environment(environment)

    save_environments(branch_name, env_store)


def delete_environment(branch_name: str, env_name: str) -> bool:
    """
    Delete an environment.

    Args:
        branch_name: Branch name
        env_name: Environment name to delete

    Returns:
        True if deleted, False if not found or if it's the current environment
    """
    env_store = load_environments(branch_name)

    # Don't allow deleting the current environment
    if env_name == env_store.current_environment:
        return False

    if env_name in env_store.environments:
        del env_store.environments[env_name]
        save_environments(branch_name, env_store)
        return True

    return False


def get_merged_variables(
    branch_name: str,
    captured_vars: Optional[Dict[str, str]] = None
) -> VariableStore:
    """
    Get merged variable store with proper precedence.

    Precedence (highest to lowest):
    1. Captured variables (from request chaining)
    2. Environment-specific variables
    3. Shell environment variables (via {{ENV_VAR}} substitution)

    Args:
        branch_name: Branch name
        captured_vars: Optional dictionary of captured variables from request chaining

    Returns:
        VariableStore with merged variables
    """
    env_store = load_environments(branch_name)
    env_vars = env_store.get_current_variables()

    # Start with environment variables
    merged = VariableStore(variables=env_vars.copy())

    # Override with captured variables
    if captured_vars:
        for key, value in captured_vars.items():
            merged.set(key, value)

    return merged


def set_environment_variable(
    branch_name: str,
    env_name: str,
    key: str,
    value: str
):
    """
    Set a variable in a specific environment.

    Args:
        branch_name: Branch name
        env_name: Environment name
        key: Variable name
        value: Variable value
    """
    env_store = load_environments(branch_name)

    if env_name in env_store.environments:
        env = env_store.environments[env_name]
        env.variables[key] = value
        save_environments(branch_name, env_store)


def delete_environment_variable(
    branch_name: str,
    env_name: str,
    key: str
) -> bool:
    """
    Delete a variable from a specific environment.

    Args:
        branch_name: Branch name
        env_name: Environment name
        key: Variable name

    Returns:
        True if deleted, False if not found
    """
    env_store = load_environments(branch_name)

    if env_name in env_store.environments:
        env = env_store.environments[env_name]
        if key in env.variables:
            del env.variables[key]
            save_environments(branch_name, env_store)
            return True

    return False
