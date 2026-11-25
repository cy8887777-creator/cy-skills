"""Environment doctor: DISCOVER existing resources first, only flag what is truly missing.

Philosophy (learned 2026-10-29): never re-install something that already exists
somewhere on this machine. Discovery order: NODE_PATH segments / PLAYWRIGHT_MODULE_PATH /
npm global / skill ancestor node_modules. Browser: read the module's OWN required
chromium build, then check the shared ms-playwright dir for it.

Usage: python doctor.py            → READY/FAIL + findings
       python doctor.py --json     → machine-readable findings
exit 0/1.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ASSETS = [
    'assets/editor-seed.html', 'assets/free-editor.js', 'assets/free-editor.css',
    'assets/direct-manipulation.js', 'assets/local-save-client.js',
    'assets/media-components.js', 'assets/media-components.css', 'assets/demo-media.webm',
    'assets/style-chooser.js', 'assets/style-chooser.css', 'assets/style-presets.json',
    'assets/design-system.json', 'assets/starter-pages.html',
]
REQUIRED_SCRIPTS = ['build.py', 'upgrade_html.py', 'validate.py',
                    'verify-interactions.mjs', 'audit.mjs', 'state_check.py',
                    'screenshot.mjs']

# 协作技能存在性（2026-11-24 加）：强依赖缺位=管线断（停线报告）；弱依赖缺位=降级可跑（黄灯，交付说明登记）。
# 不探测附加B 旁批技能（solo-doc-line-cy-page-annotation）——客户按需选，开工前探测必然误报。
DEPENDENT_SKILLS_STRONG = [
    'solo-ui-line-cy-gui-style-picker',    # 阶段3 选型：缺=没选型，管线断
    'solo-ui-line-cy-style-to-hifi-gui',   # 阶段4 画师：缺=没人画代表页
    'solo-ui-line-X-unslop',               # 阶段4/6 精修：缺=精修循环消失
    'solo-ui-line-cy-ui-walkthrough',      # 阶段4/6 收尾硬检：缺=验收门消失
]
DEPENDENT_SKILLS_WEAK = [
    'solo-ui-line-cy-design-system-extract',  # 阶段5 提取：缺=主对话手编资产（降级口径见 start-doc 设计资产表）
    'solo-ui-line-cy-design-occam-razor',     # 阶段6 减法：缺=少减法精简环节
    'solo-img-line-cy-icon-provisioner',      # 图标供给：缺=图标质量降级
]
SKILL_ROOTS = [Path.home() / '.zcode' / 'skills',
               Path.home() / '.claude' / 'skills',
               Path.home() / '.codex' / 'skills']


def find_skill(name):
    for root in SKILL_ROOTS:
        if (root / name / 'SKILL.md').is_file():
            return root / name
    return None


def find_playwright_module():
    """Discover an existing playwright module. Returns (path, version, via) or (None,)*3."""
    candidates = []
    np = os.environ.get('NODE_PATH', '')
    candidates += [(seg, 'NODE_PATH') for seg in np.split(os.pathsep) if seg.strip()]
    pmp = os.environ.get('PLAYWRIGHT_MODULE_PATH', '')
    if pmp:
        candidates.append((pmp, 'PLAYWRIGHT_MODULE_PATH'))
    appdata = os.environ.get('APPDATA', '')
    if appdata:
        candidates.append((str(Path(appdata) / 'npm' / 'node_modules'), 'npm global'))
    candidates.append((str(Path(__file__).resolve().parent / 'node_modules'), 'scripts-local'))
    candidates.append((str(ROOT / 'node_modules'), 'skill-root'))
    d = ROOT
    for _ in range(3):
        d = d.parent
        candidates.append((str(d / 'node_modules'), 'ancestor'))

    for base, via in candidates:
        pw = Path(base) / 'playwright'
        pj = pw / 'package.json'
        if pj.exists():
            try:
                ver = json.loads(pj.read_text(encoding='utf-8')).get('version', '?')
            except Exception:
                ver = '?'
            return str(pw), ver, via
    return None, None, None


def required_chromium_revision(module_path):
    """Read the chromium build this playwright module is hard-bound to."""
    if not module_path:
        return None
    for bj in (Path(module_path) / 'playwright-core' / 'browsers.json',
               Path(module_path) / 'node_modules' / 'playwright-core' / 'browsers.json'):
        if bj.exists():
            try:
                j = json.loads(bj.read_text(encoding='utf-8'))
                for b in j.get('browsers', []):
                    if b.get('name') == 'chromium':
                        return str(b.get('revision'))
            except Exception:
                pass
    return None


def browsers_dir():
    bp = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', '')
    if bp:
        return Path(bp)
    local = os.environ.get('LOCALAPPDATA', '')
    return Path(local) / 'ms-playwright' if local else None


def browser_status(module_path):
    """Returns (state, detail): state in {'found','missing','unknown'}."""
    rev = required_chromium_revision(module_path)
    if not rev:
        return 'unknown', 'could not read required chromium revision from module'
    bd = browsers_dir()
    if not bd or not bd.exists():
        return 'missing', f'browsers dir not found: {bd}'
    for name in (f'chromium-{rev}', f'chromium_headless_shell-{rev}'):
        if (bd / name).exists():
            return 'found', f'chromium build {rev} found in shared dir {bd}'
    return 'missing', (f'chromium build {rev} not in {bd} — '
                       f'install with: npx playwright install chromium '
                       f'(~430MB, report to user first)')


def node_version():
    node = os.environ.get('NODE', '') or shutil_which('node')
    if not node:
        return None, 'node not found on PATH'
    try:
        r = subprocess.run([node, '--version'], capture_output=True, text=True, timeout=30)
        ver = r.stdout.strip().lstrip('v')
        major = int(ver.split('.')[0])
        if major < 18:
            return ver, f'node >=18 required, found {ver}'
        return ver, None
    except Exception as e:
        return None, f'node --version failed: {e}'


def shutil_which(cmd):
    for d in os.environ.get('PATH', '').split(os.pathsep):
        exe = Path(d) / (cmd + ('.exe' if os.name == 'nt' else ''))
        if exe.exists():
            return str(exe)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    findings = []   # {kind: ok|info|fail, msg}
    problems = []

    py_ver = f'{sys.version_info.major}.{sys.version_info.minor}'
    if sys.version_info < (3, 10):
        problems.append(f'python >=3.10 required, found {py_ver}')
    findings.append({'kind': 'ok' if sys.version_info >= (3, 10) else 'fail',
                     'msg': f'python {py_ver}'})

    ver, err = node_version()
    findings.append({'kind': 'fail' if err else 'ok',
                     'msg': f'node {ver}' if not err else 'node: ' + err})
    if err:
        problems.append('node: ' + err)

    pw_path, pw_ver, via = find_playwright_module()
    if pw_path:
        findings.append({'kind': 'ok',
                         'msg': f'playwright module found: {pw_path} (v{pw_ver}, via {via}) — reuse, no install'})
    else:
        msg = ('playwright module not found in NODE_PATH/PLAYWRIGHT_MODULE_PATH/'
               'npm global/ancestors. install: npm i -g playwright@1.64.1 (~18MB) '
               '— report to user first')
        findings.append({'kind': 'fail', 'msg': msg})
        problems.append(msg)

    # AGENTS.md discipline: browser scripts require(PLAYWRIGHT_MODULE_PATH + '/playwright')
    # directly — validate that exact path when the variable is set, not just any discovery hit.
    pmp = os.environ.get('PLAYWRIGHT_MODULE_PATH', '')
    if pmp:
        if (Path(pmp) / 'playwright' / 'package.json').exists():
            findings.append({'kind': 'ok',
                             'msg': f'PLAYWRIGHT_MODULE_PATH valid: {pmp} (AGENTS.md discipline path)'})
        else:
            msg = ('PLAYWRIGHT_MODULE_PATH is set but has no playwright module: ' + pmp +
                   ' — scripts require() this exact path; fix the variable or unset it')
            findings.append({'kind': 'fail', 'msg': msg})
            problems.append(msg)

    if pw_path:
        state, detail = browser_status(pw_path)
        if state == 'found':
            findings.append({'kind': 'ok', 'msg': detail})
        elif state == 'missing':
            findings.append({'kind': 'fail', 'msg': detail})
            problems.append(detail)
        else:
            findings.append({'kind': 'fail', 'msg': detail})
            problems.append(detail)

    for rel in REQUIRED_ASSETS:
        ok = (ROOT / rel).exists()
        findings.append({'kind': 'ok' if ok else 'fail',
                         'msg': f'asset {rel}' + ('' if ok else ' MISSING')})
        if not ok:
            problems.append('missing skill asset: ' + rel)

    for script in REQUIRED_SCRIPTS:
        ok = (ROOT / 'scripts' / script).exists()
        findings.append({'kind': 'ok' if ok else 'fail',
                         'msg': f'script {script}' + ('' if ok else ' MISSING')})
        if not ok:
            problems.append('missing script: scripts/' + script)

    # 协作技能存在性：强=缺则停线；弱=黄灯降级
    for name in DEPENDENT_SKILLS_STRONG:
        if find_skill(name):
            findings.append({'kind': 'ok', 'msg': f'strong skill {name}'})
        else:
            msg = (f'strong dependency missing: {name} — pipeline cannot run as '
                   f'specified. STOP and report to user; do not silently skip the stage.')
            findings.append({'kind': 'fail', 'msg': msg})
            problems.append(msg)

    for name in DEPENDENT_SKILLS_WEAK:
        if find_skill(name):
            findings.append({'kind': 'ok', 'msg': f'skill {name}'})
        else:
            findings.append({'kind': 'info',
                             'msg': f'weak dependency missing: {name} — degrade allowed, register in delivery notes'})

    # 端型约束目录（style-to-hifi-gui 名下资源，目录级单独核——拷贝漏子目录/中文名同步出错高发）
    gui_root = find_skill('solo-ui-line-cy-style-to-hifi-gui')
    if gui_root:
        dx = gui_root / 'references' / '端型约束' / '_共用.md'
        if dx.is_file():
            findings.append({'kind': 'ok', 'msg': '端型约束 dir found under style-to-hifi-gui'})
        else:
            msg = ('端型约束 missing under solo-ui-line-cy-style-to-hifi-gui/references/ — '
                   '画师与跑批的端型约束路径断。 STOP and report.')
            findings.append({'kind': 'fail', 'msg': msg})
            problems.append(msg)

    if args.json:
        print(json.dumps({'ready': not problems, 'problems': problems,
                          'findings': findings}, ensure_ascii=False, indent=2))
        raise SystemExit(0 if not problems else 1)

    for f in findings:
        mark = {'ok': '[OK]', 'info': '[!]'}.get(f['kind'], '[X] ')
        print(mark + f['msg'])
    if problems:
        print(f'\nFAIL — {len(problems)} problem(s). Fix above, then re-run. '
              f'Install actions: report to user BEFORE downloading anything.')
        raise SystemExit(1)
    print('\nREADY — all dependencies discovered and reusable. No installs needed.')
    raise SystemExit(0)


if __name__ == '__main__':
    main()
