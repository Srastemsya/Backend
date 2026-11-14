from uuid import NAMESPACE_URL, uuid5


def dev_account_id(index):
    return str(uuid5(NAMESPACE_URL, f"srastemsya:dev:person{index}@example.test"))
