---
title: "Agent integrations"
description: "Install the planesnitch agent skill in Claude Code, Codex or OpenClaw, so an AI agent can write the config, set up watchlists and run the container for you."
nav_order: 10
---

# Agent integrations

The [`planesnitch` skill](https://github.com/psyb0t/docker-planesnitch/tree/main/.agents/skills/planesnitch) teaches an AI agent how to set planesnitch up: the config schema, watchlists, Telegram setup and the Docker commands. It works in any agent that reads `.agents/skills/`, such as [peen](https://github.com/psyb0t/peen), and installs natively in the clients below. planesnitch has no API for an agent to call; the skill is about configuring and running it.

## Claude Code

```bash
claude plugin marketplace add psyb0t/agents
claude plugin install planesnitch@psyb0t
```

## Codex

```bash
codex plugin marketplace add psyb0t/agents
codex plugin add planesnitch@psyb0t
```

Installed from the marketplace, it invokes as `$planesnitch:planesnitch`. In a repository that contains `.agents/skills/`, Codex also finds it as plain `$planesnitch` without installing anything.

## OpenClaw

The skill is published to ClawHub on every release:

```bash
openclaw skills install @psyb0t/planesnitch
```
