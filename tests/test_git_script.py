import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import subprocess

# Add the git scripts directory to sys.path and import custom as git_script for compatibility
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'skills', 'git', 'scripts')))
# pyrefly: ignore [missing-import]
import custom as git_script
sys.modules['git_script'] = git_script

class TestGitScript(unittest.TestCase):

    @patch('git_script.subprocess.run')
    def test_run_command_success(self, mock_run):
        """Test that run_command works and returns True on success."""
        mock_result = MagicMock()
        mock_result.stdout = "success output"
        mock_run.return_value = mock_result
        
        result = git_script.run_command("echo hello")
        
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            "echo hello", shell=True, check=True, text=True, capture_output=True
        )

    @patch('git_script.subprocess.run')
    def test_run_command_failure(self, mock_run):
        """Test that run_command catches CalledProcessError and returns False."""
        # Setup mock to raise an error to simulate command failure
        mock_run.side_effect = subprocess.CalledProcessError(1, "bad_cmd", stderr="error output")
        
        result = git_script.run_command("bad_cmd", fail_on_error=True)
        
        self.assertFalse(result)

    @patch('git_script.sys.argv', ['git_script.py', 'test message'])
    @patch('git_script.run_command')
    @patch('git_script.sys.exit')
    def test_main_success_with_args(self, mock_exit, mock_run_command):
        """Test the standard happy-path flow when a message is provided via arguments."""
        # Mock run_command to always return True (success)
        mock_run_command.return_value = True
        
        git_script.main()
        
        # Verify the sequence of Git commands
        mock_run_command.assert_any_call("git pull --rebase --autostash origin main", fail_on_error=False)
        mock_run_command.assert_any_call('git commit -a -m "test message"', fail_on_error=False)
        mock_run_command.assert_any_call("git push origin main")
        mock_exit.assert_not_called()

    @patch('git_script.sys.argv', ['git_script.py'])
    @patch('git_script.input', return_value='interactive message')
    @patch('git_script.run_command')
    @patch('git_script.sys.exit')
    def test_main_interactive_input(self, mock_exit, mock_run_command, mock_input):
        """Test that it prompts for input if no arguments are provided."""
        mock_run_command.return_value = True
        
        git_script.main()
        
        mock_input.assert_called_once()
        mock_run_command.assert_any_call('git commit -a -m "interactive message"', fail_on_error=False)

    @patch('git_script.sys.argv', ['git_script.py', 'msg'])
    @patch('git_script.run_command')
    @patch('git_script.subprocess.run')
    @patch('git_script.sys.exit')
    def test_main_conflict_resolution(self, mock_exit, mock_subprocess_run, mock_run_command):
        """Test that a conflict on pull triggers the mergetool and rebase continue."""
        
        # Custom side effect: return False for 'git pull' to simulate a conflict
        def run_command_side_effect(cmd, **kwargs):
            if "git pull" in cmd:
                return False
            return True
        mock_run_command.side_effect = run_command_side_effect
        
        git_script.main()
        
        # Verify it opened the mergetool and attempted to continue
        mock_subprocess_run.assert_any_call("git mergetool", shell=True)
        mock_subprocess_run.assert_any_call("git rebase --continue", shell=True, capture_output=True)
        # Should still try to commit and push afterward
        mock_run_command.assert_any_call("git push origin main")

    @patch('git_script.sys.argv', ['git_script.py', 'msg'])
    @patch('git_script.run_command')
    @patch('git_script.sys.exit')
    def test_main_keyboard_interrupt(self, mock_exit, mock_run_command):
        """Test that pressing Ctrl+C correctly intercepts and aborts the rebase."""
        # Make the very first run_command raise a KeyboardInterrupt, then return True
        mock_run_command.side_effect = [KeyboardInterrupt(), True]
        
        git_script.main()
        
        # Verify the fallback aborted the rebase
        mock_run_command.assert_called_with("git rebase --abort", fail_on_error=False)
        mock_exit.assert_called_once_with(1)

if __name__ == '__main__':
    unittest.main()
