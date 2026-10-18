import html as htmllib
import re
import sys

import requests

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


def main():
    s = requests.Session()
    s.cookies.set("user", TOKEN)

    r = s.get(BASE + "/")
    while True:
        step = parse(r.text)
        if step is None:
            print(r.text)
            return
        if step["method"] not in ("GET", "POST") or step.get("other"):
            print(r.text)
            return
        r = s.request(
            step["method"],
            BASE + step["path"],
            headers=step["headers"],
            params=step["params"],
            cookies=step["cookies"],
            data=step["form"] or None,
            files={
                name: (name, content.encode("utf-8"))
                for name, content in step["files"].items()
            } or None,
        )
        print(f"{step['method']} {step['path']} -> {r.status_code}", file=sys.stderr)


if __name__ == "__main__":
    main()