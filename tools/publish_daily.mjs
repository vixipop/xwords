#!/usr/bin/env node
// Publish the next queued issue as today's issue.
// Idempotent: does nothing if today's issue already exists or the queue is empty.
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const DATA = join(dirname(fileURLToPath(import.meta.url)), "..", "public", "data");
const read = (f) => JSON.parse(readFileSync(join(DATA, f), "utf8"));
const write = (f, obj) => writeFileSync(join(DATA, f), JSON.stringify(obj, null, 1));

const today = new Date().toISOString().slice(0, 10); // UTC YYYY-MM-DD

const index = existsSync(join(DATA, "index.json")) ? read("index.json") : [];
const queue = existsSync(join(DATA, "queue.json")) ? read("queue.json") : [];

if (index.some((e) => e.date === today)) {
  console.log(`Issue for ${today} already published — nothing to do.`);
  process.exit(0);
}
if (queue.length === 0) {
  console.log("Queue is empty — no issue to publish. Add more to public/data/queue.json.");
  process.exit(0);
}

const next = queue.shift();
const issue = { ...next, id: today, date: today };
write(`${today}.json`, issue);

index.push({ date: today, issue: next.issue, id: today, title: next.title, size: next.size });
index.sort((a, b) => (a.date < b.date ? 1 : -1)); // newest first
write("index.json", index);
write("queue.json", queue);

console.log(`Published issue No. ${next.issue} as ${today}. ${queue.length} left in queue.`);
