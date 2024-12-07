# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2024-01-17

### Added
- Comprehensive documentation for `markdown_utils.py`
- Mermaid diagrams for component visualization
- Type definitions and error handling documentation
- Development dependencies for testing and linting
- Integration point documentation
- Error scenario documentation

### Changed
- Updated requirements.txt with development dependencies
- Improved documentation structure following RULES.md
- Enhanced error handling documentation
- Reorganized component documentation

### Fixed
- Missing dependency specifications
- Documentation formatting issues
- Type hint completeness
- Error handling documentation gaps

## [1.0.0] - 2024-01-17

### Added
- New `markdown_utils.py` module for shared markdown processing functionality
- Interactive menu system in `process_existing.py`
- Support for both online and offline processing
- Automatic chapter number generation
- Glossary handling
- Print-ready version generation
- Progress tracking and state persistence
- Comprehensive documentation

### Changed
- Reorganized code to reduce duplication
- Moved shared functionality to `markdown_utils.py`
- Updated `webmark_uefn.py` to use shared utilities
- Improved error handling and logging
- Enhanced chapter organization logic
- Updated documentation structure

### Fixed
- Link processing for glossary entries
- Chapter number generation for API documentation
- Image path handling in markdown
- Frontmatter parsing issues
- Duplicate title removal
- Link resolution for nested directories

### Removed
- Duplicate code from individual scripts
- Unnecessary configuration options
- Legacy processing functions

## [0.2.0] - 2024-01-15

### Added
- Initial offline processing support
- Basic chapter organization
- Link fixing utilities
- Image downloading
- Print version generation

### Changed
- Improved documentation scraping
- Enhanced error handling
- Updated configuration options

### Fixed
- Various link processing issues
- Image download failures
- Chapter numbering inconsistencies

## [0.1.0] - 2024-01-10

### Added
- Initial release
- Basic documentation scraping
- HTML to markdown conversion
- Simple link processing
- Basic error handling