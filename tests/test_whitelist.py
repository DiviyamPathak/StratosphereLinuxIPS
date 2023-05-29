from tests.module_factory import ModuleFactory
import pytest



def test_read_whitelist(database):
    """
    make sure the content of whitelists is read and stored properly
    uses tests/test_whitelist.conf for testing
    """
    whitelist = ModuleFactory().create_whitelist_obj()
    # 9 is the number of lines read after the comment lines at th begining of the file
    assert whitelist.read_whitelist() == 29
    assert '91.121.83.118' in database.get_whitelist('IPs').keys()
    assert 'apple.com' in database.get_whitelist('domains').keys()
    assert 'microsoft' in database.get_whitelist('organizations').keys()


@pytest.mark.parametrize('org,asn', [('google', 'AS6432')])
def test_load_org_asn(org, asn):
    whitelist = ModuleFactory().create_whitelist_obj()
    assert whitelist.load_org_asn(org) is not False
    assert asn in whitelist.load_org_asn(org)


@pytest.mark.parametrize('org,subnet', [('google', '216.73.80.0/20')])
def test_load_org_IPs(org, subnet):
    whitelist = ModuleFactory().create_whitelist_obj()
    assert whitelist.load_org_IPs(org) is not False
    # we now store subnets in a dict sorted by the first octet
    first_octet = subnet.split('.')[0]
    assert first_octet in whitelist.load_org_IPs(org)
    assert subnet in whitelist.load_org_IPs(org)[first_octet]
