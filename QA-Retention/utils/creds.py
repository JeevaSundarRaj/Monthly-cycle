import json

CRED_PATH = 'data/userCred.json'


def load_creds(path=CRED_PATH):
    with open(path) as f:
        return json.load(f)


def get_external_user(creds):
    external_user = creds.get("external_user") or creds.get("ExternalUser")
    assert external_user, "No external user credentials found in JSON"
    return external_user


def get_policy_cases(*entity_keys, path=CRED_PATH):
    """(policy_type, option_name, entity_info) for every individual/inherited policy that defines any of `entity_keys`."""
    data = load_creds(path)
    cases = []
    for policy_type in ("individual_policies", "inherited_policies"):
        for option_name, details in data.get(policy_type, {}).items():
            if not isinstance(details, dict):
                continue
            for key in entity_keys:
                if key in details:
                    cases.append((policy_type, option_name, details[key]))
                    break
    return cases
