# 🔐 Sign-Off Skill for Claude

**Secure conversation closing** — A skill that lets Claude save what matters from a session before saying goodbye.

## What it does

When you type `/sign-off` (or variants like "wrap up", "save and quit", "let's call it"), Claude:

1. Scans the entire conversation
2. Extracts decisions, new data, pending tasks, and preferences
3. Saves them to memory for future sessions
4. Shows you a summary of what was saved
5. Says goodbye

## How to use

### As a Claude skill

Copy the `sign-off-skill/` folder to your skills directory:

```
/mnt/skills/user/sign-off/SKILL.md
```

### Triggers

Type any of these at the end of your session:

- `/sign-off`
- `"save and quit"`
- `"wrap up"`
- `"let's call it"`
- `"summarize and close"`

### Example output

```
📋 Session Summary

Saved for next time:
- You're building an API in FastAPI for your startup
- You prefer responses in Spanish with code in English

Pending items you mentioned:
- Add JWT authentication to the /users endpoint

Until next time! 👋
Good luck with the JWT! I'll be here when you need me.
```

## Safety

The skill **never** saves:
- Passwords or tokens
- API keys
- Specific financial data
- Personal ID numbers

## License

MIT
