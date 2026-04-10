---
name: sign-off
description: >
  Secure conversation closing ritual. Triggers when the user types /sign-off,
  "sign off", "save and quit", "wrap up", "let's call it", "save what we discussed",
  "don't want to lose today's progress", "summarize and close", or any variant
  indicating they want to end the conversation while preserving important context.
  Use this skill whenever the user wants to leave in an orderly way, saving relevant
  information for future sessions. Even casual farewells like "gotta go, save this"
  or "heading out" combined with save intent should trigger this skill.
---

# Sign-Off: Secure Conversation Closing

## What it does

When the user signals they want to close the session, Claude runs a closing protocol that:

1. **Scans** the full conversation
2. **Extracts** what's worth remembering
3. **Saves** to memory using `memory_user_edits`
4. **Presents** a closing summary to the user
5. **Says goodbye** in a warm, personalized way

## Execution protocol

### Step 1: Conversation analysis

Review the entire thread and identify these categories:

- **Decisions made**: Anything the user decided or agreed upon
- **New personal data**: Name, job, preferences, location, projects, etc.
- **Pending tasks**: Things left to do or that the user mentioned they would do
- **Claude preferences**: How the user likes Claude to respond (tone, format, language)
- **Project context**: What they're working on, current state, next steps
- **Problems solved**: Solutions found that could be useful in future sessions

### Step 2: Save to memory

Use `memory_user_edits` with `view` command first to check what already exists and avoid duplicates.

Then use `add` for each new piece of information that is:
- **Lasting**: Not ephemeral or single-use
- **Useful**: Will help personalize future conversations
- **Concise**: Written in one clear line

Examples:
- `User is building a fitness app in React Native`
- `User prefers responses in Spanish with code in English`
- `User chose PostgreSQL over MongoDB for their project`

### Step 3: Present closing summary

Show the user a brief, friendly summary with this structure:

```
## Session Summary

**Saved for next time:**
- [short list of what was saved to memory]

**Pending items you mentioned:**
- [tasks or to-dos, if any]

**Until next time!**
[Brief, warm goodbye — personalized if there's context]
```

### Important rules

- **Never save sensitive information**: passwords, tokens, API keys, specific financial data, ID numbers
- **No duplicates**: If something is already in memory, don't add it again
- **Ask when in doubt**: If unsure whether something is worth saving, ask the user
- **Match language**: Respect the language the user used during the conversation
- **Trivial sessions**: If the conversation was light (just a greeting, a simple question), don't invent things to save. Say something like "Light session today — nothing new to save. See you next time!"
- **Brevity**: The closing summary should be short. No more than 10 lines.
