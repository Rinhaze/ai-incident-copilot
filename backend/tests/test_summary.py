import json, subprocess
from pathlib import Path
from app.summary import CommandResult, run_command, summarize_with_optional_codex

RULE={"source":"rule","summary":"규칙","severity_reason":"근거","candidates":[{"cause":"원인","reasoning":"추론","evidence_log_ids":["1"]}],"checklist":["확인"]}
def enabled(monkeypatch):
    monkeypatch.setenv("CODEX_SUMMARY_ENABLED","true");monkeypatch.setenv("CODEX_WINDOWS_READ_DENY_READY","true")

def test_codex_is_off_by_default(monkeypatch):
    monkeypatch.delenv("CODEX_SUMMARY_ENABLED",raising=False)
    assert summarize_with_optional_codex(RULE,[{"id":"1","severity":"error","message":"x"}]) is RULE

def test_fake_runner_verifies_login_argv_stdin_schema_and_secret_removal(monkeypatch):
    enabled(monkeypatch);monkeypatch.setenv("OPENAI_API_KEY","금지된키");monkeypatch.setenv("CODEX_API_KEY","금지된키");monkeypatch.setenv("AWS_ACCESS_KEY_ID","금지된키");calls=[]
    def runner(argv,stdin,timeout,env,cwd,work):
        calls.append((argv,stdin,timeout,env,cwd,work))
        if argv==["codex","login","status"]:return CommandResult(0,b"Logged in using ChatGPT")
        assert argv[:7]==["codex","exec","--ignore-user-config","--ignore-rules","-m","gpt-5.6-sol","--json"]
        schema=json.loads(Path(argv[argv.index("--output-schema")+1]).read_text(encoding="utf-8"));assert schema["additionalProperties"] is False and set(schema["required"])==set(schema["properties"])
        Path(argv[argv.index("-o")+1]).write_text(json.dumps({"source":"codex_cli","summary":"요약","severity_reason":"근거","candidates":[{"cause":"원인","reasoning":"추론","evidence_log_ids":["1"]}],"checklist":["확인"],"error":None},ensure_ascii=False),encoding="utf-8")
        return CommandResult(0,b'{"type":"item.completed"}')
    result=summarize_with_optional_codex(RULE,[{"id":"1","severity":"error","message":"비밀 없는 근거"}],runner)
    assert result["source"]=="codex_cli" and "비밀 없는 근거" in calls[1][1]
    assert not {"OPENAI_API_KEY","CODEX_API_KEY","AWS_ACCESS_KEY_ID"} & calls[1][3].keys()
    assert not calls[1][5].exists()

def test_configured_codex_executable_is_used(monkeypatch):
    enabled(monkeypatch);monkeypatch.setenv("CODEX_EXECUTABLE", "C:/tools/codex.exe");calls=[]
    def runner(argv,stdin,timeout,env,cwd,work):
        calls.append(argv)
        if "status" in argv:return CommandResult(1,b"",b"Not logged in")
        raise AssertionError("로그인 실패 뒤 exec가 실행되면 안 됩니다")
    result=summarize_with_optional_codex(RULE,[{"id":"1","severity":"error","message":"x"}],runner)
    assert calls[0][0] == "C:/tools/codex.exe" and result["source"] == "rule"

def test_unknown_citation_and_non_chatgpt_login_fall_back(monkeypatch):
    enabled(monkeypatch)
    def forged(argv,stdin,timeout,env,cwd,work):
        if "status" in argv:return CommandResult(0,b"Logged in with API key")
        raise AssertionError("실행되면 안 됩니다")
    assert "ChatGPT 로그인" in summarize_with_optional_codex(RULE,[{"id":"1","severity":"error","message":"x"}],forged)["error"]
    def bad_citation(argv,stdin,timeout,env,cwd,work):
        if "status" in argv:return CommandResult(0,b"Logged in using ChatGPT")
        Path(argv[argv.index("-o")+1]).write_text(json.dumps({"source":"codex_cli","summary":"요약","severity_reason":"근거","candidates":[{"cause":"원인","reasoning":"추론","evidence_log_ids":["fake"]}],"checklist":[],"error":None}),encoding="utf-8");return CommandResult(0)
    assert "입력에 없는 로그" in summarize_with_optional_codex(RULE,[{"id":"1","severity":"error","message":"x"}],bad_citation)["error"]

def test_timeout_returns_korean_rule_fallback(monkeypatch):
    enabled(monkeypatch)
    def timeout(argv,stdin,seconds,env,cwd,work):
        if "status" in argv:return CommandResult(0,b"Logged in using ChatGPT")
        raise subprocess.TimeoutExpired(argv,seconds)
    result=summarize_with_optional_codex(RULE,[{"id":"1","severity":"error","message":"x"}],timeout)
    assert result["source"]=="rule" and "규칙 요약" in result["error"]

def test_subprocess_uses_shell_false_and_kills_tree_on_timeout(tmp_path,monkeypatch):
    seen={}
    class FakeProcess:
        pid=4321;returncode=1
        def __init__(self,*args,**kwargs):seen.update(kwargs)
        def communicate(self,_input,timeout):raise subprocess.TimeoutExpired("codex",timeout)
        def wait(self,timeout):return 1
    monkeypatch.setattr("app.summary.subprocess.Popen",FakeProcess);monkeypatch.setattr("app.summary._kill_tree",lambda process:seen.update(killed=process.pid))
    try:run_command(["codex"],"입력",1,{},tmp_path,tmp_path)
    except subprocess.TimeoutExpired:pass
    assert seen["shell"] is False and seen["killed"]==4321
