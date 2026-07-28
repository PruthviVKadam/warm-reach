import fs from 'node:fs';

const [sourcePath, targetPath, outputPath] = process.argv.slice(2);

if (!sourcePath || !targetPath || !outputPath) {
  throw new Error(
    'Usage: node attach-referral-reply-monitor-gmail-credential.mjs <email-monitoring-export.json> <reply-monitor-export.json> <updated-reply-monitor.json>',
  );
}

const asWorkflows = (value) => (Array.isArray(value) ? value : [value]);
const sourceExport = JSON.parse(fs.readFileSync(sourcePath, 'utf8'));
const targetExport = JSON.parse(fs.readFileSync(targetPath, 'utf8'));
const source = asWorkflows(sourceExport).find((workflow) => workflow.name === '01 Email Monitoring');
const target = asWorkflows(targetExport).find((workflow) => workflow.name === '08 Referral Reply Monitor');

if (!source || !target) {
  throw new Error('Expected exported workflows named "01 Email Monitoring" and "08 Referral Reply Monitor".');
}
if (target.active) {
  throw new Error('08 Referral Reply Monitor is active. Deactivate it before attaching credentials.');
}

const sourceTrigger = source.nodes?.find((node) => node.name === 'Gmail Trigger');
const targetTrigger = target.nodes?.find((node) => node.name === 'Gmail Trigger');
const gmailCredential = sourceTrigger?.credentials?.gmailOAuth2;

if (!gmailCredential || !targetTrigger) {
  throw new Error('Could not find the existing Gmail trigger credential or the referral reply monitor trigger.');
}

targetTrigger.credentials = {
  gmailOAuth2: JSON.parse(JSON.stringify(gmailCredential)),
};

fs.writeFileSync(outputPath, `${JSON.stringify(targetExport, null, 2)}\n`);
console.log(
  JSON.stringify({
    workflowId: target.id,
    workflowName: target.name,
    active: Boolean(target.active),
    credentialName: gmailCredential.name,
  }),
);
