import shlex
import subprocess
import sys

from modelforge import config
from modelforge.registry import (
    ConfigurationError,
    ModelForgeRegistry,
    ModelNotFoundError,
    ProviderError,
)

PROMPT = "Say hello from GitHub Copilot!"
COPILOT_PROVIDER = "github_copilot"


def run_cli_command(args: list[str]) -> bool:
    """Run a CLI command and print output."""
    if not args or not isinstance(args, list):
        raise ValueError("Invalid arguments provided")

    # Sanitize each argument
    safe_args = [shlex.quote(str(arg)) for arg in args]
    print(f"$ {' '.join(safe_args)}")

    # Use shell=False (default) for safety
    result = subprocess.run(args, capture_output=True, text=True, check=False)  # noqa: S603
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


def main() -> None:
    print("\n=== GitHub Copilot ModelForge Connection Test ===\n")
    registry = ModelForgeRegistry()
    current = config.get_current_model()
    if not current or current.get("provider") != COPILOT_PROVIDER:
        print("❌ No GitHub Copilot model is currently selected.")
        print("➡️  To add and select one, run:")
        cmd1 = "poetry run modelforge config add --provider github_copilot"
        cmd1 += " --model claude-3.7-sonnet --dev-auth"
        cmd2 = "poetry run modelforge config use --provider github_copilot"
        cmd2 += " --model claude-3.7-sonnet"
        print(f"    {cmd1}")
        print(f"    {cmd2}")
        sys.exit(1)
    print(f"✅ Current Copilot model: {current['model']}")

    # Try to get the LLM (this will trigger device flow if needed)
    try:
        llm = registry.get_llm()
    except ProviderError as e:
        msg = str(e)
        if "not installed" in msg:
            print("❌ langchain-github-copilot is not installed. Run:")
            print("    poetry add langchain-github-copilot")
        elif "Could not get valid credentials" in msg or "Authentication failed" in msg:
            print("❌ Not authenticated with GitHub Copilot.")
            cmd = "poetry run modelforge config add --provider github_copilot"
            cmd += " --model claude-3.7-sonnet --dev-auth"
            print("➡️  Run the following to authenticate:")
            print(f"    {cmd}")
        else:
            print(f"❌ Error: {msg}")
        sys.exit(1)
    except (ModelNotFoundError, ConfigurationError) as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

    # Send a test prompt
    print(f"\n✅ Connected! Sending test prompt: '{PROMPT}'\n")
    try:
        response = llm.invoke(PROMPT)
        print("--- Response ---")
        print(response)
        print("\n🎉 Success! GitHub Copilot is working via ModelForge.\n")
    except Exception as e:
        print(f"❌ Failed to invoke model: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
