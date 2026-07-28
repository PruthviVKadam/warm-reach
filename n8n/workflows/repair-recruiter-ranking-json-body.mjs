import { readFileSync, writeFileSync } from 'node:fs';

const [inputPath, outputPath] = process.argv.slice(2);

if (!inputPath || !outputPath) {
  throw new Error('Usage: node repair-recruiter-ranking-json-body.mjs <export.json> <repaired-research-workflow.json>');
}

const exported = JSON.parse(readFileSync(inputPath, 'utf8'));
const workflows = Array.isArray(exported) ? exported : [exported];
const workflow = workflows.find((candidate) => candidate.name === '02 Recruiter Research');

if (!workflow) {
  throw new Error('Workflow "02 Recruiter Research" was not found in the export.');
}

const rankNode = (workflow.nodes ?? []).find((node) => node.name === 'Rank Recruiters');
if (!rankNode || rankNode.type !== 'n8n-nodes-base.httpRequest') {
  throw new Error('Expected an HTTP Request node named "Rank Recruiters".');
}

rankNode.parameters.jsonBody = "={{ JSON.stringify({ company: $json.company || '', job_title: $json.job_title || '', location: $json.location || '', recruiters: $json.recruiters || [] }) }}";

writeFileSync(outputPath, `${JSON.stringify(workflow, null, 2)}\n`, 'utf8');
console.log(JSON.stringify({
  workflowId: workflow.id,
  workflowName: workflow.name,
  active: Boolean(workflow.active),
  repairedNode: rankNode.name,
}));
