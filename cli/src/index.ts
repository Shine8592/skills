#!/usr/bin/env node

import { Command } from 'commander';
import chalk from 'chalk';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);
const { version } = require('../package.json');
import { SUPPORTED_AGENTS } from './core/agents';
import { addCommand } from './commands/add';
import { removeCommand } from './commands/remove';
import { listCommand } from './commands/list';
import { listRegistryCommand } from './commands/list-registry';
import { showCommand } from './commands/show';
import { configCommand } from './commands/config';
import { pullCommand } from './commands/pull';
import { versionsCommand } from './commands/versions';
import { pushCommand } from './commands/push';
import { suggestCommand, getValidCommands } from './utils/fuzzy-match';
import type { CommandFlags, PushFlags } from './types/index';

const program = new Command();

function isPromptExit(error: unknown): boolean {
  return error instanceof Error && error.name === 'ExitPromptError';
}

function handleCommandError(error: unknown): never {
  // Quietly exit when user cancels an interactive prompt (Ctrl+C / SIGINT).
  if (isPromptExit(error)) {
    process.exit(130);
  }

  console.error(chalk.red(error instanceof Error ? error.message : String(error)));
  process.exit(1);
}

program
  .name('sun')
  .description('Sundial CLI - Manage skills for your AI agents')
  .version(version);

// Add command
const add = program
  .command('add <skills...>')
  .description('Add skill(s) to agent configuration(s)')
  .option('--global', 'Install to global agent config (~/.claude/, ~/.codex/, etc.)');

// Add agent flags dynamically
for (const agent of SUPPORTED_AGENTS) {
  add.option(`--${agent.flag}`, `Install to ${agent.name}`);
}

add.action(async (skills: string[], options: CommandFlags) => {
  try {
    await addCommand(skills, options);
  } catch (error) {
    handleCommandError(error);
  }
});

// Remove command
const remove = program
  .command('remove <skills...>')
  .description('Remove skill(s) from agent configuration(s)')
  .option('--global', 'Remove from global config');

for (const agent of SUPPORTED_AGENTS) {
  remove.option(`--${agent.flag}`, `Remove from ${agent.name}`);
}

remove.action(async (skills: string[], options: CommandFlags) => {
  try {
    await removeCommand(skills, options);
  } catch (error) {
    handleCommandError(error);
  }
});

// List command (registry)
program
  .command('list')
  .description('List available skills from the registry')
  .action(async () => {
    try {
      await listRegistryCommand();
    } catch (error) {
      handleCommandError(error);
    }
  });

// Installed command (alias for installed skills)
program
  .command('installed')
  .alias('list-installed')
  .description('List installed skills for each agent')
  .action(async () => {
    try {
      await listCommand();
    } catch (error) {
      handleCommandError(error);
    }
  });

// Show command
program
  .command('show [skill]')
  .description('Show all agent folders and packages, or details for a specific skill')
  .action(async (skill?: string) => {
    try {
      await showCommand(skill);
    } catch (error) {
      handleCommandError(error);
    }
  });

// Config command
program
  .command('config')
  .description('Configure default agents')
  .action(async () => {
    try {
      await configCommand();
    } catch (error) {
      handleCommandError(error);
    }
  });

// Pull command
const pull = program
  .command('pull [skill]')
  .description('Pull all skills (or a specific skill) from the registry')
  .option('--global', 'Install to global agent config (~/.claude/, ~/.codex/, etc.)');

for (const agent of SUPPORTED_AGENTS) {
  pull.option(`--${agent.flag}`, `Install to ${agent.name}`);
}

pull.action(async (skill: string | undefined, options: CommandFlags) => {
  try {
    await pullCommand(skill, options);
  } catch (error) {
    handleCommandError(error);
  }
});

// Versions command
program
  .command('versions <skill>')
  .description('List all versions of a skill from the registry')
  .action(async (skill: string) => {
    try {
      await versionsCommand(skill);
    } catch (error) {
      handleCommandError(error);
    }
  });

// Push command
program
  .command('push <path>')
  .description('Push a skill to the registry (requires authentication)')
  .requiredOption('--user-id <id>', 'Your user ID for authentication')
  .requiredOption('--token <token>', 'Your auth token')
  .option('--version <version>', 'Explicit version string (e.g., 1.0.0)')
  .option('--description <description>', 'Description override for the skill')
  .action(async (skillPath: string, options: PushFlags) => {
    try {
      await pushCommand(skillPath, options);
    } catch (error) {
      handleCommandError(error);
    }
  });

// Handle unknown commands with fuzzy matching
program.on('command:*', (operands) => {
  const unknownCommand = operands[0];
  const suggestion = suggestCommand(unknownCommand);

  console.error(chalk.red(`Error: Unknown command '${unknownCommand}'`));

  if (suggestion) {
    console.error(chalk.yellow(`Did you mean '${suggestion}'?`));
  }

  console.error();
  console.error(`Valid commands: ${getValidCommands().join(', ')}`);
  process.exit(1);
});

// Parse and execute
program.parse();
