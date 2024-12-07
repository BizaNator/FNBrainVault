# Contributing to WebMark

First off, thank you for considering contributing to WebMark! It's people like you that make WebMark such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the issue list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* Use a clear and descriptive title
* Describe the exact steps which reproduce the problem
* Provide specific examples to demonstrate the steps
* Describe the behavior you observed after following the steps
* Explain which behavior you expected to see instead and why
* Include screenshots if relevant
* Include error messages and logs

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* Use a clear and descriptive title
* Provide a step-by-step description of the suggested enhancement
* Provide specific examples to demonstrate the steps
* Describe the current behavior and explain which behavior you expected to see instead
* Explain why this enhancement would be useful
* List some other applications where this enhancement exists, if applicable

### Pull Requests

* Fill in the required template
* Do not include issue numbers in the PR title
* Follow the Python style guide
* Include appropriate test cases
* Document new code based on the Documentation Styleguide
* End all files with a newline

## Development Process

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code follows the style guidelines
6. Issue that pull request!

### Development Setup

1. Clone your fork of the repo
```bash
git clone https://github.com/YOUR_USERNAME/webmark.git
```

2. Install development dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # if exists
```

3. Create a branch
```bash
git checkout -b name-of-your-bugfix-or-feature
```

### Code Style

* Follow PEP 8
* Use type hints
* Write descriptive docstrings
* Comment complex logic
* Keep functions focused and small
* Use meaningful variable names

### Testing

* Write unit tests for new functionality
* Ensure all tests pass before submitting PR
* Include integration tests where appropriate
* Document test cases clearly

### Documentation

* Update README.md if needed
* Add docstrings to new functions
* Update CHANGELOG.md
* Include comments for complex logic
* Update type hints

## Project Structure

When adding new features, please follow the existing project structure:

```
webmark/
├── markdown_utils.py      # Core markdown processing utilities
├── webmark_uefn.py       # Online scraping functionality
├── fix_markdown_links.py  # Offline link processing
├── process_existing.py    # Main interface and processing
├── combine_docs.py       # Documentation combination
└── book_formatter.py     # Book formatting utilities
```

### Adding New Features

1. Core Processing Logic
   - Add to `markdown_utils.py`
   - Keep functions focused and reusable
   - Include comprehensive error handling
   - Add appropriate logging

2. Online Functionality
   - Add to `webmark_uefn.py`
   - Focus on scraping and downloading
   - Handle network errors gracefully
   - Implement rate limiting

3. Offline Processing
   - Add to `fix_markdown_links.py`
   - Focus on content improvement
   - Handle file operations safely
   - Maintain state properly

4. User Interface
   - Add to `process_existing.py`
   - Keep menu options clear
   - Provide good feedback
   - Handle interruptions gracefully

## Release Process

1. Update version numbers
2. Update CHANGELOG.md
3. Run full test suite
4. Create release branch
5. Submit PR for review
6. Create GitHub release
7. Update documentation

## Questions?

Feel free to open an issue with your question or contact the maintainers directly.

Thank you for contributing to WebMark! 