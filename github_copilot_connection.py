import subprocess
import sys
from modelforge.registry import ModelForgeRegistry, ProviderError, ModelNotFoundError, ConfigurationError
from modelforge import config

PROMPT = "Say hello from GitHub Copilot!"
COPILOT_PROVIDER = "github_copilot"


def run_cli_command(args):
    """Run a CLI command and print output."""
    print(f"$ {' '.join(args)}")
    result = subprocess.run(args, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


def main():
    print("\n=== GitHub Copilot ModelForge Connection Test ===\n")
    registry = ModelForgeRegistry()
    current = config.get_current_model()
    if not current or current.get("provider") != COPILOT_PROVIDER:
        print("❌ No GitHub Copilot model is currently selected.")
        print("➡️  To add and select one, run:")
        print("    poetry run modelforge config add --provider github_copilot --model claude-3.7-sonnet --dev-auth")
        print("    poetry run modelforge config use --provider github_copilot --model claude-3.7-sonnet")
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
            print("➡️  Run the following to authenticate:")
            print("    poetry run modelforge config add --provider github_copilot --model claude-3.7-sonnet --dev-auth")
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