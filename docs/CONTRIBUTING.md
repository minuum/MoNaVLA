# Contributing Guide

## Commit Message Convention

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

### Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **perf**: A code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **build**: Changes that affect the build system or external dependencies (example scopes: gulp, broccoli, npm)
- **ci**: Changes to our CI configuration files and scripts (example scopes: Travis, Circle, BrowserStack, SauceLabs)
- **chore**: Other changes that don't modify src or test files
- **revert**: Reverts a previous commit

### Example
```
feat(auth): add google login support

Added Google OAuth2 integration for user authentication.
- Implemented GoogleStrategy
- Updated user model to store googleId

Closes #123
```

## Branch Naming Convention

- **Features**: `feature/description-of-feature`
- **Bug Fixes**: `bugfix/description-of-bug`
- **Hot Fixes**: `hotfix/critical-fix`
- **Documentation**: `docs/description`
- **Refactoring**: `refactor/description`

## Workflow

1. Create a new branch for your work.
2. Make small, focused commits.
3. Write clear and descriptive commit messages.
4. Push to the remote repository and create a Pull Request (if applicable).
