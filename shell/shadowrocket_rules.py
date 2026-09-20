#!/usr/bin/env python3
"""Convert this repository's embedded Clash template, using only the stdlib."""
import argparse
import concurrent.futures
import ipaddress
import os
from pathlib import Path
import re
import tempfile
from urllib.request import Request, urlopen


def template(text):
    text = text.split('clashMetaConfig() {', 1)[1].split('\nEOF', 1)[0]
    sections = {}
    section = None
    for line in text.splitlines():
        if line in ('proxy-groups:', 'rule-providers:', 'rules:'):
            section = line[:-1]
            sections[section] = []
        elif section:
            sections[section].append(line)
    groups, providers = [], {}
    group = None
    choices = False
    for line in sections['proxy-groups']:
        if line.startswith('  - name: '):
            group = {'name': line[10:].strip(), 'choices': []}
            groups.append(group)
            choices = False
        elif line.startswith('    type: '):
            group['type'] = line.split(': ', 1)[1]
        elif line.strip() == 'proxies:':
            choices = True
        elif line.startswith('      - ') and choices:
            group['choices'].append(line[8:].strip())
        elif line.startswith('    ') and not line.startswith('      '):
            choices = False
    name = None
    for line in sections['rule-providers']:
        if re.fullmatch(r'  [\w-]+:', line):
            name = line.strip()[:-1]
            providers[name] = {}
        elif line.startswith('    ') and ': ' in line:
            key, value = line.strip().split(': ', 1)
            providers[name][key] = value
    rules = [line[4:].strip() for line in sections['rules'] if line.startswith('  - ')]
    if not groups or not providers or not rules or not rules[-1].startswith('MATCH,'):
        raise ValueError('Unsupported or incomplete Clash template')
    return groups, providers, rules


def fetch(url):
    urls = [url]
    prefix = 'https://gh-proxy.com/'
    if url.startswith(prefix):
        urls.append(url[len(prefix):])
    for candidate in urls:
        try:
            with urlopen(Request(candidate, headers={'User-Agent': 'v2ray-agent'}), timeout=30) as response:
                return response.read(32 * 1024 * 1024).decode('utf-8-sig')
        except Exception as error:
            last_error = error
    raise RuntimeError('Could not download ' + url) from last_error


def payload(text):
    if not re.search(r'^payload:\s*$', text, re.M):
        raise ValueError('Expected a Clash YAML payload, not HTML or an error response')
    result = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or line == 'payload:':
            continue
        if not line.startswith('- '):
            raise ValueError('Unsupported payload line: ' + line[:120])
        value = line[2:].strip()
        if value[:1] in ("'", '"'):
            if value[-1:] != value[:1]:
                raise ValueError('Unbalanced payload quote')
            value = value[1:-1]
        if not value or '\n' in value or '#' in value:
            raise ValueError('Invalid payload value')
        result.append(value)
    if not result:
        raise ValueError('Empty rule payload')
    return result


def convert(value, behavior):
    if behavior == 'domain':
        if value.startswith('+.'):
            return ['DOMAIN-SUFFIX,' + value[2:]]
        if value.startswith('.'):
            return ['DOMAIN-WILDCARD,*' + value]
        if '*' in value or '?' in value:
            return ['DOMAIN-WILDCARD,' + value]
        return ['DOMAIN,' + value]
    if behavior == 'ipcidr':
        ipaddress.ip_network(value, strict=False)
        return ['IP-CIDR,' + value]
    if behavior != 'classical':
        raise ValueError('Unsupported provider behavior: ' + behavior)
    kind = value.split(',', 1)[0]
    if kind in ('PROCESS-NAME', 'PROCESS-PATH'):
        return []  # Desktop process matching is unavailable on iOS.
    if kind == 'IP-CIDR6':
        value = 'IP-CIDR,' + value.split(',', 1)[1]
        kind = 'IP-CIDR'
    if kind not in ('DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD', 'DOMAIN-WILDCARD', 'IP-CIDR', 'IP-ASN', 'GEOIP'):
        raise ValueError('Unsupported rule type: ' + kind)
    parts = value.split(',')
    if len(parts) not in (2, 3) or (len(parts) == 3 and parts[2] != 'no-resolve'):
        raise ValueError('Unsupported classical rule: ' + value)
    return [value]


def generate(script, url, loader=fetch):
    groups, providers, rules = template(script)
    names = {g['name'] for g in groups} | {'DIRECT', 'REJECT', 'PROXY'}
    used = list(dict.fromkeys(r.split(',')[1] for r in rules if r.startswith('RULE-SET,')))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {name: pool.submit(loader, providers[name]['url']) for name in used}
        values = {name: payload(job.result()) for name, job in jobs.items()}
    out = ['# Generated from the installed Clash Meta template; rules-only, no node credentials.',
           '# Snapshot: regenerate on server, then update this remote config in Shadowrocket.',
           '# iOS does not support Clash desktop process-name rules; these are omitted.',
           '[General]', 'update-url = ' + url, 'dns-server = system', 'ipv6 = true',
           '', '[Proxy Group]']
    for group in groups:
        if group['type'] not in ('select', 'url-test'):
            raise ValueError('Unsupported group type: ' + group['type'])
        choices = group['choices']
        if any(choice not in names for choice in choices):
            raise ValueError('Unknown group reference')
        if group['type'] == 'url-test':
            spec = 'url-test,policy-regex-filter=.*,url=https://cp.cloudflare.com/generate_204,interval=36000,tolerance=50'
        else:
            spec = 'select,' + ','.join(choices or ['PROXY'])
            spec += ',policy-select-name=' + (choices or ['PROXY'])[0]
            spec += ',policy-regex-filter=.*'
        out.append(group['name'] + ' = ' + spec)
    out += ['', '[Rule]']
    for rule in rules:
        parts = rule.split(',')
        if parts[0] == 'RULE-SET':
            _, name, policy, *options = parts
            if policy not in names or any(x != 'no-resolve' for x in options):
                raise ValueError('Unsupported rule: ' + rule)
            out.append('# ' + name + ': ' + providers[name]['url'])
            omitted = 0
            for value in values[name]:
                converted = convert(value, providers[name]['behavior'])
                omitted += not bool(converted)
                for item in converted:
                    fields = item.split(',')
                    extra = fields[2:] + options
                    extra = list(dict.fromkeys(extra)) if fields[0] in ('IP-CIDR', 'IP-ASN', 'GEOIP') else []
                    out.append(','.join(fields[:2] + [policy] + extra))
            if omitted:
                out.append('# Omitted %d desktop process rules (iOS unsupported).' % omitted)
        elif parts[0] == 'MATCH' and len(parts) == 2 and parts[1] in names:
            out.append('FINAL,' + parts[1])
        elif parts[0] == 'GEOIP' and len(parts) >= 3 and parts[2] in names:
            out.append(rule)
        else:
            raise ValueError('Unsupported template rule: ' + rule)
    return '\n'.join(out) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--script', required=True)
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'https?://[^\s,]+', args.url):
        parser.error('Expected a HTTP(S) config URL')
    content = generate(Path(args.script).read_text(), args.url)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=output.parent, prefix='.shadowrocket-')
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(content)
        os.chmod(temporary, 0o644)
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


if __name__ == '__main__':
    main()
