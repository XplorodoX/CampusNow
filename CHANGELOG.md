# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CI/CD Pipeline with GitHub Actions
- Automated testing on multiple Python versions (3.9, 3.10, 3.11)
- Code quality gates (Ruff, Flake8, Black)
- Security scanning (Bandit, Safety)
- Code coverage tracking with Codecov
- Docker image building in CI/CD

### Changed
- Enhanced Makefile with additional targets
- Improved pre-commit hooks configuration

### Fixed
- Python 3.9 type annotation compatibility

## [1.0.0] - 2026-03-20

### Added
- Initial StarPlan Scraper implementation
- Live HS Aalen integration
- JSON endpoint discovery
- iCal URL generation and validation
- iCal parsing with lecture data extraction

[Unreleased]: https://github.com/your-username/CampusNow/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/your-username/CampusNow/releases/tag/v1.0.0
