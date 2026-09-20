import importlib.util
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
            self.assertEqual(path.read_text(), 'new config')

    def test_shell_syntax_and_menu_wiring(self):
        for name in ['install.sh', 'shell/install_en.sh']:
            text = (ROOT / name).read_text()
            subprocess.run(['bash', '-n', str(ROOT / name)], check=True)
            self.assertIn('elif [[ "${manageAccountStatus}" == "6" ]]; then\n        shadowrocketRules', text)
            self.assertIn('shadowrocket://config/add/${configUrl}', text)
            self.assertIn('printf \'%s\' "${importUrl}" | qrencode', text)


if __name__ == '__main__':
    unittest.main()
