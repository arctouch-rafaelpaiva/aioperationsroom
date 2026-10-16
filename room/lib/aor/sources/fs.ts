import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { parse } from "yaml";
import { eventPath, parseJsonl, toJsonl } from "../events";
import type { ProjectFile, RoomEvent } from "../types";
import { configFromYaml, DEFAULT_CONFIG, projectFromYaml, type OpsSource } from "./types";

async function list(dir: string): Promise<string[]> {
  try {
    return (await readdir(dir)).sort();
  } catch {
    return [];
  }
}

/** A local clone of the ops repo (AOR_OPS_DIR). Room writes land as files; commit and push them as usual. */
export function fsSource(root: string): OpsSource {
  return {
    kind: "fs",
    async listEvents() {
      const base = path.join(root, "aor", "room", "events");
      const out: RoomEvent[] = [];
      for (const day of await list(base)) {
        for (const file of await list(path.join(base, day))) {
          if (file.endsWith(".jsonl")) out.push(...parseJsonl(await readFile(path.join(base, day, file), "utf8")));
        }
      }
      return out;
    },
    async listProjects() {
      const base = path.join(root, "_bmad", "memory", "aor", "projects");
      const out: ProjectFile[] = [];
      for (const id of await list(base)) {
        try {
          const p = projectFromYaml(parse(await readFile(path.join(base, id, "project.yaml"), "utf8")));
          if (p) out.push(p);
        } catch {
          // An invalid project.yaml is aor-onboard-project's to report; the room skips it.
        }
      }
      return out;
    },
    async config() {
      try {
        return configFromYaml(parse(await readFile(path.join(root, "_bmad", "config.yaml"), "utf8")));
      } catch {
        return DEFAULT_CONFIG;
      }
    },
    async append(events, runId) {
      const file = path.join(root, eventPath(runId));
      await mkdir(path.dirname(file), { recursive: true });
      await writeFile(file, toJsonl(events), { flag: "a" });
    },
  };
}
