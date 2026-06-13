import logging
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("successcore.connectors")

CONNECTOR_TEMPLATES = {
    "jira": {
        "name": "Jira",
        "actions": {
            "create_issue": {"url": "https://{domain}.atlassian.net/rest/api/3/issue", "method": "POST", "headers": {"Authorization": "Basic {api_token_base64}", "Content-Type": "application/json"}, "body_template": '{"fields":{"project":{"key":"{project_key}"},"summary":"{summary}","description":"{description}","issuetype":{"name":"{issue_type}"}}}'},
            "transition_issue": {"url": "https://{domain}.atlassian.net/rest/api/3/issue/{issue_key}/transitions", "method": "POST", "headers": {"Authorization": "Basic {api_token_base64}", "Content-Type": "application/json"}, "body_template": '{"transition":{"id":"{transition_id}"}}'},
        }
    },
    "microsoft_teams": {
        "name": "Microsoft Teams",
        "actions": {
            "send_message": {"url": "{webhook_url}", "method": "POST", "headers": {"Content-Type": "application/json"}, "body_template": '{"text":"{message}"}'}
        }
    },
    "google_workspace": {
        "name": "Google Workspace",
        "actions": {
            "create_user": {"url": "https://admin.googleapis.com/admin/directory/v1/users", "method": "POST", "headers": {"Authorization": "Bearer {access_token}", "Content-Type": "application/json"}, "body_template": '{"primaryEmail":"{email}","name":{"givenName":"{first_name}","familyName":"{last_name}"},"password":"{temp_password}","changePasswordAtNextLogin":true}'},
            "send_email": {"url": "https://gmail.googleapis.com/gmail/v1/users/me/messages/send", "method": "POST", "headers": {"Authorization": "Bearer {access_token}", "Content-Type": "application/json"}, "body_template": '{"raw":"{base64_encoded_email}"}'},
        }
    },
    "github": {
        "name": "GitHub",
        "actions": {
            "create_issue": {"url": "https://api.github.com/repos/{owner}/{repo}/issues", "method": "POST", "headers": {"Authorization": "token {github_token}", "Accept": "application/vnd.github.v3+json"}, "body_template": '{"title":"{title}","body":"{body}"}'},
        }
    },
    "stripe": {
        "name": "Stripe",
        "actions": {
            "create_invoice": {"url": "https://api.stripe.com/v1/invoices", "method": "POST", "headers": {"Authorization": "Bearer {stripe_key}", "Content-Type": "application/x-www-form-urlencoded"}, "body_template": "customer={customer_id}&auto_advance=true"},
            "create_customer": {"url": "https://api.stripe.com/v1/customers", "method": "POST", "headers": {"Authorization": "Bearer {stripe_key}", "Content-Type": "application/x-www-form-urlencoded"}, "body_template": "email={email}&name={name}"},
        }
    },
    "salesforce": {
        "name": "Salesforce",
        "actions": {
            "create_contact": {"url": "https://{instance}.salesforce.com/services/data/v58.0/sobjects/Contact", "method": "POST", "headers": {"Authorization": "Bearer {access_token}", "Content-Type": "application/json"}, "body_template": '{"FirstName":"{first_name}","LastName":"{last_name}","Email":"{email}","Phone":"{phone}"}'},
        }
    },
    "slack": {
        "name": "Slack",
        "actions": {
            "send_message": {"url": "https://slack.com/api/chat.postMessage", "method": "POST", "headers": {"Authorization": "Bearer {slack_bot_token}", "Content-Type": "application/json"}, "body_template": '{"channel":"{channel}","text":"{text}"}'},
        }
    },
}


def get_connector_config(provider: str) -> dict:
    return CONNECTOR_TEMPLATES.get(provider.lower(), {})


def list_connectors() -> List[Dict]:
    return [{"provider": k, "name": v["name"], "actions": list(v["actions"].keys())} for k, v in CONNECTOR_TEMPLATES.items()]
