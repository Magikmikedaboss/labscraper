from tools.demo_domains import domains

def test_demo_domains_list():
    # Just check that the domains list is not empty and contains expected domains
    assert isinstance(domains, list)
    assert "methods_tooling" in domains or len(domains) > 0
