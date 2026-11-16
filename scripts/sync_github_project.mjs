import fs from "node:fs";
import path from "node:path";

const TOKEN = process.env.GITHUB_TOKEN;
if (!TOKEN) {
  console.error("ERROR: GITHUB_TOKEN environment variable is required.");
  process.exit(1);
}

const OWNER = "Nickddb";
const REPO = "NASA_Hackaton";
const PROJECT_NUMBER = 5;

async function ghGraphQL(query, variables = {}) {
  const res = await fetch("https://api.github.com/graphql", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      "Content-Type": "application/json",
      "User-Agent": "AstraCare-Project-Sync",
    },
    body: JSON.stringify({ query, variables }),
  });
  const json = await res.json();
  if (!res.ok || json.errors) {
    throw new Error(`GraphQL error (${res.status}): ${JSON.stringify(json.errors || json)}`);
  }
  return json.data;
}

function parseTasksFromMarkdown(mdPath) {
  const content = fs.readFileSync(mdPath, "utf8");
  const lines = content.split(/\r?\n/);
  let currentLevel = "";
  const tasks = [];

  for (const line of lines) {
    if (line.startsWith("## 🟢")) currentLevel = "🟢 Baixa";
    else if (line.startsWith("## 🟡")) currentLevel = "🟡 Média";
    else if (line.startsWith("## 🔴")) currentLevel = "🔴 Alta";

    const parts = line
      .split("|")
      .slice(1, -1)
      .map((s) => s.trim());
    if (parts.length < 7) continue;

    const idMatch = parts[0].match(/^\*\*(T\d+)\*\*$/);
    if (!idMatch) continue;

    const id = idMatch[1];
    const [, rawTitle, rawPrimary, rawFallback, area, deliverable, deps, rawStatus] = parts;
    const clean = (s) => (s || "").replace(/\*\*/g, "").trim();
    const shortModel = (s) =>
      s
        .replace(/`/g, "")
        .replace(/\s*\([^)]*-[^)]*\)/g, "")
        .replace(/Medium/g, "Med")
        .trim();

    const title = clean(rawTitle);
    const primary = clean(rawPrimary);
    const fallback = clean(rawFallback);
    const status = clean(rawStatus) || "Todo";

    tasks.push({
      id,
      level: currentLevel || "Task",
      status,
      cardTitle: `[${id}][${currentLevel}][${shortModel(primary)} | FB: ${shortModel(fallback)}] ${title}`,
      body: [
        `### ${id} — ${title}`,
        "",
        `- **Complexidade:** ${currentLevel}`,
        `- **Modelo Primário:** ${primary}`,
        `- **Modelo Fallback:** ${fallback}`,
        `- **Área:** ${clean(area)}`,
        `- **Dependências:** ${clean(deps)}`,
        `- **Status:** ${status}`,
        "",
        `#### Entregável`,
        clean(deliverable),
      ].join("\n"),
    });
  }
  return tasks;
}

