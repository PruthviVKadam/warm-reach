import fs from 'node:fs';

const [inputPath, outputPath] = process.argv.slice(2);

if (!inputPath || !outputPath) {
  throw new Error('Usage: node add-boilerplate-email-composer.mjs <export.json> <repaired-workflow.json>');
}

const templatePath = new URL('./03-email-drafting.json', import.meta.url);
const template = JSON.parse(fs.readFileSync(templatePath, 'utf8'));
const exported = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
const workflows = Array.isArray(exported) ? exported : [exported];
const workflow = workflows.find((candidate) => candidate.name === '03 Email Drafting');

if (!workflow) {
  throw new Error('Could not find 03 Email Drafting in the n8n export.');
}

if (workflow.active) {
  throw new Error('03 Email Drafting is active. Deactivate it in n8n, rerun this helper, then reactivate it after review.');
}

const clone = (value) => JSON.parse(JSON.stringify(value));
const templateNodes = new Map(template.nodes.map((node) => [node.name, node]));
const liveNodes = new Map(workflow.nodes.map((node) => [node.name, node]));
const renamedNodes = new Map([
  ['Build Draft Prompt', 'Build Email Part Prompts'],
  ['Generate Draft With Ollama', 'Draft Subject'],
  ['Parse Draft JSON', 'Draft Opening'],
]);

for (const [oldName, newName] of renamedNodes) {
  const liveNode = liveNodes.get(newName) ?? liveNodes.get(oldName);
  const templateNode = templateNodes.get(newName);

  if (!liveNode || !templateNode) {
    throw new Error(`Expected ${oldName} and ${newName} while updating 03 Email Drafting.`);
  }

  const replacement = clone(templateNode);
  replacement.id = liveNode.id;
  const index = workflow.nodes.indexOf(liveNode);
  workflow.nodes[index] = replacement;
  if (oldName !== newName) {
    liveNodes.delete(oldName);
  }
  liveNodes.set(newName, replacement);
}

for (const name of ['Draft Relevant Point', 'Draft Call To Action', 'Assemble Boilerplate Email']) {
  if (!liveNodes.has(name)) {
    const templateNode = templateNodes.get(name);
    if (!templateNode) {
      throw new Error(`The workflow template is missing ${name}.`);
    }
    const addition = clone(templateNode);
    workflow.nodes.push(addition);
    liveNodes.set(name, addition);
  }
}

for (const name of ['Notification Recipient Configured']) {
  const liveNode = liveNodes.get(name);
  const templateNode = templateNodes.get(name);
  const replacement = clone(templateNode);

  if (liveNode) {
    replacement.id = liveNode.id;
    workflow.nodes[workflow.nodes.indexOf(liveNode)] = replacement;
  } else {
    workflow.nodes.push(replacement);
  }
  liveNodes.set(name, replacement);
}

const liveGmailDraft = liveNodes.get('Create Gmail Draft');
const liveNotification = liveNodes.get('Notify For Approval');
const notificationTemplate = templateNodes.get('Notify For Approval');

if (!liveGmailDraft || !liveNotification || !notificationTemplate) {
  throw new Error('Expected Gmail draft and approval notification nodes while updating 03 Email Drafting.');
}

const notificationReplacement = clone(notificationTemplate);
notificationReplacement.id = liveNotification.id;
if (liveGmailDraft.credentials?.gmailOAuth2) {
  notificationReplacement.credentials = { gmailOAuth2: clone(liveGmailDraft.credentials.gmailOAuth2) };
}
workflow.nodes[workflow.nodes.indexOf(liveNotification)] = notificationReplacement;
liveNodes.set('Notify For Approval', notificationReplacement);

for (const name of ['Workflow Input', 'Retrieve Memory', 'Create Gmail Draft', 'Notification Recipient Configured', 'Notify For Approval']) {
  const liveNode = liveNodes.get(name);
  const templateNode = templateNodes.get(name);
  if (liveNode && templateNode) {
    liveNode.position = clone(templateNode.position);
  }
}

workflow.connections = clone(template.connections);

const repaired = Array.isArray(exported) ? workflows : workflow;
fs.writeFileSync(outputPath, `${JSON.stringify(repaired, null, 2)}\n`);
console.log(JSON.stringify({ workflowId: workflow.id, updated: workflow.name }));
