import { readFileSync, writeFileSync } from 'node:fs';

const [inputPath, outputPath] = process.argv.slice(2);

if (!inputPath || !outputPath) {
  throw new Error('Usage: node add-crm-company-guard.mjs <export.json> <repaired-crm-workflow.json>');
}

const exported = JSON.parse(readFileSync(inputPath, 'utf8'));
const workflows = Array.isArray(exported) ? exported : [exported];
const workflow = workflows.find((candidate) => candidate.name === '04 CRM Updates');

if (!workflow) {
  throw new Error('Workflow "04 CRM Updates" was not found in the export.');
}

const guardName = 'Company Provided';
const guardId = 'crm-company-provided';
const nodes = workflow.nodes ?? [];
const inputNode = nodes.find((node) => node.name === 'Workflow Input');
if (!inputNode || inputNode.type !== 'n8n-nodes-base.executeWorkflowTrigger') {
  throw new Error('Expected an Execute Workflow Trigger named "Workflow Input".');
}

const applicationInputExample = {
  application_date: '2026-07-27',
  careers_url: 'https://jpmorganchase.com/careers',
  company: 'JPMorgan Chase & Co.',
  confidence: 'high',
  job_id: '210770939',
  job_title: 'Data Scientist [Multiple Positions Available]',
  location: '',
  type: 'full-time',
};

let inputSchemaUpdated = false;
if (inputNode.typeVersion < 1.1 || !inputNode.parameters?.inputSource) {
  inputNode.typeVersion = 1.1;
  inputNode.parameters = {
    inputSource: 'jsonExample',
    jsonExample: JSON.stringify(applicationInputExample, null, 2),
  };
  inputSchemaUpdated = true;
}

let guardAdded = false;
let guard = nodes.find((node) => node.name === guardName);
if (!guard) {
  guard = {
    parameters: {
      conditions: {
        string: [{
          value1: '={{$json.company}}',
          operation: 'isNotEmpty',
        }],
      },
    },
    id: guardId,
    name: guardName,
    type: 'n8n-nodes-base.if',
    typeVersion: 2,
    position: [-560, 0],
  };
  nodes.push(guard);
  workflow.nodes = nodes;
  guardAdded = true;
}

const inputConnection = workflow.connections?.['Workflow Input']?.main?.[0];
if (!inputConnection?.[0]) {
  throw new Error('Expected a connection from "Workflow Input".');
}
if (inputConnection[0].node === 'Initialize CRM') {
  inputConnection[0].node = guardName;
}
else if (inputConnection[0].node !== guardName) {
  throw new Error('Expected "Workflow Input" to lead to "Initialize CRM" or "Company Provided".');
}
workflow.connections[guardName] = {
  main: [[{ node: 'Initialize CRM', type: 'main', index: 0 }]],
};

writeFileSync(outputPath, `${JSON.stringify(workflow, null, 2)}\n`, 'utf8');
console.log(JSON.stringify({
  workflowId: workflow.id,
  workflowName: workflow.name,
  active: Boolean(workflow.active),
  guardAdded,
  inputSchemaUpdated,
}));
