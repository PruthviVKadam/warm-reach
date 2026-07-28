import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from recruiting_ai.workflow_validate import validate_all


class WorkflowTests(unittest.TestCase):
    def test_workflow_exports_validate(self):
        errors = validate_all(ROOT / "n8n" / "workflows")
        self.assertEqual(errors, [])

    def test_expected_workflow_count(self):
        workflows = sorted((ROOT / "n8n" / "workflows").glob("*.json"))
        self.assertEqual(len(workflows), 8)

    def test_referral_reply_monitor_is_inactive_and_review_first(self):
        workflow = json.loads((ROOT / "n8n" / "workflows" / "08-referral-reply-monitor.json").read_text(encoding="utf-8"))
        nodes = {node["name"]: node for node in workflow["nodes"]}

        self.assertEqual(workflow["name"], "08 Referral Reply Monitor")
        self.assertFalse(workflow["active"])
        self.assertEqual(nodes["Gmail Trigger"]["parameters"]["filters"]["readStatus"], "unread")
        self.assertIn("from_email", nodes["Normalize Inbox Message"]["parameters"]["jsCode"])
        self.assertIn("/api/referral-replies/match", nodes["Match Sent Referral Asks"]["parameters"]["url"])
        self.assertNotIn("n8n-nodes-base.emailSend", [node["type"] for node in workflow["nodes"]])
        self.assertEqual(
            workflow["connections"]["Normalize Inbox Message"]["main"][0][0]["node"],
            "Match Sent Referral Asks",
        )

    def test_referral_outreach_workflow_creates_a_draft_and_saves_its_details(self):
        workflow = json.loads((ROOT / "n8n" / "workflows" / "07-referral-outreach.json").read_text(encoding="utf-8"))
        nodes = {node["name"]: node for node in workflow["nodes"]}

        self.assertEqual(workflow["name"], "07 Referral Outreach")
        self.assertEqual(nodes["Create Referral Gmail Draft"]["parameters"]["resource"], "draft")
        self.assertEqual(nodes["Create Referral Gmail Draft"]["parameters"]["operation"], "create")
        self.assertIn("at most 7 words", nodes["Build Referral Email Prompts"]["parameters"]["jsCode"])
        self.assertIn("Best,\\nPruthvi Kadam", nodes["Assemble Referral Boilerplate"]["parameters"]["jsCode"])
        self.assertIn("/api/referral-asks", nodes["Save Referral Ask"]["parameters"]["url"])
        self.assertIn("/api/referral-asks/draft", nodes["Save Referral Draft"]["parameters"]["url"])
        self.assertEqual(
            workflow["connections"]["Workflow Input"]["main"][0][0]["node"],
            "Save Referral Ask",
        )
        self.assertEqual(
            workflow["connections"]["Assemble Referral Boilerplate"]["main"][0][0]["node"],
            "Create Referral Gmail Draft",
        )
        self.assertEqual(
            workflow["connections"]["Create Referral Gmail Draft"]["main"][0][0]["node"],
            "Save Referral Draft",
        )

    def test_referral_gmail_credential_helper_is_present(self):
        helper = (ROOT / "n8n" / "workflows" / "attach-referral-gmail-credential.mjs").read_text(encoding="utf-8")

        self.assertIn("03 Email Drafting", helper)
        self.assertIn("07 Referral Outreach", helper)
        self.assertIn("Create Referral Gmail Draft", helper)
        self.assertIn("gmailOAuth2", helper)
        self.assertIn("target.active", helper)

    def test_referral_reply_monitor_gmail_credential_helper_is_present(self):
        helper = (
            ROOT / "n8n" / "workflows" / "attach-referral-reply-monitor-gmail-credential.mjs"
        ).read_text(encoding="utf-8")

        self.assertIn("01 Email Monitoring", helper)
        self.assertIn("08 Referral Reply Monitor", helper)
        self.assertIn("Gmail Trigger", helper)
        self.assertIn("gmailOAuth2", helper)
        self.assertIn("target.active", helper)

    def test_outreach_workflow_creates_draft_not_send(self):
        data = json.loads((ROOT / "n8n" / "workflows" / "03-email-drafting.json").read_text(encoding="utf-8"))
        gmail_nodes = [node for node in data["nodes"] if node["type"] == "n8n-nodes-base.gmail"]
        draft_node = next(node for node in gmail_nodes if node["name"] == "Create Gmail Draft")

        self.assertEqual(draft_node["parameters"]["resource"], "draft")
        self.assertEqual(draft_node["parameters"]["operation"], "create")

    def test_outreach_notification_reuses_gmail_and_skips_when_no_recipient_is_configured(self):
        workflow = json.loads((ROOT / "n8n" / "workflows" / "03-email-drafting.json").read_text(encoding="utf-8"))
        nodes = {node["name"]: node for node in workflow["nodes"]}

        guard = nodes["Notification Recipient Configured"]
        notification = nodes["Notify For Approval"]
        condition = guard["parameters"]["conditions"]["string"][0]

        self.assertEqual(notification["type"], "n8n-nodes-base.gmail")
        self.assertEqual(notification["parameters"]["resource"], "message")
        self.assertEqual(notification["parameters"]["operation"], "send")
        self.assertIn("NOTIFICATION_EMAIL", notification["parameters"]["sendTo"])
        self.assertEqual(condition["operation"], "isNotEmpty")
        self.assertEqual(
            workflow["connections"]["Create Gmail Draft"]["main"][0][0]["node"],
            "Notification Recipient Configured",
        )
        self.assertEqual(
            workflow["connections"]["Notification Recipient Configured"]["main"][0][0]["node"],
            "Notify For Approval",
        )

    def test_outreach_workflow_generates_short_parts_then_assembles_boilerplate(self):
        workflow = json.loads((ROOT / "n8n" / "workflows" / "03-email-drafting.json").read_text(encoding="utf-8"))
        nodes = {node["name"]: node for node in workflow["nodes"]}

        self.assertIn("Build Email Part Prompts", nodes)
        self.assertIn("Assemble Boilerplate Email", nodes)
        for name in ("Draft Subject", "Draft Opening", "Draft Relevant Point", "Draft Call To Action"):
            self.assertEqual(nodes[name]["type"], "n8n-nodes-base.httpRequest")
            self.assertIn("OLLAMA_CHAT_MODEL", nodes[name]["parameters"]["jsonBody"])

        builder = nodes["Build Email Part Prompts"]["parameters"]["jsCode"]
        assembler = nodes["Assemble Boilerplate Email"]["parameters"]["jsCode"]
        self.assertIn("at most 8 words", builder)
        self.assertIn("return exactly NONE", builder)
        self.assertIn("Best,\\nPruthvi Kadam", assembler)
        self.assertEqual(
            workflow["connections"]["Draft Call To Action"]["main"][0][0]["node"],
            "Assemble Boilerplate Email",
        )
        self.assertEqual(
            workflow["connections"]["Assemble Boilerplate Email"]["main"][0][0]["node"],
            "Create Gmail Draft",
        )

    def test_boilerplate_email_composer_helper_is_present(self):
        helper = (ROOT / "n8n" / "workflows" / "add-boilerplate-email-composer.mjs").read_text(encoding="utf-8")

        self.assertIn("03 Email Drafting", helper)
        self.assertIn("Draft Relevant Point", helper)
        self.assertIn("Create Gmail Draft", helper)
        self.assertIn("gmailOAuth2", helper)
        self.assertIn("workflow.active", helper)

    def test_email_monitoring_only_saves_applications_with_a_company(self):
        workflow = json.loads((ROOT / "n8n" / "workflows" / "01-email-monitoring.json").read_text(encoding="utf-8"))
        nodes = {node["name"]: node for node in workflow["nodes"]}

        guard = nodes["Company Identified"]
        condition = guard["parameters"]["conditions"]["string"][0]
        self.assertEqual(guard["type"], "n8n-nodes-base.if")
        self.assertEqual(condition["value1"], "={{$json.company}}")
        self.assertEqual(condition["operation"], "isNotEmpty")
        self.assertEqual(
            workflow["connections"]["Ignore Newsletters"]["main"][0][0]["node"],
            "Company Identified",
        )
        self.assertEqual(
            workflow["connections"]["Company Identified"]["main"][0][0]["node"],
            "Save Application",
        )

    def test_email_monitoring_has_pinned_walkthrough_data_for_save_application(self):
        workflow = json.loads((ROOT / "n8n" / "workflows" / "01-email-monitoring.json").read_text(encoding="utf-8"))
        fixture = workflow["pinData"]["Company Identified"][0]["json"]

        self.assertEqual(fixture["company"], "JPMorgan Chase & Co.")
        self.assertEqual(fixture["job_id"], "210770939")
        self.assertEqual(fixture["type"], "full-time")

    def test_crm_updates_rejects_inputs_without_a_company_before_upsert(self):
        workflow = json.loads((ROOT / "n8n" / "workflows" / "04-crm-updates.json").read_text(encoding="utf-8"))
        nodes = {node["name"]: node for node in workflow["nodes"]}

        guard = nodes["Company Provided"]
        condition = guard["parameters"]["conditions"]["string"][0]
        self.assertEqual(condition["value1"], "={{$json.company}}")
        self.assertEqual(condition["operation"], "isNotEmpty")
        self.assertEqual(
            workflow["connections"]["Workflow Input"]["main"][0][0]["node"],
            "Company Provided",
        )
        self.assertEqual(
            workflow["connections"]["Company Provided"]["main"][0][0]["node"],
            "Initialize CRM",
        )

    def test_crm_updates_declares_the_application_input_contract(self):
        workflow = json.loads((ROOT / "n8n" / "workflows" / "04-crm-updates.json").read_text(encoding="utf-8"))
        trigger = next(node for node in workflow["nodes"] if node["name"] == "Workflow Input")
        example = json.loads(trigger["parameters"]["jsonExample"])

        self.assertEqual(trigger["typeVersion"], 1.1)
        self.assertEqual(trigger["parameters"]["inputSource"], "jsonExample")
        self.assertEqual(example["company"], "JPMorgan Chase & Co.")
        self.assertEqual(example["job_id"], "210770939")

    def test_crm_company_guard_helper_is_present(self):
        helper = (ROOT / "n8n" / "workflows" / "add-crm-company-guard.mjs").read_text(encoding="utf-8")

        self.assertIn("04 CRM Updates", helper)
        self.assertIn("Company Provided", helper)
        self.assertIn("applicationInputExample", helper)
        self.assertIn("isNotEmpty", helper)

    def test_company_identified_test_data_helper_is_present(self):
        helper = (ROOT / "n8n" / "workflows" / "add-company-identified-test-data.mjs").read_text(encoding="utf-8")

        self.assertIn("Company Identified", helper)
        self.assertIn("JPMorgan Chase & Co.", helper)
        self.assertIn("pinData", helper)

    def test_recruiter_ranking_serializes_the_recruiter_array_as_json(self):
        workflow = json.loads((ROOT / "n8n" / "workflows" / "02-recruiter-research.json").read_text(encoding="utf-8"))
        rank_node = next(node for node in workflow["nodes"] if node["name"] == "Rank Recruiters")
        json_body = rank_node["parameters"]["jsonBody"]

        self.assertIn("JSON.stringify", json_body)
        self.assertIn("recruiters: $json.recruiters || []", json_body)
        self.assertNotIn('"recruiters":{{$json.recruiters}}', json_body)

    def test_recruiter_ranking_json_body_helper_is_present(self):
        helper = (ROOT / "n8n" / "workflows" / "repair-recruiter-ranking-json-body.mjs").read_text(encoding="utf-8")

        self.assertIn("02 Recruiter Research", helper)
        self.assertIn("Rank Recruiters", helper)
        self.assertIn("JSON.stringify", helper)

    def test_email_monitoring_subworkflow_placeholders_match_repair_targets(self):
        workflow = json.loads((ROOT / "n8n" / "workflows" / "01-email-monitoring.json").read_text(encoding="utf-8"))
        workflow_ids = {
            node["name"]: node["parameters"].get("workflowId")
            for node in workflow["nodes"]
            if node["type"] == "n8n-nodes-base.executeWorkflow"
        }

        self.assertEqual(
            workflow_ids,
            {
                "Save Application": "04 CRM Updates",
                "Research Recruiters": "02 Recruiter Research",
                "Draft Email For Approval": "03 Email Drafting",
            },
        )

    def test_subworkflow_repair_helper_lists_all_required_nodes(self):
        helper = (ROOT / "n8n" / "workflows" / "repair-subworkflow-references.mjs").read_text(encoding="utf-8")

        for node_name in ("Save Application", "Research Recruiters", "Draft Email For Approval"):
            self.assertIn(node_name, helper)
        self.assertIn("Company Identified", helper)
        self.assertIn("applicationInputFields", helper)
        self.assertIn("applicationWorkflowInputs", helper)
        self.assertIn("$items('Company Identified')", helper)
        self.assertIn("isNotEmpty", helper)
        self.assertIn("workflowInputs", helper)
        self.assertIn("typeVersion = 1.3", helper)


if __name__ == "__main__":
    unittest.main()
