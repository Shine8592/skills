import type { SkillVersion } from '../types/index';

const API_URL = 'https://vfbndmrgggrhnlrileqv.supabase.co/functions/v1/skills';
const STORAGE_API_URL = 'https://vfbndmrgggrhnlrileqv.supabase.co/storage/v1/object/skill-zips';

export interface Skill {
  name: string;
  display_name: string;
  description: string;
  category: string;
  author: string;
  github_url: string | null;
  degit_path: string;
  zip_path: string | null;
  download_count: number;
  version?: string;
}

export async function fetchSkills(): Promise<Skill[]> {
  const res = await fetch(`${API_URL}/list`);
  if (!res.ok) throw new Error(`Failed to fetch skills: ${res.statusText}`);
  return res.json() as Promise<Skill[]>;
}

export async function fetchSkillByName(name: string): Promise<Skill | null> {
  const res = await fetch(`${API_URL}/get?name=${encodeURIComponent(name)}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to fetch skill: ${res.statusText}`);
  return res.json() as Promise<Skill>;
}

export async function fetchSkillVersions(name: string): Promise<SkillVersion[]> {
  const res = await fetch(`${API_URL}/versions?name=${encodeURIComponent(name)}`);
  if (res.status === 404) return [];
  if (!res.ok) throw new Error(`Failed to fetch skill versions: ${res.statusText}`);
  return res.json() as Promise<SkillVersion[]>;
}

export async function trackDownload(skillName: string): Promise<void> {
  try {
    await fetch(`${API_URL}/track`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ skill_name: skillName }),
    });
  } catch {
    // Silently fail - don't block installation if tracking fails
  }
}

/**
 * Upload a skill zip to storage and register it in the DB.
 * Requires user ID and auth token for authorization.
 */
export async function uploadSkillZip(
  zipBuffer: Buffer,
  storagePath: string,
  token: string
): Promise<void> {
  const res = await fetch(`${STORAGE_API_URL}/${storagePath}`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/zip',
    },
    body: zipBuffer,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`Failed to upload skill zip: ${res.statusText}${body ? ` - ${body}` : ''}`);
  }
}

/**
 * Push (register or update) a skill in the registry.
 * If version is provided, creates a new version entry.
 */
export async function pushSkill(params: {
  name: string;
  displayName: string;
  description: string;
  category?: string;
  author: string;
  userId: string;
  token: string;
  version?: string;
  contentHash: string;
  zipPath: string;
}): Promise<{ skill: Skill; version?: SkillVersion }> {
  const res = await fetch(`${API_URL}/push`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${params.token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      name: params.name,
      display_name: params.displayName,
      description: params.description,
      category: params.category || 'general',
      author: params.author,
      user_id: params.userId,
      version: params.version,
      content_hash: params.contentHash,
      zip_path: params.zipPath,
    }),
  });

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`Failed to push skill: ${res.statusText}${body ? ` - ${body}` : ''}`);
  }

  return res.json() as Promise<{ skill: Skill; version?: SkillVersion }>;
}
