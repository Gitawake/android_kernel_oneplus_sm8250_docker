"""Repack a LOS v2 boot with a compiled ARM64 Image, preserving its ramdisk/DTB.
Produces an unsigned experimental image; does not flash or reuse an AVB footer.
"""
import argparse, hashlib, json, struct, subprocess, sys, tempfile
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--stock', type=Path, required=True)
parser.add_argument('--kernel', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--tools', type=Path, default=Path(__file__).resolve().parents[1] / 'tools/mkbootimg')
args = parser.parse_args()
if args.output.exists():
    raise FileExistsError(args.output)
stock = args.stock.read_bytes()
kernel = args.kernel.read_bytes()
if stock[:8] != b'ANDROID!' or struct.unpack_from('<I', stock, 40)[0] != 2:
    raise ValueError('requires Android boot header v2')
if kernel[56:60] != b'ARMd':
    raise ValueError('requires an uncompressed ARM64 Image')
with tempfile.TemporaryDirectory(prefix='los-boot-') as temp:
    work = Path(temp)
    raw = subprocess.check_output([sys.executable, str(args.tools / 'unpack_bootimg.py'),
        '--boot_img', str(args.stock.resolve()), '--out', str(work / 'stock'), '--format', 'mkbootimg', '-0'])
    flags = [item.decode() for item in raw.rstrip(b'\0').split(b'\0')]
    flags[flags.index('--kernel') + 1] = str(args.kernel.resolve())
    candidate = work / 'boot.img'
    subprocess.run([sys.executable, str(args.tools / 'mkbootimg.py'), *flags, '--output', str(candidate)], check=True)
    data = candidate.read_bytes()
    if len(data) > len(stock):
        raise ValueError('repacked boot exceeds original partition size')
    subprocess.run([sys.executable, str(args.tools / 'unpack_bootimg.py'), '--boot_img', str(candidate),
        '--out', str(work / 'check')], check=True, stdout=subprocess.DEVNULL)
    for name in ('ramdisk', 'dtb'):
        if (work / 'stock' / name).read_bytes() != (work / 'check' / name).read_bytes():
            raise ValueError('repacking changed ' + name)
    if (work / 'check/kernel').read_bytes() != kernel:
        raise ValueError('repacking changed kernel')
    with args.output.open('xb') as output:
        output.write(data)
report = {'status': 'experimental_unsigned_unvalidated',
          'stock_sha256': hashlib.sha256(stock).hexdigest(),
          'kernel_sha256': hashlib.sha256(kernel).hexdigest(),
          'output_sha256': hashlib.sha256(data).hexdigest(),
          'bytes': len(data), 'preserved': ['ramdisk', 'dtb', 'header parameters']}
print(json.dumps(report, indent=2))
