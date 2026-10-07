from pr_evidence.__main__ import main
from pr_evidence.render import MARKER

RULES = """
[[rule]]
id = "api_contract"
tier = 2
paths = ["src/api/**"]
"""


def test_writes_comment_and_exits_zero(tmp_path):
    rules = tmp_path / "rules.toml"
    rules.write_text(RULES)
    files = tmp_path / "files.txt"
    files.write_text("src/api/locations.ts\n\nsrc/views/Home.vue\n")
    output = tmp_path / "evidence.md"

    code = main(["--rules", str(rules), "--files", str(files), "--output", str(output)])

    assert code == 0
    comment = output.read_text()
    assert comment.startswith(MARKER)
    assert "Tier 2" in comment
    assert "`src/views/Home.vue`" in comment
    assert "``" not in comment


def test_invalid_rules_exit_non_zero_with_message(tmp_path, capsys):
    rules = tmp_path / "rules.toml"
    rules.write_text('[[rule]]\nid = "x"\n')
    files = tmp_path / "files.txt"
    files.write_text("")
    output = tmp_path / "evidence.md"

    code = main(["--rules", str(rules), "--files", str(files), "--output", str(output)])

    assert code == 2
    assert "tier" in capsys.readouterr().err
    assert not output.exists()


def test_missing_rules_file_exit_non_zero(tmp_path, capsys):
    files = tmp_path / "files.txt"
    files.write_text("")

    code = main(["--rules", str(tmp_path / "nope.toml"), "--files", str(files), "--output", "x.md"])

    assert code == 2
    assert "nope.toml" in capsys.readouterr().err
