# Aethon Architecture

## Overview

Aethon should use a simple layered architecture so conversation, memory, tools, and agents stay easy to maintain.

## Layers

### 1. Assistant core

Responsible for:

- conversation;
- reasoning;
- prompt assembly;
- memory lookup; and
- deciding whether to use a tool.

### 2. Memory layer

Responsible for:

- storing user preferences;
- storing reusable facts;
- tracking task context; and
- keeping session state separate from long-term memory.

### 3. Tool layer

Responsible for:

- file actions;
- app control;
- terminal commands;
- reminders;
- workflow actions; and
- other approved operations.

### 4. Agent layer

Responsible for:

- splitting goals into steps;
- executing approved actions;
- tracking progress;
- handling retries; and
- reporting results.

### 5. UI layer

Responsible for:

- chat input;
- task status visibility;
- tool activity display; and
- optional voice support.

## Design rules

- Keep local processing as the default.
- Require approval for sensitive actions.
- Avoid silent execution.
- Make tool use visible.
- Keep the system easy to extend.
