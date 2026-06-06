from tools.demo_domains import domains

def test_demo_domains_list():
    # Check that the domains list is a non-empty list
    assert isinstance(domains, list)
    assert len(domains) > 0
    # Optionally, require a specific domain
    assert "methods_tooling" in domains
