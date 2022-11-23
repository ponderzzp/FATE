import pprint
from .dag_structures import PartySpec


class Roles(object):
    def __init__(self):
        self._role_party_id_mappings = dict()
        self._role_party_index_mapping = dict()
        self._scheduler_party_id = None

    def set_role(self, role, party_id):
        if not isinstance(party_id, list):
            party_id = [party_id]

        if role not in self._role_party_id_mappings:
            self._role_party_id_mappings[role] = []
            self._role_party_index_mapping[role] = dict()

        for pid in party_id:
            if pid in self._role_party_index_mapping[role]:
                raise ValueError(f"role {role}, party {pid} has been added before")
            self._role_party_index_mapping[role][pid] = len(self._role_party_id_mappings[role])
            self._role_party_id_mappings[role].append(pid)

        self._role_party_id_mappings[role] = party_id

    def set_scheduler_party_id(self, party_id):
        self._scheduler_party_id = party_id

    @property
    def scheduler_party_id(self):
        return self._scheduler_party_id

    def get_party_id_list_by_role(self, role):
        return self._role_party_id_mappings[role]

    def get_party_by_role_index(self, role, index):
        return self._role_party_id_mappings[role][index]

    def get_runtime_roles(self):
        return self._role_party_id_mappings.keys()

    def get_parties_spec(self, roles=None):
        if not roles:
            roles = self._role_party_id_mappings.keys()

        roles = set(roles)

        role_list = []
        for role, party_id_list in self._role_party_id_mappings.items():
            if role not in roles:
                continue
            role_list.append(PartySpec(role=role, party_id=party_id_list))

        return role_list
