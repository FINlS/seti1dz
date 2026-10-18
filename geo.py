import html as htmllib
import re
import sys
import os
import subprocess
import tempfile
from urllib.parse import urlencode
BASE = "http://hw1.alexbers.com"
TOKEN = "7bba72939a69e00474ca7d3e85e57e38"


def tags(s):
    return re.sub(r"<[^>]+>", " ", s)


def parse(html):
    m = re.search(r"Отправьте\s+(\w+)-запрос\s+по адресу\s*<code>([^<]+)</code>", html)
    mu = re.search(r"Загрузите файлы по адресу\s*<code>([^<]+)</code>", html)
    if m:
        method, path = m.group(1).upper(), m.group(2)
    elif mu:
        method, path = "POST", mu.group(1)
    else:
        m = re.search(r"""Перейдите по\s*<a\s+href\s*=\s*["']([^"']+)["']""", html)
        if not m:
            return None
        method, path = "GET", m.group(1)
    step = {"method": method, "path": path,
            "headers": {}, "cookies": {}, "params": {}, "form": {}, "files": {}}

    pos = 0
    for tm in re.finditer(r"<table.*?</table>", html, re.S):
        label = tags(html[pos:tm.start()]).lower()
        pos = tm.end()
        rows = re.findall(
            r"<tr>\s*<td><code>(.*?)</code></td>\s*<td><code>(.*?)</code></td>\s*</tr>",
            tm.group(0), re.S)
        data = {htmllib.unescape(k): htmllib.unescape(v) for k, v in rows}
        if mu and "содержим" in label:
            step["files"].update(data)
        elif "заголовк" in label:
            step["headers"].update(data)
        elif "cookie" in label:
            step["cookies"].update(data)
        elif "параметр" in label:
            step["params"].update(data)
        elif "форм" in label:
            step["form"].update(data)
        else:
            step.setdefault("other", []).append((label.strip(), data))
    return step

BASE = os.environ.get("HW1_BASE", BASE)


def run_curl(step, jar, tmp):
    method, url = step["method"], BASE + step["path"]
    cmd = ["curl", "-sS", "-L", "-w", "\n%{http_code}", "-b", jar, "-c", jar]
    cookies = {"user": TOKEN, **step["cookies"]}
    cmd += ["-b", "; ".join(f"{k}={v}" for k, v in cookies.items())]
    for k, v in step["headers"].items():
        cmd += ["-H", f"{k}: {v}"]

    if method == "GET":
        if step["params"]:
            cmd.append("-G")
            for k, v in step["params"].items():
                cmd += ["--data-urlencode", f"{k}={v}"]
    else:
        if step["params"]:
            url += ("&" if "?" in url else "?") + urlencode(step["params"])
        for k, v in step["form"].items():
            cmd += ["--data-urlencode", f"{k}={v}"]
        for name, content in step["files"].items():
            path = os.path.join(tmp, name)
            with open(path, "wb") as f:
                f.write(content.encode("utf-8"))
            cmd += ["-F", f"{name}=@{path}"]

    cmd.append(url)
    res = subprocess.run(cmd, capture_output=True)
    out = res.stdout.decode("utf-8", "replace")
    body, _, code = out.rpartition("\n")
    return code, body


def main():
    with tempfile.TemporaryDirectory() as tmp:
        jar = os.path.join(tmp, "cookies.txt")
        first = {"method": "GET", "path": "/", "headers": {}, "cookies": {},
                 "params": {}, "form": {}, "files": {}}
        code, text = run_curl(first, jar, tmp)
        while True:
            step = parse(text)
            if step is None:
                print(text)
                return
            if step["method"] not in ("GET", "POST") or step.get("other"):
                print(text)
                return
            code, text = run_curl(step, jar, tmp)
            print(f"{step['method']} {step['path']} -> {code}", file=sys.stderr)


if __name__ == "__main__":
    main()
