# Contributing to JellyDemon

First off, thanks for taking the time to contribute! 🎉

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues as you might find that the problem has already been reported. When you are creating a bug report, please include as many details as possible:

- Use a clear and descriptive title
- Describe the exact steps to reproduce the problem
- Provide specific examples and expected vs actual behavior
- Include log snippets and configuration details
- Describe your environment (OS, Python version, Jellyfin version, router model)

### Suggesting Features

Feature suggestions are welcome! Please provide:

- A clear and concise description of the feature
- Your specific use case and how it would benefit users
- Any implementation ideas you might have
- Consider if this fits the project's scope of bandwidth management

### Development Setup

1. **Clone and setup the project:**
   ```bash
   git clone <your-fork>
   cd jellydemon
   cp .env.example .env
   # Fill in your actual credentials in .env
   # config.yml uses placeholders like ${ROOTER_PASS} and ${JELLY_API}.
   # Replace them manually or enable environment-variable substitution
   # so they are read from your .env file.
   pip install -r requirements.txt
   ```

2. **Test your setup:**
   ```bash
   python test_bandwidth_control.py  # Test Jellyfin integration
   python test_jellydemon.py         # Run test suite
   ```

3. **Development workflow:**
   - Create a feature branch: `git checkout -b feature/your-feature-name`
   - Make your changes
   - Test thoroughly
   - Commit with clear messages
   - Push and create a PR

### Code Style

- Follow PEP 8 Python style guidelines
- Use clear, descriptive variable and function names
- Add docstrings for functions and classes
- Include error handling and logging
- Keep functions focused and modular

### Testing

- Test your changes with real Jellyfin sessions when possible
- Use the provided test scripts
- Ensure backward compatibility
- Test both SSH and LuCI router communication methods
- Verify dry-run mode works correctly

### Pull Request Process

1. Update documentation if you're adding new features
2. Add or update tests as appropriate
3. Ensure all tests pass
4. Update the README if needed
5. Request review from maintainers

## Architecture Notes

### Key Components

- **Router Communication**: Both SSH and LuCI methods supported
- **Jellyfin Integration**: Uses official API with proper authentication
- **Session Management**: Handles bandwidth changes with session restart
- **Bandwidth Algorithms**: Pluggable calculation methods

### Important Behaviors

- **Bandwidth changes require session restart**: This is a Jellyfin limitation
- **External IP detection**: Configurable IP ranges for internal vs external users
- **Safe operation**: Always includes dry-run and backup mechanisms

## Questions?

Feel free to open an issue for questions or join discussions. We're here to help!

## License

By contributing, you agree that your contributions will be licensed under the MIT License. 