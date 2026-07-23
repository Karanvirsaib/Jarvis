# Aethon: Build Plan for an Iron Man JARVIS-Inspired Local Assistant

This document turns the earlier concept into a practical build plan for **Aethon**: a local-first assistant inspired by the Iron Man JARVIS style of calm, capable, always-available support.

## What Aethon should do

Aethon should be able to:

- answer questions in natural language;
- explain and generate code;
- modify files with user approval;
- launch and control supported apps;
- manage reminders, workflows, and task execution;
- coordinate multi-step agent work;
- speak in a composed, helpful, and concise style; and
- keep as much data local as possible.

## Build plan

### Step 1: Define the local runtime

**Goal:** Choose the local model and execution approach.

**Do this:**

- pick a local model runtime such as Ollama or another on-device inference server;
- define a default coding-capable model;
- confirm CPU/GPU requirements for the target machine;
- decide how prompts, chat history, and tool instructions will be formatted.

**Done when:**

- Aethon can load a local model and answer a basic prompt.

### Step 2: Build the chat core

**Goal:** Make the assistant answer questions reliably.

**Do this:**

- create a conversation loop;
- preserve short-term context;
- add system instructions that explain Aethon’s role;
- keep responses concise and actionable;
- add fallback behavior when the model is unavailable.

**Done when:**

- Aethon can hold a basic conversation without tools.

### Step 3: Add local memory

**Goal:** Store useful information on the user’s machine.

**Do this:**

- store preferences and facts locally;
- separate temporary chat state from persistent memory;
- add commands for remembering and forgetting items;
- make memory searchable and editable.

**Done when:**

- Aethon can remember user preferences and recall them later.

### Step 4: Add safe code assistance

**Goal:** Let Aethon help with development work.

**Do this:**

- add code generation prompts;
- support file reading and summarizing;
- support editing files only after confirmation;
- expose code review and refactoring helpers;
- avoid automatically executing generated code.

**Done when:**

- Aethon can explain code, propose changes, and prepare file edits safely.

### Step 5: Add task planning

**Goal:** Turn a user request into a sequence of steps.

**Do this:**

- add a planner that splits goals into smaller tasks;
- define task status states such as pending, active, blocked, and done;
- track what the assistant has already done;
- summarize progress after each task.

**Done when:**

- Aethon can take a goal and produce a clear task list.

### Step 6: Add app control tools

**Goal:** Let Aethon interact with supported desktop apps.

**Do this:**

- create tools for opening and focusing apps;
- add window switching and basic UI automation;
- limit actions to approved workflows;
- require confirmation for sensitive actions;
- log each action locally.

**Done when:**

- Aethon can open and control at least a few target apps safely.

### Step 7: Add agent execution

**Goal:** Let Aethon work through multi-step tasks.

**Do this:**

- add an agent loop that can plan, act, and report;
- let the agent request approval before risky steps;
- support retrying failed steps;
- show the user what the agent is doing in real time.

**Done when:**

- Aethon can complete multi-step tasks with human oversight.

### Step 8: Add workflow skills

**Goal:** Make Aethon more useful for repeated tasks.

**Do this:**

- create reusable skills for common app workflows;
- add templates for frequent goals;
- support local document search and summarization;
- allow custom user-defined skills.

**Done when:**

- Aethon can reuse task patterns instead of starting from scratch every time.

## Suggested architecture

### Assistant core

Responsible for conversation, reasoning, memory lookup, and tool selection.

### Tool layer

Provides controlled actions for files, apps, terminal commands, reminders, and task operations.

### Agent layer

Handles planning, step execution, approvals, retries, and progress reporting.

### Memory layer

Stores preferences, facts, task context, and skill notes locally.

### UI layer

Shows chat, tool activity, task state, and assistant responses.

## Safety rules

- Keep local processing as the default.
- Ask before destructive actions.
- Do not auto-run code unless the user explicitly allows it.
- Log important actions locally.
- Make it easy to review or undo work.
- Preserve a polished, trustworthy assistant personality without pretending to be human.

## Suggested project phases for Aethon

1. Local chat and memory
2. Safe coding help
3. App control
4. Task planning and agent workflows
5. Reusable skills and local document support

## Outcome

If built in this order, Aethon becomes a practical local assistant that feels JARVIS-inspired while staying private, controllable, and extensible.
