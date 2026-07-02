---
name: project-governance
description: Handles repository standards, workspace setup, and project initialization steps.
---

# Project Governance

This skill coordinates workspace setups, coding guidelines, and repository-specific development standards.

## Workspace Check on Load

Whenever this skill is triggered or loaded:

1. **Check for Recent Clone / Fresh Environment**:
   - Immediately ask the user if this is a recently cloned repository or a fresh setup.
   - Check if the local development environment is initialized (e.g., check if the virtual environment `.venv` folder exists).
   
2. **Execute Setup**:
   - If the project was recently cloned or the environment is not initialized, guide the user to run the setup script.
   - Offer to execute the following command:
     ```bash
     bash skills/project-governance/scripts/setup.sh
     ```
