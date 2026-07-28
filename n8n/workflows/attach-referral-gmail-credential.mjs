import fs from 'node:fs';

const [sourcePath, targetPath, outputPath] = process.argv.slice(2);

if (!sourcePath || !targetPath || !outputPath) {
  throw new Error(
    'Usage: node attach-referral-gmail-credential.mjs <drafting-export.json> <referral-export.json> <updated-referral.json>',
  );
}

const asWorkflows = (value) => (Array.isArray(value) ? value : [value]);
const sourceExport = JSON.parse(fs.readFileSync(sourcePath, 'utf8'));
const targetExport = JSON.parse(fs.readFileSync(targetPath, 'utf8'));
const source = asWorkflows(sourceExport).find((workflow) => workflow.name === '03 Email Drafting');
const target = asWorkflows(targetExport).find((workflow) => workflow.name === '07 Referral Outreach');

if (!source || !target) {
  throw new Error('Expected exported workflows named "03 Email Drafting" and "07 Referral Outreach".');
}
if (target.active) {
  throw new Error('07 Referral Outreach is active. Deactivate it before attaching credentials.');
}

const sourceDraft = source.nodes?.find((node) => node.name === 'Create Gmail Draft');
const targetDraft = target.nodes?.find((node) => node.name === 'Create Referral Gmail Draft');
const gmailCredential = sourceDraft?.credentials?.gmailOAuth2;

if (!gmailCredential || !targetDraft) {
  throw new Error('Could not find the existing Gmail draft credential or the referral draft node.');
}

targetDraft.credentials = {
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