async function main() {
  const tasksPath = path.resolve("TASKS.md");
  const tasks = parseTasksFromMarkdown(tasksPath);
  console.log(`Parsed ${tasks.length} tasks from TASKS.md.`);

  const projectQuery = `
    query($owner: String!, $repo: String!, $number: Int!) {
      repository(owner: $owner, name: $repo) {
        id
      }
      user(login: $owner) {
        projectV2(number: $number) {
          id
          title
          fields(first: 20) {
            nodes {
              ... on ProjectV2SingleSelectField {
                id
                name
                options {
                  id
                  name
                }
              }
            }
          }
          items(first: 100) {
            nodes {
              id
              content {
                __typename
                ... on Issue {
                  id
                  number
                  title
                }
                ... on DraftIssue {
                  id
                  title
                }
              }
            }
          }
        }
      }
    }
  `;

  const data = await ghGraphQL(projectQuery, {
    owner: OWNER,
    repo: REPO,
    number: PROJECT_NUMBER,
  });

  const repoId = data.repository?.id;
  const project = data.user?.projectV2;
  if (!repoId || !project) {
    throw new Error("Could not find repository or ProjectV2 #5.");
  }

  const statusField = project.fields.nodes.find((f) => f && f.name === "Status");
  const findStatusOption = (targetName) => {
    const normalized = (targetName || "Todo").toLowerCase();
    return (
      statusField?.options?.find((o) => o.name.toLowerCase() === normalized) ||
      statusField?.options?.find((o) => o.name.toLowerCase() === "todo")
    );
  };

  const existingItems = project.items.nodes
    .map((n) => ({
      itemId: n.id,
      type: n.content?.__typename,
      contentId: n.content?.id,
      number: n.content?.number,
      title: n.content?.title || "",
    }))
    .filter((i) => i.title);

  console.log(`Project "${project.title}" currently has ${existingItems.length} items.`);

  const createIssueMutation = `
    mutation($repositoryId: ID!, $title: String!, $body: String!) {
      createIssue(input: { repositoryId: $repositoryId, title: $title, body: $body }) {
        issue {
          id
          number
          url
        }
      }
    }
  `;

  const updateIssueMutation = `
    mutation($id: ID!, $title: String!, $body: String!) {
      updateIssue(input: { id: $id, title: $title, body: $body }) {
        issue {
          id
          number
          url
        }
      }
    }
  `;

  const updateDraftMutation = `
    mutation($draftIssueId: ID!, $title: String!, $body: String!) {
      updateProjectV2DraftIssue(input: { draftIssueId: $draftIssueId, title: $title, body: $body }) {
        draftIssue {
          id
          title
        }
      }
    }
  `;

  const addItemMutation = `
    mutation($projectId: ID!, $contentId: ID!) {
      addProjectV2ItemById(input: { projectId: $projectId, contentId: $contentId }) {
        item {
          id
        }
      }
    }
  `;

  const setStatusMutation = `
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
      updateProjectV2ItemFieldValue(
        input: {
          projectId: $projectId
          itemId: $itemId
          fieldId: $fieldId
          value: { singleSelectOptionId: $optionId }
        }
      ) {
        projectV2Item {
          id
        }
      }
    }
  `;

  let createdCount = 0;
  let updatedCount = 0;

  for (const task of tasks) {
    const statusOption = findStatusOption(task.status);
    const existing = existingItems.find((i) => i.title.includes(`[${task.id}]`));
    if (existing) {
      if (existing.type === "Issue" && existing.contentId) {
        const updRes = await ghGraphQL(updateIssueMutation, {
          id: existing.contentId,
          title: task.cardTitle,
          body: task.body,
        });
        console.log(`UPDATED ${task.id} -> Issue #${updRes.updateIssue.issue.number} [${task.status}]`);
        updatedCount++;
      } else if (existing.type === "DraftIssue" && existing.contentId) {
        await ghGraphQL(updateDraftMutation, {
          draftIssueId: existing.contentId,
          title: task.cardTitle,
          body: task.body,
        });
        console.log(`UPDATED ${task.id} -> DraftIssue [${task.status}]`);
        updatedCount++;
      }
      if (statusField && statusOption && existing.itemId) {
        await ghGraphQL(setStatusMutation, {
          projectId: project.id,
          itemId: existing.itemId,
          fieldId: statusField.id,
          optionId: statusOption.id,
        });
      }
      continue;
    }

    const issueRes = await ghGraphQL(createIssueMutation, {
      repositoryId: repoId,
      title: task.cardTitle,
      body: task.body,
    });
    const issue = issueRes.createIssue.issue;

    const itemRes = await ghGraphQL(addItemMutation, {
      projectId: project.id,
      contentId: issue.id,
    });
    const itemId = itemRes.addProjectV2ItemById.item.id;

    if (statusField && statusOption) {
      await ghGraphQL(setStatusMutation, {
        projectId: project.id,
        itemId,
        fieldId: statusField.id,
        optionId: statusOption.id,
      });
    }

    console.log(`CREATED ${task.id} -> Issue #${issue.number} (${issue.url}) [${task.status}]`);
    createdCount++;
  }

  console.log(`\nDone! Created: ${createdCount}, Updated: ${updatedCount}, Total tasks: ${tasks.length}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
