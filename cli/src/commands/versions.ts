import chalk from 'chalk';
import ora from 'ora';
import { fetchSkillByName, fetchSkillVersions } from '../lib/supabase';

/**
 * List all versions of a skill from the registry.
 */
export async function versionsCommand(skillName: string): Promise<void> {
  const spinner = ora(`Fetching versions for ${skillName}...`).start();

  // First verify the skill exists
  const skill = await fetchSkillByName(skillName);
  if (!skill) {
    spinner.fail(`Skill "${skillName}" not found in the registry.`);
    console.log(chalk.gray('Run "sun list" to see available skills.'));
    return;
  }

  const versions = await fetchSkillVersions(skillName);
  spinner.stop();

  console.log(chalk.cyan(`${skill.display_name || skill.name}`));
  if (skill.description) {
    console.log(chalk.gray(skill.description));
  }
  if (skill.author) {
    console.log(chalk.gray(`by ${skill.author}`));
  }
  console.log();

  if (versions.length === 0) {
    console.log(chalk.yellow('No versioned releases found for this skill.'));
    console.log(chalk.gray('The skill is available but has no explicit version history.'));
    if (skill.version) {
      console.log(chalk.gray(`Current version from registry: ${skill.version}`));
    }
    return;
  }

  console.log(chalk.white(`Versions (${versions.length}):`));
  console.log();

  for (const ver of versions) {
    const date = new Date(ver.created_at).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });

    const latest = ver === versions[0] ? chalk.green(' (latest)') : '';
    console.log(`  ${chalk.bold(ver.version)}${latest}  ${chalk.gray(date)}`);

    if (ver.description) {
      console.log(`    ${chalk.gray(ver.description)}`);
    }

    console.log(`    ${chalk.gray(`hash: ${ver.content_hash}`)}`);

    if (ver.author) {
      console.log(`    ${chalk.gray(`by ${ver.author}`)}`);
    }
    console.log();
  }

  console.log(chalk.gray(`Install a specific version: sun add ${skillName}@<version>`));
  console.log(chalk.gray(`Install latest: sun add ${skillName}`));
}
