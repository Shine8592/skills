import chalk from 'chalk';
import ora from 'ora';
import fs from 'fs-extra';
import path from 'path';
import os from 'os';
import AdmZip from 'adm-zip';
import { readSkillMetadata, findSkillDirectories } from '../core/skill-info';
import { computeContentHash } from '../core/skill-hash';
import { uploadSkillZip, pushSkill, fetchSkillByName } from '../lib/supabase';
import type { PushFlags } from '../types/index';

/**
 * Package a skill directory into a zip buffer.
 */
async function packageSkill(skillDir: string): Promise<Buffer> {
  const zip = new AdmZip();

  async function addDirectory(dir: string, zipPath: string): Promise<void> {
    const entries = await fs.readdir(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      const entryZipPath = zipPath ? `${zipPath}/${entry.name}` : entry.name;

      if (entry.isDirectory()) {
        if (entry.name === '.git' || entry.name === 'node_modules') continue;
        await addDirectory(fullPath, entryZipPath);
      } else if (entry.isFile()) {
        const content = await fs.readFile(fullPath);
        zip.addFile(entryZipPath, content);
      }
    }
  }

  await addDirectory(skillDir, '');
  return zip.toBuffer();
}

/**
 * Push a skill from a local path to the registry.
 * Requires authentication via user ID and token.
 */
export async function pushCommand(skillPath: string, flags: PushFlags): Promise<void> {
  // Resolve the skill path
  let resolvedPath = skillPath;
  if (resolvedPath.startsWith('~/')) {
    resolvedPath = path.join(os.homedir(), resolvedPath.slice(2));
  }
  resolvedPath = path.resolve(resolvedPath);

  if (!await fs.pathExists(resolvedPath)) {
    throw new Error(`Path does not exist: ${resolvedPath}`);
  }

  // Find skills in the given path
  const spinner = ora('Scanning for skills...').start();
  const skillDirs = await findSkillDirectories(resolvedPath);

  if (skillDirs.length === 0) {
    spinner.fail(`No skills found at "${skillPath}". A skill must contain a SKILL.md file with name in frontmatter.`);
    return;
  }

  spinner.stop();

  // Push each skill found
  for (const skillDir of skillDirs) {
    const metadata = await readSkillMetadata(skillDir);
    if (!metadata) {
      console.log(chalk.yellow(`Skipping ${skillDir}: invalid SKILL.md`));
      continue;
    }

    const pushSpinner = ora(`Pushing ${metadata.name}...`).start();

    try {
      // Compute content hash
      const contentHash = await computeContentHash(skillDir);

      // Determine version: explicit flag > metadata > content hash
      const version = flags.version
        || metadata.metadata?.version
        || contentHash;

      // Package the skill into a zip
      const zipBuffer = await packageSkill(skillDir);
      const storagePath = flags.version
        ? `${metadata.name}/${metadata.name}-${version}.zip`
        : `${metadata.name}/${metadata.name}.zip`;

      // Upload the zip to storage
      pushSpinner.text = `Uploading ${metadata.name} (${(zipBuffer.length / 1024).toFixed(1)} KB)...`;
      await uploadSkillZip(zipBuffer, storagePath, flags.token);

      // Register the skill in the DB
      pushSpinner.text = `Registering ${metadata.name}...`;
      const result = await pushSkill({
        name: metadata.name,
        displayName: metadata.metadata?.display_name || metadata.name,
        description: flags.description || metadata.description || '',
        category: metadata.metadata?.category,
        author: metadata.metadata?.author || '',
        userId: flags.userId,
        token: flags.token,
        version,
        contentHash,
        zipPath: storagePath,
      });

      pushSpinner.succeed(`Pushed ${metadata.name}`);

      // Display summary
      console.log();
      console.log(chalk.white(`  Name:    ${result.skill.name}`));
      console.log(chalk.white(`  Version: ${version}`));
      console.log(chalk.white(`  Hash:    ${contentHash}`));
      console.log(chalk.gray(`  Zip:     ${storagePath}`));

      if (result.version) {
        console.log(chalk.gray(`  Version ID: ${result.version.id}`));
      }
      console.log();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      pushSpinner.fail(`Failed to push ${metadata.name}: ${message}`);
    }
  }

  // Check for existing skill to show update vs create context
  if (skillDirs.length === 1) {
    const metadata = await readSkillMetadata(skillDirs[0]);
    if (metadata) {
      const existing = await fetchSkillByName(metadata.name).catch(() => null);
      if (existing) {
        console.log(chalk.gray(`Updated existing skill "${metadata.name}" in the registry.`));
      } else {
        console.log(chalk.green(`Published new skill "${metadata.name}" to the registry.`));
      }
      console.log(chalk.gray(`Others can install it with: sun add ${metadata.name}`));
    }
  }
}
