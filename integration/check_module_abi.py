"""Compare an ARM64 module's required symbol CRCs with build Module.symvers.
This checks loader ABI metadata only; it cannot prove runtime compatibility.
"""
import argparse, json, struct
from pathlib import Path
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('module', type=Path)
parser.add_argument('symvers', type=Path)
args = parser.parse_args()
data = args.module.read_bytes()
if data[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', data, 18)[0] != 183:
    raise ValueError('expected little-endian ELF64 ARM64 module')
offset = struct.unpack_from('<Q', data, 40)[0]
stride, count, strings = struct.unpack_from('<HHH', data, 58)
if stride != 64 or offset + count * stride > len(data) or strings >= count:
    raise ValueError('invalid/truncated ELF section table')
headers = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * stride) for i in range(count)]
h = headers[strings]
names = data[h[4]:h[4]+h[5]]
sections = {}
for h in headers:
    name = names[h[0]:].split(b'\0', 1)[0].decode()
    if h[1] == 8:  # SHT_NOBITS
        continue
    if h[4] + h[5] > len(data):
        raise ValueError('section exceeds file: ' + name)
    sections[name] = data[h[4]:h[4]+h[5]]
versions = sections['__versions']
if len(versions) % 64:
    raise ValueError('invalid modversion records')
required = {versions[i+8:i+64].split(b'\0', 1)[0].decode():
            struct.unpack_from('<I', versions, i)[0] for i in range(0, len(versions), 64)}
available = {}
for line in args.symvers.read_text().splitlines():
    fields = line.split()
    if len(fields) >= 2:
        available[fields[1]] = int(fields[0], 16) & 0xffffffff
missing = sorted(set(required) - set(available))
mismatch = {name: {'module': hex(crc), 'kernel': hex(available[name])}
            for name, crc in required.items() if name in available and crc != available[name]}
vermagic = next(v.decode().split('=', 1)[1] for v in sections['.modinfo'].split(b'\0') if v.startswith(b'vermagic='))
print(json.dumps({'required_symbols': len(required), 'vermagic': vermagic,
                  'missing': missing, 'mismatched': mismatch,
                  'symbol_crcs_match': not missing and not mismatch}, indent=2))
raise SystemExit(1 if missing or mismatch else 0)
