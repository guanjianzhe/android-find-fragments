# Repository Guidelines

## Project Structure & Module Organization
- Gradle-based IntelliJ Platform Plugin. Typical layout:
  - `build.gradle.kts`, `settings.gradle.kts`, `gradle.properties`
  - `src/main/kotlin/…` — plugin sources (Kotlin preferred)
  - `src/main/resources/META-INF/plugin.xml` — plugin descriptor
  - `src/main/resources/…` — icons, messages, UI descriptors
  - `src/test/kotlin/…` — unit tests
- Package names: `com.<org>.ideaplugin.currentfragment.…` (keep packages aligned to folders).

## Build, Test, and Development Commands
- `./gradlew build` — compile, run tests, produce artifacts.
- `./gradlew test` — run unit tests (JUnit 5).
- `./gradlew runIde` — launch sandbox IDE with the plugin.
- `./gradlew verifyPlugin` — verify plugin metadata and compatibility.
- `./gradlew buildPlugin` — assemble distributable ZIP in `build/distributions/`.

## Coding Style & Naming Conventions
- Language: Kotlin (use Java only when required).
- Indentation: 4 spaces; 120-char soft line limit.
- Names: PascalCase for classes/objects; camelCase for functions/vars; UPPER_SNAKE_CASE for constants.
- Files: one top-level class/object per file; match filename to class.
- Documentation: KDoc for public APIs; brief function comments for tricky logic.
- Imports/formatting: follow IntelliJ default formatter; run `Reformat Code` before committing.

## Testing Guidelines
- Framework: JUnit 5 with `org.junit.jupiter`.
- Naming: mirror source packages; test classes end with `Test` (e.g., `CurrentFragmentServiceTest`).
- Style: Given/When/Then in test method names (e.g., `shouldExtractCurrentFragment_whenCaretInsideRange`).
- Run locally via `./gradlew test`; target critical services and action handlers; prefer fast, unit-level tests.

## Commit & Pull Request Guidelines
- Commits: follow Conventional Commits where possible (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`).
- Scope small, message imperative mood; body explains rationale and user impact.
- PRs: include summary, motivation, linked issues, and screenshots/gifs for UI changes. Note IDE build and platform version tested (e.g., 2024.1).
- Checks: ensure `build`, `test`, and `verifyPlugin` pass.

## Security & Configuration Tips
- Do not commit secrets or local IDE configs. Exclude `.idea/`, build outputs, and sandbox directories.
- Keep `plugin.xml` minimal; read configuration from resources, not environment, at runtime.

## Agent-Specific Instructions
- When modifying files, keep to the structure above and avoid renames unless necessary.
- Prefer surgical diffs; update tests and `plugin.xml` together when adding new actions or services.
