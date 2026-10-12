"""Fail CI if any requested built-in feature is absent after Kconfig resolution."""
from pathlib import Path
import sys, json
base = Path(__file__).resolve().parents[1]
config = dict(line.split('=', 1) for line in Path(sys.argv[1]).read_text().splitlines() if line.startswith('CONFIG_'))
required = dict(line.split('=', 1) for line in (base / 'configs/docker-ksun.config').read_text().splitlines() if line.startswith('CONFIG_'))
failures = {key: config.get(key, 'n') for key, value in required.items() if config.get(key) != value}
report = {'required': required, 'missing_or_changed': failures, 'pass': not failures}
Path('config-verification.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
if failures:
    raise SystemExit('Required Docker/KernelSU features did not survive Kconfig')
if config.get('CONFIG_SECURITY_SELINUX') != 'y':
    raise SystemExit('SELinux must remain enabled')
