"""Run Codex's installed official validator with isolated, local dependencies."""
from pathlib import Path
import argparse
import importlib.util
import os
import re
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill', type=Path, default=ROOT)
    parser.add_argument('--official-validator', type=Path)
    parser.add_argument('--no-install', action='store_true')
    args = parser.parse_args()
    home = Path.home()
    codex = Path(os.environ.get('CODEX_HOME', home / '.codex'))
    candidates = [args.official_validator] if args.official_validator else [
        codex / 'skills/.system/skill-creator/scripts/quick_validate.py',
        codex / 'skills/skill-creator/scripts/quick_validate.py',
        home / '.agents/skills/skill-creator/scripts/quick_validate.py',
    ]
    official = next((p.resolve() for p in candidates if p and p.is_file()), None)
    if official is None:
        print('ERROR: Official quick_validate.py not found. Install skill-creator or pass --official-validator PATH.', file=sys.stderr)
        return 2
    deps = ROOT / '.validation-deps'
    sys.path.insert(0, str(deps))
    if importlib.util.find_spec('yaml') is None:
        if args.no_install:
            print('ERROR: PyYAML unavailable; rerun without --no-install to install local dependencies.', file=sys.stderr)
            return 2
        runtimes = [Path(sys.executable), home / '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe']
        pip_python = next((p for p in runtimes if p.is_file() and subprocess.run(
            [str(p), '-m', 'pip', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0), None)
        if not pip_python:
            print('ERROR: Python with pip is required. Install Python/pip, then rerun. No system packages were changed.', file=sys.stderr)
            return 2
        print('Installing PyYAML into skill-local .validation-deps (first run requires network).', flush=True)
        result = subprocess.run([str(pip_python), '-m', 'pip', 'install', '--disable-pip-version-check',
            '--only-binary=:all:', '--target', str(deps), 'pyyaml==6.0.3'])
        if result.returncode:
            print('ERROR: Dependency installation failed; official validation was NOT run.', file=sys.stderr)
            return result.returncode
    env = os.environ.copy()
    env['PYTHONUTF8'] = '1'
    env['PYTHONPATH'] = str(deps) + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    # Run with the dependency installer runtime when Python versions differ.
    runtime = str(pip_python) if 'pip_python' in locals() and pip_python else sys.executable
    print('Official validator: ' + str(official), flush=True)
    result = subprocess.run([runtime, str(official), str(args.skill.resolve())], env=env)
    if result.returncode:
        return result.returncode
    text = (args.skill / 'SKILL.md').read_text(encoding='utf-8')
    broken = [link for link in re.findall(r'\]\((references/[^)]+)\)', text) if not (args.skill / link).is_file()]
    if broken:
        print('ERROR: Broken references: ' + ', '.join(broken), file=sys.stderr)
        return 1
    # 条款防丢断言（2026-11-24 加：铁律8 曾无声丢失一次，后依 docs 记录补回）。
    # 改 SKILL.md 措辞须同步维护此处——只收语义稳定、不易被润色的词，勿加临时性表述。
    required_clauses = ['收口清账', '静默跳段', '强制卡点', '宁停勿错', '缺一则停', '守门缺省协议']
    lost = [c for c in required_clauses if c not in text]
    if lost:
        print('ERROR: Required clauses missing from SKILL.md (clause-loss guard): ' + ', '.join(lost), file=sys.stderr)
        return 1
    required = ['assets/editor-seed.html', 'assets/starter-pages.html', 'assets/design-system.json', 'scripts/build_html.py', 'scripts/check_prototype.py', 'scripts/upgrade_html.py', 'assets/free-editor.js', 'assets/direct-manipulation.js', 'assets/free-editor.css', 'assets/local-save-client.js', 'scripts/local_save_helper.py', 'scripts/build_local_bundle.py', 'assets/local-save-helper-windows-x64.exe', 'assets/local-save-helper-build.json', 'assets/macos-start.sh', 'assets/macos-runtimes/macos-runtime-manifest.json']
    is_prototype_skill = bool(re.search(r'(?m)^name:\s*product-prototype-html\s*$', text))
    required += ['assets/media-components.js','assets/media-components.css','assets/demo-media.webm','scripts/build_reference.py','scripts/test_media_components.cjs','references/media-and-business.md','assets/business-references/mechanical-mall-v37.html']
    required += ['scripts/test_product_media.cjs','scripts/test_product_media_save.cjs','scripts/check_local_bundle.py']
    required += ['assets/style-presets.json','assets/style-chooser.js','assets/style-chooser.css','scripts/test_design_styles.cjs','scripts/test_design_style_matrix.cjs','references/style-choices.md']
    # hifi 管线技能（现名 flow-ux-ui-line-cy-hifi-design，曾名 hifi-editable-gui-ux-design）manifest:
    # T02.1/T05/T06 resources (contract, receipts, runtime contract, profiles, editor verifier).
    # 排查 P2-15：技能改名后正则未跟，资源清单校验被静默跳过——现锚新名（兼容旧名副本）。
    is_draft_editor_skill = bool(re.search(r'(?m)^name:\s*(?:flow-ux-ui-line-cy-hifi-design|hifi-editable-gui-ux-design)\s*$', text))
    draft_editor_required = ['scripts/qa_receipt.py', 'scripts/prototype_contract.py',
                             'scripts/verify-editor.mjs', 'assets/runtime-contract.json',
                             'assets/project-profiles/mall.json']
    missing = [name for name in required if is_prototype_skill and not (args.skill / name).is_file()]
    missing += [name for name in draft_editor_required
                if is_draft_editor_skill and not (args.skill / name).is_file()]
    if missing:
        print('ERROR: Missing runnable editor resources: ' + ', '.join(missing), file=sys.stderr)
        return 1
    # 集成断言（2026-11-24 加，正本= references/integration-contract.md 同步规则节）——只锚高价值不变物，勿扩措辞级断言
    if is_draft_editor_skill:
        contract_path = args.skill / 'references' / 'integration-contract.md'
        if not contract_path.is_file():
            print('ERROR: integration-contract.md missing (interface contract source of truth).', file=sys.stderr)
            return 1
        contract_text = contract_path.read_text(encoding='utf-8')
        for anchor in ('管线模式', '协议页'):
            if anchor not in contract_text:
                print('ERROR: integration-contract.md lost anchor: ' + anchor, file=sys.stderr)
                return 1
        partner_skills = [
            'solo-ui-line-cy-gui-style-picker', 'solo-ui-line-cy-style-to-hifi-gui',
            'solo-ui-line-X-unslop', 'solo-ui-line-cy-ui-walkthrough',
            'solo-ui-line-cy-design-system-extract', 'solo-ui-line-cy-design-occam-razor',
            'solo-img-line-cy-icon-provisioner', 'solo-doc-line-cy-page-annotation',
        ]
        skill_roots = [home / '.zcode' / 'skills', home / '.claude' / 'skills', home / '.codex' / 'skills']
        missing_clause, missing_receipt = [], []
        for name in partner_skills:
            sk_path = next((r / name / 'SKILL.md' for r in skill_roots if (r / name / 'SKILL.md').is_file()), None)
            if sk_path is None:
                continue  # 技能本体缺位由 doctor.py 停线管理，此处不重复
            t = sk_path.read_text(encoding='utf-8', errors='replace')
            if '协议页' not in t:
                missing_clause.append(name)
            if name == 'solo-ui-line-cy-style-to-hifi-gui' and '落盘清单' not in t:
                missing_receipt.append(name + '/SKILL.md')
        main_bp = args.skill / 'references' / 'batch-production.md'
        if main_bp.is_file() and '落盘清单' not in main_bp.read_text(encoding='utf-8', errors='replace'):
            missing_receipt.append('references/batch-production.md')
        if missing_clause:
            print('ERROR: partner skills missing 协议页 clause: ' + ', '.join(missing_clause), file=sys.stderr)
            return 1
        if missing_receipt:
            print('ERROR: receipt structure drifted (落盘清单 missing): ' + ', '.join(missing_receipt), file=sys.stderr)
            return 1
    if is_prototype_skill:
        manifest=json.loads((args.skill/'assets/local-save-helper-build.json').read_text(encoding='utf-8'))
        for key,name in [('sourceSha256',manifest.get('sourceFile','scripts/local_save_helper.py')),('exeSha256','assets/local-save-helper-windows-x64.exe')]:
            if manifest.get(key)!=hashlib.sha256((args.skill/name).read_bytes()).hexdigest():
                print('ERROR: Local save helper build is stale: '+name,file=sys.stderr);return 1
        from build_local_bundle import verified_resources
        try:verified_resources(('windows','macos'))
        except (OSError,ValueError,KeyError) as e:
            print('ERROR: Mac offline runtime validation failed: '+str(e),file=sys.stderr);return 1
    print('PASS: Official skill validation and local reference checks. HTML interaction tests are separate.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
