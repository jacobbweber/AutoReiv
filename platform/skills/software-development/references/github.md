# GitHub: git tools and the GitHub MCP server

Two separate things, set up separately by the operator.

## 1. git over HTTPS (`git_clone`, `git_pull`, `git_push`)
- Public repos need nothing.
- Private repos and pushes to github.com need a token: the operator sets `GITHUB_TOKEN` for the serve (Docker:
  `GITHUB_TOKEN=...` in `.env` next to `docker-compose.yml`, then `docker compose up -d`; native: the serve's
  environment). A fine-grained personal access token with **Contents: read and write** on the repos is enough.
- The tools pass the token to git through the process environment only. It is never written to `.git/config`, never
  in a URL and never in tool output. Never ask the operator to paste a token into chat or into a remote URL.
- `ssh://` and `git@github.com:` URLs need an SSH key on the serve; in Docker there is none, so prefer `https://`.
- `git_push` refuses `main`, `master` and `qa` and never forces: push a work branch, then open a pull request.

## 2. The GitHub MCP server (issues, pull requests, code search)
GitHub hosts an MCP server at `https://api.githubcopilot.com/mcp/`. The operator adds it once in **Capabilities ->
MCP servers -> Add server**:
1. Store a GitHub personal access token in the **Credential Vault** (**Manage in Vault**).
2. Server name `github`, transport **HTTP / SSE**, remote URL `https://api.githubcopilot.com/mcp/`.
3. Vault credential: that token; auth type **Bearer Token**.
4. Save. AutoReiv lists the server's tools and writes a companion `mcp-github` skill in the data folder. AutoReiv
   picks it up automatically (its `user:*` skills); open it with `skill_view(skill_id="mcp-github")`. Other agents
   need it ticked in **Agents**.

To offer fewer tools, use a toolset URL such as `https://api.githubcopilot.com/mcp/x/repos` or
`https://api.githubcopilot.com/mcp/x/issues`, or append `/readonly` for read-only tools.

## Which to use
- Getting code, syncing, sharing a branch: the git tools.
- Issues, pull requests, reviews, searching GitHub: the GitHub MCP server's tools, when it is added. If it is not,
  say so and give the operator the branch name and what the pull request should say.
