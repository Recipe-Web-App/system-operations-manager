module.exports = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "type-enum": [
      2,
      "always",
      [
        "build",    // Changes that affect the build system or external dependencies
        "ci",       // Changes to our CI configuration files and scripts
        "docs",     // Documentation only changes
        "feat",     // A new feature
        "fix",      // A bug fix
        "perf",     // A code change that improves performance
        "refactor", // A code change that neither fixes a bug nor adds a feature
        "style",    // Changes that do not affect the meaning of the code
        "test",     // Adding missing tests or correcting existing tests
        "chore",    // Other changes that don't modify src or test files
        "revert",   // Reverts a previous commit
      ],
    ],
    "scope-enum": [
      2,
      "always",
      [
        "adr",           // Architecture Decision Records
        "config",        // Configuration files
        "docs",          // General documentation
        "examples",      // Example documentation
        "features",      // Feature documentation
        "integrations", // Integration documentation  
        "plugins",       // Plugin documentation
        "commands",      // Command documentation
        "deps",          // Dependencies
        "release",       // Release related
        "setup",         // Project setup
      ],
    ],
    "scope-case": [2, "always", "lower-case"],
    "subject-case": [2, "never", ["sentence-case", "start-case", "pascal-case", "upper-case"]],
    "subject-empty": [2, "never"],
    "subject-full-stop": [2, "never", "."],
    "type-case": [2, "always", "lower-case"],
    "type-empty": [2, "never"],
    "header-max-length": [2, "always", 72],
    "body-max-line-length": [2, "always", 100],
  },
};