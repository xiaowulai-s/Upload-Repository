# GitHub Repository Sync Tool

A powerful GitHub repository synchronization tool built with Python, featuring both GUI and CLI interfaces for seamless repository management.

## Version
1.0.0

## Features

### Core Functionality
- Bind local folders to GitHub repositories
- Pull and push code with a single click
- Automated changelog generation and synchronization
- Support for multiple repositories management
- Git operations encapsulation with async support

### Architecture
- **Presentation Layer**: PySide6 GUI + Click CLI
- **Business Layer**: Service-oriented design
- **Core Layer**: Git operations engine, log generation, repository management
- **Data Layer**: SQLite database for repository configuration

### GUI Interface
- Modern, user-friendly interface
- Real-time operation status updates
- Asynchronous operations to prevent freezing
- Repository management dashboard

### CLI Interface
- Comprehensive command-line commands
- Support for all core functionalities
- Easy integration with scripts and workflows

## Installation

### Prerequisites
- Python 3.8+
- Git installed and configured

### Install Dependencies
```bash
pip install -r requirements.txt
```

## Usage

### GUI Mode
```bash
python -m src.main
```

### CLI Mode
```bash
# Show help
python -m src.main --help

# Bind a local folder to a repository
python -m src.main bind --folder /path/to/folder --remote https://github.com/user/repo.git

# Pull changes from remote
python -m src.main pull <repo-id>

# Push changes to remote
python -m src.main push <repo-id> --message "Your commit message"

# Commit changes
python -m src.main commit <repo-id> --message "Your commit message"

# Synchronize repository (pull + commit + push)
python -m src.main sync <repo-id>

# Generate changelog
python -m src.main changelog <repo-id>
```

## Project Structure

```
.
├── src/
│   ├── cli/                  # Command-line interface
│   ├── core/                 # Core functionality (Git engine, log generation)
│   ├── data/                 # Data layer (database, config management)
│   ├── models/               # Data models definition
│   ├── services/             # Business logic services
│   ├── ui/                   # GUI implementation with dialogs
│   └── utils/                # Utility functions and helpers
├── tests/                    # Test suite
├── pyproject.toml            # Project configuration
├── requirements.txt          # Project dependencies
└── README.md                 # This file
```

## Configuration

The tool uses SQLite database to store repository configurations and JSON files for application settings. 
- Database file: `~/.git-sync-tool/repositories.db`
- Config files: `~/.git-sync-tool/config.<env>.json` (default: config.default.json)

## Logging

All operations are logged to `~/.github_sync_tool.log` with detailed information about each operation.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

## Authors

- xiaowulai-s

## GitHub Repository

https://github.com/xiaowulai-s/Upload-Repository.git
