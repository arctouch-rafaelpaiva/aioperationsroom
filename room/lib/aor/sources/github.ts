import { parse } from "yaml";
import { eventPath, parseJsonl, toJsonl } from "../events";
import type { ProjectFile, RoomEvent } from "../types";
import { configFromYaml, DEFAULT_CONFIG, projectFromYaml, type OpsSource } from "./types";

interface TreeEntry {
  path: string;
  type: string;
  sha: string;
}

const TREE_TTL_MS = 10_000;

interface Cache {
  tree?: { at: number; entries: TreeEntry[] };
  blobs: Map<string, string>;
}

const caches: Map<string, Cache> = ((globalThis as { __aorGithubCache?: Map<string, Cache> }).__aorGithubCache ??= new Map());

/** The ops repo through the GitHub REST API (AOR_GITHUB_REPO, AOR_GITHUB_TOKEN, AOR_GITHUB_BRANCH). */
export function githubSource(repo: string, token: string, branch = "main"): OpsSource {
  const cache: Cache = caches.get(repo) ?? { blobs: new Map() };
  caches.set(repo, cache);

  async function gh(url: string, init: RequestInit = {}) {
    const res = await fetch(`https://api.github.com/repos/${repo}${url}`, {
      ...init,
      cache: "no-store",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${token}`,
        "X-GitHub-Api-Version": "2022-11-28",
        ...(init.headers ?? {}),
      },
    });
    if (!res.ok) throw new Error(`GitHub ${init.method ?? "GET"} ${url}: ${res.status} ${(await res.text()).slice(0, 200)}`);
    return res.json();
  }

  async function tree(): Promise<TreeEntry[]> {
    if (cache.tree && Date.now() - cache.tree.at < TREE_TTL_MS) return cache.tree.entries;
    const body = await gh(`/git/trees/${encodeURIComponent(branch)}?recursive=1`);
    cache.tree = { at: Date.now(), entries: (body.tree as TreeEntry[]).filter((e) => e.type === "blob") };
    return cache.tree.entries;
  }

  async function blob(sha: string): Promise<string> {
    const hit = cache.blobs.get(sha);
    if (hit !== undefined) return hit;
    const body = await gh(`/git/blobs/${sha}`);
    const text = Buffer.from(body.content, "base64").toString("utf8");
    cache.blobs.set(sha, text);
    return text;
  }

  const read = async (pattern: RegExp) => {
    const entries = (await tree()).filter((e) => pattern.test(e.path));
    return Promise.all(entries.map(async (e) => ({ path: e.path, text: await blob(e.sha) })));
  };

  return {
    kind: "github",
    async listEvents() {
      const files = await read(/^aor\/room\/events\/[^/]+\/[^/]+\.jsonl$/);
      return files.flatMap((f) => parseJsonl(f.text));
    },
    async listProjects() {
      const files = await read(/^_bmad\/memory\/aor\/projects\/[^/]+\/project\.yaml$/);
      const out: ProjectFile[] = [];
      for (const f of files) {
        try {
          const p = projectFromYaml(parse(f.text));
          if (p) out.push(p);
        } catch {
          // aor-onboard-project reports invalid project files.
        }
      }
      return out;
    },
    async config() {
      const [f] = await read(/^_bmad\/config\.yaml$/);
      try {
        return f ? configFromYaml(parse(f.text)) : DEFAULT_CONFIG;
      } catch {
        return DEFAULT_CONFIG;
      }
    },
    async append(events: RoomEvent[], runId: string) {
      const file = eventPath(runId);
      const what = events.map((e) => `${(e.data.decision as string) ?? e.type} ${(e.data.item as string) ?? ""}`.trim()).join(", ");
      await gh(`/contents/${file}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: `aor room: ${what}`,
          content: Buffer.from(toJsonl(events)).toString("base64"),
          branch,
        }),
      });
      cache.tree = undefined;
    },
  };
}
