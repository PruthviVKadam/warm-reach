import { readFileSync, writeFileSync } from 'node:fs';

const [inputPath, outputPath] = process.argv.slice(2);

if (!inputPath || !outputPath) {
  throw new Error('Usage: node repair-subworkflow-references.mjs <export.json> <repaired-parent.json>');
}

const workflows = JSON.parse(readFileSync(inputPath, 'utf8'));

if (!Array.isArray(workflows)) {
  throw new Error('The n8n export must contain a workflow array.');
}

const targets = {
  'Save Application': '04 CRM Updates',
  'Research Recruiters': '02 Recruiter Research',
  'Draft Email For Approval': '03 Email Drafting',
};

const applicationInputFields = [
  'application_date',
  'careers_url',
  'company',
  'confidence',
  'job_id',
  'job_title',
  'location',
  'type',
];

function applicationWorkflowInputs() {
  return {
    mappingMode: 'defineBelow',
    value: Object.fromEntries(
      applicationInputFields.map((field) => [
        field,
        `={{$json.${field} || $items('Company Identified')[0].json.${field} || ''}}`,
      ]),
    ),
    matchingColumns: [],
    schema: applicationInputFields.map((field) => ({
      id: field,
      displayName: field,
      required: false,
      defaultMatch: false,
      display: true,
      canBeUsedToMatch: true,
      type: 'string',
      removed: false,
    })),
    attemptToConvertTypes: false,
    convertFieldsToString: false,
  };
}

const byName = new Map();
for (const workflow of workflows) {
  if (byName.has(workflow.name)) {
    throw new Error(`More than one workflow is named "${workflow.name}".`);
  }
  byName.set(workflow.name, workflow);
}

const parent = byName.get('01 Email Monitoring');
if (!parent) {
  throw new Error('Workflow "01 Email Monitoring" was not found in the export.');
}

const companyGuardName = 'Company Identified';
const companyGuardId = 'email-monitoring-company-identified';
const nodes = parent.nodes ?? [];
let companyGuardAdded = false;
let companyGuard = nodes.find((node) => node.name === companyGuardName);
if (!companyGuard) {
  companyGuard = {
    parameters: {
      conditions: {
        string: [{
          value1: '={{$json.company}}',
          operation: 'isNotEmpty',
        }],
      },
    },
    id: companyGuardId,
    name: companyGuardName,
    type: 'n8n-nodes-base.if',
    typeVersion: 2,
    position: [-80, -80],
  };
  nodes.push(companyGuard);
  parent.nodes = nodes;
  companyGuardAdded = true;
}

const newsletterConnection = parent.connections?.['Ignore Newsletters']?.main?.[0];
if (!newsletterConnection?.[0]) {
  throw new Error('Expected a true branch from "Ignore Newsletters".');
}
if (newsletterConnection[0].node === 'Save Application') {
  newsletterConnection[0].node = companyGuardName;
}
else if (newsletterConnection[0].node !== companyGuardName) {
  throw new Error('Expected the true branch of "Ignore Newsletters" to lead to "Save Application" or "Company Identified".');
}
parent.connections[companyGuardName] = {
  main: [[{ node: 'Save Application', type: 'main', index: 0 }]],
};

const repairedNodes = new Set();
for (const node of nodes) {
  const childName = targets[node.name];
  if (!childName) continue;
  if (node.type !== 'n8n-nodes-base.executeWorkflow') {
    throw new Error(`Node "${node.name}" must be an Execute Sub-workflow node.`);
  }

  const child = byName.get(childName);
  if (!child?.id) {
    throw new Error(`Workflow "${childName}" needs an n8n-generated ID before it can be linked.`);
  }

  node.typeVersion = 1.3;
  node.parameters = {
    source: 'database',
    workflowId: {
      __rl: true,
      value: child.id,
      mode: 'list',
      cachedResultName: childName,
    },
    workflowInputs: childName === '04 CRM Updates'
      ? applicationWorkflowInputs()
      : {
        mappingMode: 'defineBelow',
        value: {},
        matchingColumns: [],
        schema: [],
        attemptToConvertTypes: false,
        convertFieldsToString: false,
      },
    options: node.parameters?.options ?? { waitForSubWorkflow: true },
  };
  repairedNodes.add(node.name);
}

for (const nodeName of Object.keys(targets)) {
  if (!repairedNodes.has(nodeName)) {
    throw new Error(`Expected Execute Sub-workflow node "${nodeName}" was not found.`);
  }
}

writeFileSync(outputPath, `${JSON.stringify(parent, null, 2)}\n`, 'utf8');
console.log(JSON.stringify({
  workflowId: parent.id,
  workflowName: parent.name,
  active: Boolean(parent.active),
  companyGuardAdded,
  repairedNodes: [...repairedNodes],
}));
