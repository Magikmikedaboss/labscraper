from tools.demo_output import render_case

def test_render_case_runs(capsys):
    # Just check that render_case runs and prints output for a known domain/text
    text = "The peptide GGGGSGGGSGGG was tested in mice with LC-MS/MS."
    render_case("methods_tooling", text)
    out, err = capsys.readouterr()
    assert "DOMAIN: methods_tooling" in out
    assert "ENTITIES:" in out
