import { readFileSync, writeFileSync } from 'node:fs';

const [inputPath, outputPath] = process.argv.slice(2);

if (!inputPath || !outputPath) {
  throw new Error('Usage: node add-company-identified-test-data.mjs <export.json> <repaired-parent.json>');
}

const exported = JSON.parse(readFileSync(inputPath, 'utf8'));
const workflows = Array.isArray(exported) ? exported : [exported];
const workflow = workflows.find((candidate) => candidate.name === '01 Email Monitoring');

if (!workflow) {
  throw new Error('Workflow "01 Email Monitoring" was not found in the export.');
}

if (!(workflow.nodes ?? []).some((node) => node.name === 'Company Identified')) {
  throw new Error('Workflow "01 Email Monitoring" needs a node named "Company Identified".');
}

const testApplication = {
  application_date: '2026-07-27',
  careers_url: '[https://jpmorganchase.com/careers](https://jpmorganchase.com/careers)',
  company: 'JPMorgan Chase & Co.',
  confidence: 'high',
  job_id: '210770939',
  job_title: 'Data Scientist [Multiple Positions Available]',
  location: '',
  type: 'full-time',
};

workflow.pinData ??= {};
workflow.pinData['Company Identified'] = [{ json: testApplication }];

writeFileSync(outputPath, `${JSON.stringify(workflow, null, 2)}\n`, 'utf8');
console.log(JSON.stringify({
  workflowId: workflow.id,
  workflowName: workflow.name,
  active: Boolean(workflow.active),
  pinnedNode: 'Company Identified',
  company: testApplication.company,
}));
