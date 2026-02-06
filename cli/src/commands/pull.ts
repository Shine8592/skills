import chalk from 'chalk';
import ora from 'ora';
import { getAgentByFlag, SUPPORTED_AGENTS } from '../core/agents';
import { isFirstRun, getDefaultAgents, setDefaultAgents } from '../core/config-manager';
import { detectLocalAgents } from '../core/agent-detect';
import { getSkillInstallPath, installSkill, type ConfirmSkillOverride } from '../core/skill-install';
import { promptAgentSelection, promptSkillOverride } from '../utils/prompts';
import { getSkillsFromRegistry } from '../utils/registry';
import type { AgentType, CommandFlags } from '../types/index';

/**
 * Determine which agents to install to and whether to install globally.
 * Same logic as the add command.
 */
async function resolveTargetAgents(flags: CommandFlags): Promise<{ agents: AgentType[]; isGlobal: boolean }> {
  const forceGlobal = flags.global ?? false;

  const explicitAgents: AgentType[] = [];
  for (const agent of SUPPORTED_AGENTS) {
    if (flags[agent.flag as keyof CommandFlags]) {
      explicitAgents.push(agent.flag as AgentType);
    }
  }

  let targetAgents: AgentType[];

  if (explicitAgents.length > 0) {
    targetAgents = explicitAgents;
  } else if (await isFirstRun()) {
    const selectedAgents = await promptAgentSelection();
    await setDefaultAgents(selectedAgents);
    targetAgents = selectedAgents;
  } else {
    const defaultAgents = await getDefaultAgents();
    if (defaultAgents.length === 0) {
      throw new Error('No default agents configured. Run "sun config" to set up your agents.');
    }
    targetAgents = defaultAgents;
  }

  if (forceGlobal) {
    return { agents: targetAgents, isGlobal: true };
  }

  const localAgents = await detectLocalAgents();
  const localAgentFlags = new Set(localAgents.map(a => a.agent.flag));
  const hasLocalFolders = targetAgents.some(agentFlag => localAgentFlags.has(agentFlag));
  const isGlobal = !hasLocalFolders;

  return { agents: targetAgents, isGlobal };
}

/**
 * Pull all skills (or a specific skill) from the registry.
 * Installs each to the configured agents.
 */
export async function pullCommand(skillName: string | undefined, flags: CommandFlags): Promise<void> {
  const { agents, isGlobal } = await resolveTargetAgents(flags);

  // Get skills to pull
  const listSpinner = ora('Fetching skills from registry...').start();
  const allSkills = await getSkillsFromRegistry();
  listSpinner.stop();

  if (allSkills.length === 0) {
    console.log(chalk.yellow('No skills available in the registry.'));
    return;
  }

  // Filter to a specific skill if requested
  const skillsToPull = skillName
    ? allSkills.filter(s => s.name === skillName)
    : allSkills;

  if (skillsToPull.length === 0) {
    console.log(chalk.red(`Skill "${skillName}" not found in the registry.`));
    console.log(chalk.gray('Run "sun list" to see available skills.'));
    return;
  }

  console.log(chalk.cyan(`Pulling ${skillsToPull.length} skill${skillsToPull.length === 1 ? '' : 's'} from registry...`));
  console.log();

  let successCount = 0;
  let failCount = 0;

  for (const skill of skillsToPull) {
    const spinner = ora(`Pulling ${skill.name}...`).start();

    const confirmOverride: ConfirmSkillOverride = async params => {
      if (spinner.isSpinning) {
        spinner.stop();
      }
      return promptSkillOverride(params);
    };

    try {
      for (const agentFlag of agents) {
        await installSkill(skill.name, agentFlag, isGlobal, confirmOverride);
      }
      spinner.succeed(`Pulled ${skill.name}`);
      successCount++;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      spinner.fail(`Failed to pull ${skill.name}: ${message}`);
      failCount++;
    }
  }

  // Summary
  console.log();
  const agentNames = agents.map(a => getAgentByFlag(a)?.name).filter(Boolean);
  const location = isGlobal ? '(global)' : '(local)';

  if (successCount > 0) {
    console.log(chalk.green(`Successfully pulled ${successCount} skill${successCount === 1 ? '' : 's'} to ${agentNames.join(' and ')} ${chalk.gray(location)}`));
  }
  if (failCount > 0) {
    console.log(chalk.red(`Failed to pull ${failCount} skill${failCount === 1 ? '' : 's'}`));
  }
}
