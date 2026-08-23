from kube_eng.ansible.project.module_utils.idp_utils import IdPAdmin, IdPClient


def test_idp_create_client(idp_admin: IdPAdmin):
    client = IdPAdmin.client_template(client_id='kube-eng-it',
                                      name='kube-eng-it',
                                      description='Client for kube-eng integration testing',
                                      root_url='https://kube-eng-it')
    created_client = idp_admin.client_create(client)
    assert isinstance(created_client, IdPClient), 'The result is an IdPClient class'
    assert created_client.client_id == client.client_id, 'The client_id matches'
    assert created_client.id is not None, 'The client has an (object) id'

