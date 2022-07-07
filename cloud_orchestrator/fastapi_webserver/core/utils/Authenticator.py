from ldap3 import Server, Connection, ALL, SUBTREE, ALL_ATTRIBUTES
from ldap3.core.exceptions import LDAPException, LDAPBindError


class Authenticator:
    def __init__(self, config):
        self._config = config['ldap']

    def check_cred(self, ldap_user_name, ldap_password):
        try:
            ldsp_server = self._config['ldap_server']
            base_dn = self._config['base_dn']
            search_filter = self._config['search_filter'].format(ldap_user_name)

            server = Server(ldsp_server, get_info=ALL)
            connection = Connection(server,
                                    user=ldap_user_name,
                                    password=ldap_password,
                                    auto_bind=True)

            connection.search(base_dn, search_filter, attributes=ALL_ATTRIBUTES)

            return True
        except LDAPBindError as excp:
            print(excp.__str__())
            return False

        except LDAPException as excp:
            print(excp.__str__())
            return False

        except Exception as excp:
            print(excp.__str__())
            return False
