import importlib.util
import hashlib
import io
import re
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('shadowrocket_rules', ROOT / 'shell/shadowrocket_rules.py')
sr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sr)


class ShadowrocketRulesTest(unittest.TestCase):
    def setUp(self):
        self.script = (ROOT / 'install.sh').read_text()
        self.groups, self.providers, self.rules = sr.template(self.script)
        self.names = {v['url']: k for k, v in self.providers.items()}

    def loader(self, url):
        name = self.names[url]
        if name == 'applications':
            return 'payload:\n  - PROCESS-NAME,curl\n'
        if self.providers[name]['behavior'] == 'ipcidr':
            return 'payload:\n  - 2001:db8::/32\n'
        if self.providers[name]['behavior'] == 'domain':
            return "payload:\n  - '+.example.com'\n"
        return 'payload:\n  - DOMAIN,' + name.lower() + '.example\n'

    def test_template_parity_and_rule_order(self):
        self.assertEqual(sr.template(self.script), sr.template((ROOT / 'shell/install_en.sh').read_text()))
        conf = sr.generate(self.script, 'https://example.com/rules.conf', self.loader)
        self.assertIn('update-url = https://example.com/rules.conf', conf)
        self.assertIn('Siri = select,Apple Intelligence,手动切换,自动选择', conf)
        rules = conf.split('[Rule]\n')[1]
        self.assertIn('DOMAIN,appleintelligence.example,Apple Intelligence', rules)
        self.assertIn('DOMAIN,siri.example,Siri', rules)
        self.assertTrue(rules.endswith('FINAL,漏网之鱼\n'))
        comments = [line.split(': ', 1)[0][2:] for line in rules.splitlines() if line.startswith('# ') and ': https://' in line]
        expected = [r.split(',')[1] for r in self.rules if r.startswith('RULE-SET,')]
        self.assertEqual(comments, expected)
        self.assertNotIn('PROCESS-NAME,', rules)
        self.assertIn('Omitted 1 desktop process rules', rules)
        self.assertIn('IP-CIDR,2001:db8::/32,Telegram,no-resolve', rules)

    def test_payload_validation_and_conversion(self):
        self.assertEqual(sr.convert('+.example.com', 'domain'), ['DOMAIN-SUFFIX,example.com'])
        self.assertEqual(sr.convert('*.example.com', 'domain'), ['DOMAIN-WILDCARD,*.example.com'])
        self.assertEqual(sr.convert('example.com', 'domain'), ['DOMAIN,example.com'])
        self.assertEqual(sr.convert('IP-CIDR6,::1/128,no-resolve', 'classical'), ['IP-CIDR,::1/128,no-resolve'])
        for bad in ['<html>Error</html>', 'payload:\n', 'payload:\nnot a list']:
            with self.assertRaises(ValueError):
                sr.payload(bad)
        with self.assertRaises(ValueError):
            sr.convert('UNSUPPORTED,test', 'classical')

    def test_compaction_preserves_policy_boundaries_and_ip_options(self):
        source = '[Rule]\n# one: https://example.com/a\nDOMAIN-SUFFIX,example.com,OpenAI\nDOMAIN,a.example.com,OpenAI\nDOMAIN-SUFFIX,example.com,OpenAI\nIP-CIDR,2001:db8::/32,OpenAI,no-resolve\n# two: https://example.com/b\nDOMAIN,a.example.com,DIRECT\nFINAL,DIRECT\n'
        config, assets = sr.bundle(source, 'https://example.com/s/clashMetaProfiles/shadowrocket.conf')
        self.assertEqual(len(assets), 2)
        self.assertIn('DOMAIN-SUFFIX,example.com\nIP-CIDR,2001:db8::/32,no-resolve\n', assets.values())
        self.assertIn('DOMAIN,a.example.com\n', assets.values())
        self.assertTrue(config.endswith('FINAL,DIRECT\n'))
        refs = [line for line in config.splitlines() if line.startswith('RULE-SET,')]
        self.assertTrue(refs[0].endswith(',OpenAI'))
        self.assertTrue(refs[1].endswith(',DIRECT'))
        for ref in refs:
            name = ref.split(',')[1].rsplit('/', 1)[1]
            self.assertEqual(name, hashlib.sha256(assets[name].encode()).hexdigest() + '.list')

    def test_bundle_matches_generated_snapshot(self):
        original = sr.generate(self.script, 'https://example.com/rules.conf', self.loader)
        config, assets = sr.bundle(original, 'https://example.com/rules.conf')
        expanded = []
        for line in config.split('[Rule]\n')[1].splitlines():
            if line.startswith('RULE-SET,'):
                _, url, policy = line.split(',')
                for item in assets[url.rsplit('/', 1)[1]].splitlines():
                    fields = item.split(',')
                    expanded.append(','.join(fields[:2] + [policy] + fields[2:]))
            elif line and not line.startswith('#'):
                expanded.append(line)
        expected = [line for line in original.split('[Rule]\n')[1].splitlines() if line and not line.startswith('#')]
        self.assertEqual(expanded, expected)

    def test_failed_generation_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'rules.conf'
            path.write_text('previous config')
            argv = ['converter', '--script', str(ROOT / 'install.sh'), '--url', 'https://example.com/rules.conf', '--output', str(path)]
            with patch('sys.argv', argv), patch.object(sr, 'generate', side_effect=RuntimeError('download failed')):
                with self.assertRaises(RuntimeError):
                    sr.main()
            self.assertEqual(path.read_text(), 'previous config')
            with patch('sys.argv', argv), patch.object(sr, 'generate', return_value='new config'):
                sr.main()
            self.assertEqual(path.read_text(), 'new config\n')

    def test_asset_publish_failure_preserves_config(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'rules.conf'
            path.write_text('previous config')
            argv = ['converter', '--script', str(ROOT / 'install.sh'), '--url', 'https://example.com/rules.conf', '--output', str(path)]
            generated = '[Rule]\n# test: https://example.com/source\nDOMAIN,example.com,PROXY\nFINAL,DIRECT\n'
            with patch('sys.argv', argv), patch.object(sr, 'generate', return_value=generated), patch.object(sr, 'atomic_write', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    sr.main()
            self.assertEqual(path.read_text(), 'previous config')

    def test_shell_syntax_and_menu_wiring(self):
        for name in ['install.sh', 'shell/install_en.sh']:
            text = (ROOT / name).read_text()
            subprocess.run(['bash', '-n', str(ROOT / name)], check=True)
            self.assertIn('elif [[ "${manageAccountStatus}" == "6" ]]; then\n        shadowrocketRules', text)
            self.assertIn('shadowrocket://config/add/${configUrl}', text)
            self.assertIn('printf \'%s\' "${importUrl}" | qrencode', text)

    def test_in_memory_template_survives_move_and_directory_change(self):
        # Execute only the template definition, never installer top-level code.
        start = self.script.index('clashMetaConfig() {')
        end = self.script.index('\n}', start) + 2
        definition = self.script[start:end]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / 'install.sh'
            moved = root / 'installed.sh'
            original.write_text(definition + '\nmv -- "$0" "$1"\ncd /\ndeclare -f clashMetaConfig\n')
            result = subprocess.run(['bash', str(original), str(moved)], check=True, capture_output=True, text=True)
            self.assertFalse(original.exists())
            self.assertTrue(moved.exists())
            with patch('sys.stdin', io.StringIO(result.stdout)):
                memory = sr.read_script('-')
            self.assertEqual(sr.template(memory), sr.template(self.script))
            url = 'https://example.com/rules.conf'
            self.assertEqual(sr.generate(memory, url, self.loader), sr.generate(self.script, url, self.loader))

    def test_legacy_caller_falls_back_only_when_script_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / 'install.sh'
            installed = Path(directory) / 'installed.sh'
            installed.write_text(self.script)
            self.assertEqual(sr.read_script(str(original), installed), self.script)
            original.write_text('custom installer')
            self.assertEqual(sr.read_script(str(original), installed), 'custom installer')
            original.unlink()
            installed.unlink()
            with self.assertRaisesRegex(FileNotFoundError, 'update and reopen'):
                sr.read_script(str(original), installed)

    def test_converter_is_pinned_and_stale_download_is_rejected(self):
        script = (ROOT / 'install.sh').read_text()
        self.assertRegex(script, r'v2ray-agent/[0-9a-f]{40}/shell/shadowrocket_rules.py')
        expected = re.search(r'local converterSha="([0-9a-f]{64})"', script).group(1)
        self.assertEqual(hashlib.sha256((ROOT / 'shell/shadowrocket_rules.py').read_bytes()).hexdigest(), expected)
        start = script.index('    local converterSha=')
        end = script.index('    echoContent yellow "Shadowrocket: converter ', start)
        block = script[start:end]
        with tempfile.TemporaryDirectory() as directory:
            helper = Path(directory) / 'converter.py'
            for body, success in [((ROOT / 'shell/shadowrocket_rules.py').read_bytes(), True), (b'old converter', False)]:
                helper.write_bytes(body)
                shell = 'echoContent() { :; }; check() { local helper="$1";\n' + block + '\n}; check "$1"'
                result = subprocess.run(['bash', '-c', shell, 'test', str(helper)])
                self.assertEqual(result.returncode == 0, success)
                self.assertEqual(helper.exists(), success)


if __name__ == '__main__':
    unittest.main()
