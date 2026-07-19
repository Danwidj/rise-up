import os
import platform
import subprocess
import sys


def run_command(command, fail_on_error=True):
    """Executes a shell command cleanly across Windows and macOS architectures."""
    # Windows requires shell=True to find cmd paths; macOS handles arrays natively if needed,
    # but shell=True remains safe for standard cross-platform Git wrappers.
    try:
        result = subprocess.run(
            command, shell=True, check=True, text=True, capture_output=True
        )
        print(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        if fail_on_error:
            print(f"\nError executing: {command}", file=sys.stderr)
            print(f"Details: {e.stderr.strip()}", file=sys.stderr)
        return False


def main():
    if len(sys.argv) >= 2 and sys.argv[1].strip():
        commit_message = sys.argv[1].strip()
    else:
        try:
            commit_message = input("Enter your commit message: ").strip()
            if not commit_message:
                print("Error: Commit message cannot be empty.")
                sys.exit(1)
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            sys.exit(1)
    current_os = platform.system()

    print(f"System Detected: {current_os}")
    
    try:
        # We use --autostash so that any uncommitted changes are safely tucked away during the rebase
        print("Step 1: Fetching updates and rebasing from remote main...")
        rebase_success = run_command(
            "git pull --rebase --autostash origin main", fail_on_error=False
        )

        if not rebase_success:
            print(
                "\nConflict detected! Launching the visual conflict resolver in your IDE..."
            )

            # Triggers the specific mergetool layout
            subprocess.run("git mergetool", shell=True)

            print("\nVerification: Finalizing the rebase/stash pipeline...")
            
            # We try to continue the rebase in case the conflict was during rebase. 
            # If the conflict was during stash pop, this command will safely do nothing/fail.
            if current_os == "Windows":
                os.environ["GIT_EDITOR"] = "true"
            
            # We ignore errors here because if the conflict was from an autostash pop, 
            # there is no rebase in progress to continue.
            subprocess.run("git rebase --continue", shell=True, capture_output=True)

        print("\nStep 2: Committing changes locally...")
        escaped_message = commit_message.replace('"', '\\"')
        run_command("git add -A", fail_on_error=False)
        run_command(f'git commit -m "{escaped_message}"', fail_on_error=False)

        print("\nStep 3: Pushing clean commit history to remote main...")
        if not run_command("git push origin main"):
            sys.exit(1)

        print("\nStep 4: Pulling latest changes from remote main...")
        run_command("git pull origin main")

        print("\nSuccess! Changes pulled, committed, pushed, and synced.")

    except KeyboardInterrupt:
        print("\nCancellation detected! Aborting operation and reverting to original state...")
        # Aborting the rebase restores the state back to before the pull, including popping the autostash.
        run_command("git rebase --abort", fail_on_error=False)
        sys.exit(1)


if __name__ == "__main__":
    main()