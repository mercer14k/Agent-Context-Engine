# Publish your local repository

The local repository is named `agent-context-engine` and uses branch `main`. No remote is configured and nothing has been uploaded. Project files are staged for your first commit; local databases, environment files, virtual environments, browser downloads, and build outputs are excluded by `.gitignore`.

## 1. Set your commit email

Open a terminal in the repository directory. Your local author name is configured as `Rushi Rane`. Set an email you want attached to commits, such as the no-reply address shown in your GitHub email settings:

```sh
git config --local user.email "YOUR_COMMIT_EMAIL"
```

Replace the placeholder before running the command. This changes only this repository's configuration.

## 2. Review and make the first commit

```sh
git status
git diff --cached --stat
git commit -m "Initial release: Agent Context Engine developer preview"
```

Before public release, review the proposed Apache-2.0 license and the project name as noted in NOTICE. The README distinguishes measured offline results from unverified live-provider claims.

## 3. Create an empty GitHub repository

Create a repository named `agent-context-engine` under your own account. Choose its visibility. Leave GitHub's automatic README, license, and gitignore options unchecked: those files already exist locally.

Suggested About description:

> Local-first context optimization for Python AI agents. Deterministic transforms, exact task scoping, CLI/SDK/MCP, and a local dashboard for workflow evidence.

Suggested topics:

`ai-agents`, `context-engineering`, `context-compression`, `token-optimization`, `local-first`, `python`, `mcp`, `llm`, `observability`, `developer-tools`

These are descriptive suggestions, not claims of supported integrations beyond this preview.

## 4. Connect and upload

Replace `YOUR_USERNAME` with the account or organization that owns your new repository:

```sh
git remote add origin https://github.com/YOUR_USERNAME/agent-context-engine.git
git push -u origin main
```

If you already added a remote, inspect `git remote -v` before changing it. After upload, check the Actions tab for the first hosted test results. The committed test report records a local run, not hosted CI execution.

## 5. Prepare a public release when ready

- Confirm the license/name decision, establish private vulnerability reporting, and update the preview status in README, NOTICE, SECURITY, and the status document as appropriate.
- Once a real repository URL exists, add it to package metadata and the README clone instructions.
- Use the included issue forms and pull request template to collect reproducible contributions.
- Attach the wheel and source archive from `dist/` to a release if desired. Local archives are build outputs, not tracked source files.
- Keep benchmark boundaries and synthetic labels intact when sharing results.

## Rebuild packages locally

With the project environment active and build dependencies installed:

```sh
python -m pip wheel --no-build-isolation --no-deps --wheel-dir dist .
python -c "from setuptools.build_meta import build_sdist; build_sdist('dist')"
```

`MANIFEST.in` includes documentation, examples, tests, benchmarks, integration bundles, reports, and third-party notices in the source distribution. The wheel includes the runtime code and dashboard assets.
